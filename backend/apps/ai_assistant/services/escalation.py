"""
AI Escalation Chain — Alice local → Alice at WCHQ → Alice+Claude at WCHQ.

Three tiers of answer quality:
    1. Alice local (Ollama RAG) — fast, private, free, always first
    2. Alice at WCHQ (WCHQ shared LLM) — better model, subscription
    3. Alice+Claude at WCHQ — WCHQ calls Claude on behalf of the installation

Individual installations never need a Claude API key. WCHQ manages the
Claude relationship centrally. Users just need a subscription.

Confidence scoring determines when to escalate. All escalations are
logged as AliceObservation(category='escalation') for pattern analysis.

All data flows through wcapi. All persisted results use JSON envelopes
validated by Pydantic schemas. No direct model writes from AI output.

Usage:
    from apps.ai_assistant.services.escalation import EscalationChain

    chain = EscalationChain()
    result = chain.ask("What discount tier is customer X in?",
                       mode="general", history=history)
    # result includes: answer, confidence, tier_used, sources, escalation_log
"""
import logging
import re
from dataclasses import dataclass

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

# Confidence thresholds — tune based on observation
CONFIDENCE_ESCALATE_THRESHOLD = 0.40  # Below this → escalate to WCHQ

# Hedging signals in Alice's local answers — indicate low confidence
_HEDGING_PATTERNS = [
    r"\bi(?:'m| am) not sure\b",
    r"\bi don'?t (?:know|have)\b",
    r"\bi cannot (?:find|determine|answer)\b",
    r"\bbased on (?:the |my )?limited\b",
    r"\bno (?:relevant |matching )?(?:context|documentation|information)\b",
    r"\boutside (?:my|the) (?:scope|knowledge)\b",
    r"\bI would need (?:more|additional)\b",
    r"\bcannot be determined\b",
]
_HEDGING_RE = re.compile('|'.join(_HEDGING_PATTERNS), re.IGNORECASE)


@dataclass
class ConfidenceScore:
    """Breakdown of how confidence was computed."""
    score: float           # 0.0–1.0
    context_score: float   # from RAG retrieval quality
    answer_score: float    # from answer content analysis
    chunk_count: int       # number of relevant context chunks
    best_distance: float   # best vector similarity distance
    hedging_count: int     # number of hedging phrases detected


def score_confidence(
    answer: str,
    sources: list[dict],
    question: str,
) -> ConfidenceScore:
    """Score Alice's confidence in her own answer.

    Factors:
        Context quality — how many relevant chunks, how close the best match
        Answer quality — length, hedging language, specificity
    """
    # --- Context score (0.0–1.0) ---
    chunk_count = len(sources)
    if chunk_count == 0:
        context_score = 0.0
        best_distance = 99.0
    else:
        distances = [s.get('distance') or 99.0 for s in sources]
        best_distance = min(distances)
        # Distance < 0.5 = excellent, < 0.8 = good, < 1.0 = fair, > 1.0 = poor
        if best_distance < 0.5:
            dist_score = 1.0
        elif best_distance < 0.8:
            dist_score = 0.8
        elif best_distance < 1.0:
            dist_score = 0.5
        else:
            dist_score = 0.2

        # More chunks = more context (diminishing returns after 4)
        chunk_score = min(chunk_count / 4.0, 1.0)
        context_score = (dist_score * 0.7) + (chunk_score * 0.3)

    # --- Answer score (0.0–1.0) ---
    answer_len = len(answer.strip())
    hedging_matches = _HEDGING_RE.findall(answer)
    hedging_count = len(hedging_matches)

    # Very short answers are suspicious
    if answer_len < 50:
        length_score = 0.3
    elif answer_len < 150:
        length_score = 0.6
    else:
        length_score = 1.0

    # Each hedging phrase reduces confidence
    hedge_penalty = min(hedging_count * 0.25, 0.8)
    answer_score = max(length_score - hedge_penalty, 0.0)

    # --- Combined score ---
    score = (context_score * 0.6) + (answer_score * 0.4)

    return ConfidenceScore(
        score=round(score, 3),
        context_score=round(context_score, 3),
        answer_score=round(answer_score, 3),
        chunk_count=chunk_count,
        best_distance=round(best_distance, 3),
        hedging_count=hedging_count,
    )


# ── WCHQ endpoints ──────────────────────────────────────────────────

WCHQ_ALICE_URL = "https://webclerk.com/wcapi/alice/ask/"
WCHQ_ALICE_CLAUDE_URL = "https://webclerk.com/wcapi/alice/ask-claude/"


