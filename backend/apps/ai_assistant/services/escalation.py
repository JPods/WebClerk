"""
AI Escalation Chain — Alice → Claude API → WCHQ.

Three tiers of answer quality:
    1. Alice local (Ollama RAG) — fast, private, free
    2. Claude API — higher-quality reasoning for low-confidence answers
    3. WCHQ data query — cross-instance product/pattern data

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

from django.conf import settings

logger = logging.getLogger(__name__)

# Confidence thresholds — tune based on observation
CONFIDENCE_ESCALATE_THRESHOLD = 0.40  # Below this → escalate to Claude
CONFIDENCE_WCHQ_KEYWORDS = [
    'other installation', 'other store', 'other location',
    'cross-instance', 'headquarters', 'wchq', 'all stores',
    'company-wide', 'across locations', 'network-wide',
    'supplier catalog', 'product library', 'shared catalog',
]

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
    needs_wchq: bool       # question references cross-instance data


def score_confidence(
    answer: str,
    sources: list[dict],
    question: str,
) -> ConfidenceScore:
    """Score Alice's confidence in her own answer.

    Factors:
        Context quality — how many relevant chunks, how close the best match
        Answer quality — length, hedging language, specificity
        Cross-instance signal — does the question need data from other stores
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

    # --- Cross-instance detection ---
    q_lower = question.lower()
    needs_wchq = any(kw in q_lower for kw in CONFIDENCE_WCHQ_KEYWORDS)

    # --- Combined score ---
    score = (context_score * 0.6) + (answer_score * 0.4)

    # If needs WCHQ data and we don't have it, lower confidence
    if needs_wchq:
        score = min(score, 0.35)

    return ConfidenceScore(
        score=round(score, 3),
        context_score=round(context_score, 3),
        answer_score=round(answer_score, 3),
        chunk_count=chunk_count,
        best_distance=round(best_distance, 3),
        hedging_count=hedging_count,
        needs_wchq=needs_wchq,
    )


def _get_claude_api_key() -> str:
    """Get Claude API key from Setting."""
    try:
        from apps.core.models import Setting
        s = Setting.objects.filter(
            purpose='claude_api', is_active=True
        ).first()
        if s and isinstance(s.config, dict):
            return s.config.get('api_key', '')
    except Exception:
        pass
    # Fallback to environment
    return getattr(settings, 'ANTHROPIC_API_KEY', '')


def escalate_to_claude(
    question: str,
    local_answer: str,
    context: str = "",
    history: list[dict] | None = None,
    mode: str = "general",
) -> dict:
    """Re-ask via Claude API when Alice's local answer has low confidence.

    Returns {"answer": str, "model": str, "tier": "claude"} or raises.
    """
    api_key = _get_claude_api_key()
    if not api_key:
        raise ConnectionError(
            "Claude API key not configured. Add a Setting with "
            "purpose='claude_api' and config={'api_key': '...'}"
        )

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    from .prompt_templates import get_system_prompt
    system_prompt = get_system_prompt(mode)
    system_prompt += (
        "\n\nYou are answering because the local AI assistant (Alice, running "
        "a smaller model) was not confident in her answer. The user's question "
        "and Alice's attempt are provided. Give a better, more complete answer."
    )

    messages = []
    if history:
        messages.extend(history)

    user_content = question
    if context:
        user_content = (
            f"Relevant documentation:\n{context}\n\n"
            f"Alice's local answer (low confidence):\n{local_answer}\n\n"
            f"Question: {question}"
        )

    messages.append({"role": "user", "content": user_content})

    response = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=2048,
        system=system_prompt,
        messages=messages,
    )

    answer = response.content[0].text
    return {
        "answer": answer,
        "model": response.model,
        "tier": "claude",
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    }


def query_wchq_data(
    question: str,
    data_type: str = "product",
) -> dict:
    """Query WCHQ for cross-instance data.

    Used when the question references data that doesn't exist locally
    (supplier catalogs, shared patterns, multi-store aggregates).

    Returns {"data": dict, "source": "wchq"} or raises ConnectionError.
    """
    import httpx
    from .ollama_client import _get_athena_token, _is_subscribed

    if not _is_subscribed():
        raise ConnectionError(
            "WCHQ data query requires a subscription. "
            "Subscribe at webclerk.com for cross-instance data access."
        )

    athena_token = _get_athena_token()
    if not athena_token:
        raise ConnectionError(
            "WCHQ data query requires an Athena token. "
            "Register this installation at webclerk.com."
        )

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                "https://webclerk.com/wcapi/alice/data-query/",
                headers={
                    'Authorization': f'Athena {athena_token}',
                },
                json={
                    "question": question,
                    "data_type": data_type,
                },
            )

            if resp.status_code == 401:
                raise ConnectionError("Athena token rejected by WCHQ.")
            if resp.status_code == 402:
                raise ConnectionError("WCHQ data query limit reached.")

            resp.raise_for_status()
            return {
                "data": resp.json(),
                "source": "wchq",
            }

    except httpx.ConnectError:
        raise ConnectionError(
            "Cannot reach webclerk.com for cross-instance data query."
        )
    except ConnectionError:
        raise
    except Exception as e:
        logger.exception("WCHQ data query failed")
        raise ConnectionError(f"WCHQ data query error: {e}")


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