def _get_athena_token() -> str:
    """Get the Athena token for WCHQ authentication."""
    try:
        from apps.core.models import Setting
        conn = Setting.objects.filter(
            purpose='wchq_connection', is_active=True
        ).first()
        if conn and isinstance(conn.config, dict):
            return conn.config.get('athena_token', '')
    except Exception:
        pass
    return ''


def _is_subscribed() -> bool:
    """Check if this installation has an active WCHQ subscription."""
    try:
        from apps.core.models import Setting
        sub = Setting.objects.filter(
            purpose='wc:subscription', is_active=True
        ).first()
        if sub and isinstance(sub.config, dict):
            return bool(sub.config.get('subscribed', False))
    except Exception:
        pass
    return False


def _subscription_tier() -> str:
    """Return the subscription tier: community, standard, professional."""
    try:
        from apps.core.models import Setting
        sub = Setting.objects.filter(
            purpose='wc:subscription', is_active=True
        ).first()
        if sub and isinstance(sub.config, dict):
            return sub.config.get('tier', 'community')
    except Exception:
        pass
    return 'community'


def escalate_to_wchq(
    question: str,
    local_answer: str,
    local_confidence: float,
    context: str = "",
    mode: str = "general",
) -> dict:
    """Escalate to WCHQ's Alice — better model, shared infrastructure.

    Tier 2: WCHQ runs its own Alice with a larger model. The installation
    sends the question (not raw data) plus the local confidence score.
    WCHQ Alice answers. If WCHQ's Alice is also low-confidence and the
    subscription tier allows it, WCHQ will internally escalate to Claude.

    Returns {"answer": str, "model": str, "tier": str} or raises.
    """
    if not _is_subscribed():
        raise ConnectionError(
            "WCHQ escalation requires a subscription. "
            "Subscribe at webclerk.com for AI escalation access."
        )

    athena_token = _get_athena_token()
    if not athena_token:
        raise ConnectionError(
            "WCHQ escalation requires an Athena token. "
            "Register this installation at webclerk.com."
        )

    tier = _subscription_tier()

    # Choose endpoint based on subscription tier
    # Standard: WCHQ Alice only. Professional: WCHQ can escalate to Claude.
    url = WCHQ_ALICE_URL
    if tier == 'professional':
        url = WCHQ_ALICE_CLAUDE_URL

    # Scrub PII before sending upstream
    from .pii_scrub import scrub_pii
    question, _ = scrub_pii(question)
    local_answer, _ = scrub_pii(local_answer)
    if context:
        context, _ = scrub_pii(context)

    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                url,
                headers={
                    'Authorization': f'Athena {athena_token}',
                    'X-Alice-Mode': mode,
                },
                json={
                    "question": question,
                    "local_answer": local_answer,
                    "local_confidence": local_confidence,
                    "context_summary": context[:2000] if context else "",
                    "mode": mode,
                    "tier": tier,
                },
            )

            if resp.status_code == 401:
                raise ConnectionError(
                    "Athena token rejected by WCHQ. "
                    "Re-register this installation at webclerk.com."
                )
            if resp.status_code == 402:
                raise ConnectionError(
                    "WCHQ AI quota reached. Upgrade your subscription "
                    "or wait for the next billing cycle."
                )

            resp.raise_for_status()
            data = resp.json()

            # WCHQ tells us which tier it used internally
            wchq_tier = data.get('tier_used', 'wchq_alice')

            logger.info(
                "WCHQ escalation succeeded: tier=%s, tokens=%s",
                wchq_tier, data.get('usage', {}).get('total_tokens', '?'),
            )

            return {
                "answer": data.get('answer', ''),
                "model": data.get('model', 'wchq'),
                "tier": wchq_tier,
                "usage": data.get('usage', {}),
            }

    except httpx.ConnectError:
        raise ConnectionError(
            "Cannot reach webclerk.com — WCHQ escalation unavailable. "
            "Alice will use her local answer."
        )
    except ConnectionError:
        raise
    except Exception as e:
        logger.exception("WCHQ escalation failed")
        raise ConnectionError(f"WCHQ escalation error: {e}")


def log_escalation(
    question: str,
    local_confidence: float,
    tier_used: str,
    reason: str,
) -> None:
    """Log an escalation as AliceObservation for pattern analysis."""
    try:
        from apps.ai_assistant.models.alice import AliceObservation
        AliceObservation.objects.create(
            category='escalation',
            source='alice',
            message=f"Escalated to {tier_used}: {question[:80]}",
            detail=(
                f"Confidence: {local_confidence:.1%}\n"
                f"Reason: {reason}\n"
                f"Question: {question[:500]}"
            ),
            priority=0,
        )
    except Exception:
        logger.warning("Failed to log escalation observation", exc_info=True)
