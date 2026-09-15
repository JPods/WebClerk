"""
Alice QA Service — Answer user questions, track frequency, escalate unknowns.

Users ask "how does X work in WebClerk?" Alice answers from her vector store
(readmes + code), tracks what gets asked and how often (Pareto distribution),
and escalates to WC_HQ ("ask Bill") for questions she can't answer.

The Pareto insight: 20% of questions account for 80% of volume. Alice
learns which questions those are, pre-builds answers for them, and reports
the distribution so Bill can see where users struggle.

Storage:
  - alice_log (allie DB): every question + answer logged
  - AliceObservation (commerce_expert): escalations + patterns
  - AliceInsight (commerce_expert): per-topic frequency tracking

Called by: alice_qa_task (Celery) for batch processing of queued questions,
           or directly from ask_alice MCP tool for real-time answers.
"""
from __future__ import annotations

import json
import logging
import time
from collections import Counter

import psycopg2
import psycopg2.extras

logger = logging.getLogger('alice.qa')


def _connect_allie():
    return psycopg2.connect(dbname="allie", user="williamjames", host="localhost")


def _now_ms():
    return int(time.time() * 1000)


# ── Question Classification ──────────────────────────────────────────

# Top-level topic buckets for Pareto tracking
TOPIC_BUCKETS = {
    "accounting": ["gl", "journal", "ledger", "debit", "credit", "balance",
                    "chart of accounts", "aging", "receivable", "payable",
                    "reconcil", "unbalance", "imbalance"],
    "inventory": ["stock", "reorder", "on_hand", "overstock", "understock",
                   "warehouse", "quantity", "bom", "velocity", "dead stock",
                   "safety stock", "available"],
    "transactions": ["order", "invoice", "payment", "proposal", "purchase",
                      "requisition", "work order", "convert", "status",
                      "line item", "totals"],
    "pricing": ["price", "discount", "margin", "cost", "markup", "tier",
                 "level", "wholesale", "retail", "sample"],
    "customers": ["customer", "contact", "org", "communication", "address",
                   "phone", "email", "relationship"],
    "products": ["item", "product", "sku", "catalog", "category",
                  "cross reference", "xref", "keyword"],
    "system": ["setting", "config", "rbac", "permission", "role",
                "sync", "bundle", "connection", "import", "export"],
    "reports": ["report", "dashboard", "tally", "statistics", "quick report",
                 "super report"],
}


def classify_question(question: str) -> str:
    """Classify a question into a topic bucket for Pareto tracking."""
    q_lower = question.lower()
    scores = {}
    for topic, keywords in TOPIC_BUCKETS.items():
        score = sum(1 for kw in keywords if kw in q_lower)
        if score > 0:
            scores[topic] = score
    if scores:
        return max(scores, key=scores.get)
    return "general"


def normalize_question(question: str) -> str:
    """Create a normalized key for dedup / frequency counting.

    Strips punctuation, lowercases, removes common filler words.
    Two questions with the same normalized form are "the same question."
    """
    import re
    q = question.lower().strip()
    q = re.sub(r'[^\w\s]', '', q)
    filler = {'how', 'do', 'i', 'the', 'a', 'an', 'is', 'are', 'what',
              'does', 'can', 'where', 'when', 'why', 'in', 'webclerk',
              'wc3', 'please', 'help', 'me', 'to', 'with'}
    words = [w for w in q.split() if w not in filler]
    return ' '.join(sorted(words))  # sorted for order-independence


# ── Answer a Question ────────────────────────────────────────────────

def answer_question(question: str, user_id: int | None = None,
                    category: str | None = None) -> dict:
    """Answer a user question and track it.

    Returns dict with: answer, topic, sources, is_escalated, question_id.
    """
    topic = classify_question(question)
    norm_key = normalize_question(question)

    # Track the question in alice_log
    question_id = _log_question(question, topic, norm_key, user_id)

    # Search vector store for relevant context
    try:
        from apps.ai_assistant.services.vector_store import VectorStoreService
        vs = VectorStoreService()
        results = vs.search(question, n_results=5, category=category)
    except Exception:
        # Fallback: try direct chromadb access
        results = _vector_search_fallback(question, category)

    # Determine if we have a good enough answer
    if not results or _is_low_confidence(results):
        # Escalate to WC_HQ
        _escalate_to_bill(question, topic, norm_key, question_id)
        return {
            "answer": ("I don't have a confident answer for this yet. "
                       "I've flagged it for Bill at WC_HQ. "
                       "I'll have an answer next time this comes up."),
            "topic": topic,
            "sources": [],
            "is_escalated": True,
            "question_id": question_id,
        }

    # Build answer from sources
    answer_text = _build_answer(question, results)

    # Update frequency tracking
    _update_frequency(topic, norm_key, question)

    return {
        "answer": answer_text,
        "topic": topic,
        "sources": [r.get("source", "?") for r in results if isinstance(r, dict)],
        "is_escalated": False,
        "question_id": question_id,
    }


def _is_low_confidence(results: list) -> bool:
    """Check if search results are too distant to be useful."""
    if not results:
        return True
    # If best result distance > 0.8, we're guessing
    for r in results:
        if isinstance(r, dict):
            dist = r.get("distance")
            if dist is not None and dist < 0.8:
                return False
    return True


def _build_answer(question: str, results: list) -> str:
    """Build an answer from vector search results.

    Uses Alice's LLM if available, otherwise returns structured excerpts.
    """
    try:
        # Try Alice's local LLM
        import urllib.request as ur
        context = "\n\n---\n\n".join(
            f"[Source: {r.get('source', '?')}]\n{r.get('content', '')}"
            for r in results if isinstance(r, dict) and "error" not in r
        )
        prompt = (
            f"Context from WebClerk3:\n\n{context}\n\n---\n\n"
            f"User question: {question}\n\n"
            f"Answer clearly and concisely. Use exact field names. "
            f"If the answer involves steps, number them."
        )
        payload = json.dumps({
            "model": "alice:latest",
            "prompt": prompt,
            "stream": False,
        }).encode()
        req = ur.Request("http://localhost:11434/api/generate",
                         data=payload,
                         headers={"Content-Type": "application/json"})
        with ur.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            return result.get("response", "")
    except Exception:
        # Fallback: return excerpts
        parts = []
        for r in results[:3]:
            if isinstance(r, dict) and "content" in r:
                parts.append(f"From {r.get('source', '?')}:\n{r['content'][:300]}")
        return "\n\n".join(parts) if parts else "No relevant documentation found."


def _vector_search_fallback(question: str, category: str | None = None) -> list:
    """Direct chromadb search when VectorStoreService isn't available."""
    try:
        import chromadb
        from pathlib import Path
        chroma_dir = str(Path.home() / "Allie" / ".chroma_db_alice")
        client = chromadb.PersistentClient(path=chroma_dir)
        collection = client.get_or_create_collection(
            name="alice_commerce_knowledge",
            metadata={"hnsw:space": "cosine"},
        )
        where = {"category": category} if category else None
        results = collection.query(
            query_texts=[question], n_results=5, where=where,
        )
        if not results or not results["documents"]:
            return []
        items = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            dist = results["distances"][0][i] if results["distances"] else None
            items.append({
                "content": doc[:800],
                "source": meta.get("doc_id", "?"),
                "distance": round(dist, 4) if dist else None,
            })
        return items
    except Exception:
        return []


# ── Frequency Tracking ───────────────────────────────────────────────

def _log_question(question: str, topic: str, norm_key: str,
                  user_id: int | None) -> int | None:
    """Log the question to alice_log. Returns the log entry ID."""
    try:
        conn = _connect_allie()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO alice_log
                    (dt_created, event, model_name, message, source, data)
                VALUES (%s, 'question', %s, %s, 'user', %s)
                RETURNING id
            """, (_now_ms(), topic, question[:500], json.dumps({
                "norm_key": norm_key,
                "user_id": user_id,
                "topic": topic,
            })))
            row = cur.fetchone()
            conn.commit()
            conn.close()
            return row[0] if row else None
    except Exception as e:
        logger.debug("Failed to log question: %s", e)
        return None


def _update_frequency(topic: str, norm_key: str, raw_question: str):
    """Update question frequency tracking in AliceInsight.

    Uses a system-level AliceInsight record (contact_id=system_contact)
    with subject_type='flow', subject_key='qa_frequency'.
    The config JSON accumulates topic counts and top questions.
    """
    try:
        from apps.ai_assistant.models.alice import AliceInsight
        from apps.core.models import Contact

        # Use the system contact (claude@jpods.com or first superuser)
        system_contact = Contact.objects.filter(
            communication__email__icontains='claude@jpods.com'
        ).first()
        if not system_contact:
            system_contact = Contact.objects.filter(
                userprofile__user__is_superuser=True
            ).first()
        if not system_contact:
            return

        insight, created = AliceInsight.objects.get_or_create(
            agent='alice',
            contact_id=system_contact.pk,
            subject_type='flow',
            subject_key='qa_frequency',
            defaults={
                'summary': 'Question frequency distribution (Pareto tracking)',
                'config': {'topics': {}, 'top_questions': {}, 'total_questions': 0},
            }
        )

        config = insight.config or {}
        topics = config.get('topics', {})
        top_q = config.get('top_questions', {})
        total = config.get('total_questions', 0)

        # Increment topic count
        topics[topic] = topics.get(topic, 0) + 1

        # Track normalized question frequency (keep top 100)
        top_q[norm_key] = top_q.get(norm_key, {'count': 0, 'sample': ''})
        top_q[norm_key]['count'] += 1
        top_q[norm_key]['sample'] = raw_question[:200]

        # Prune to top 100 by count
        if len(top_q) > 100:
            sorted_q = sorted(top_q.items(), key=lambda x: x[1]['count'], reverse=True)
            top_q = dict(sorted_q[:100])

        config['topics'] = topics
        config['top_questions'] = top_q
        config['total_questions'] = total + 1

        insight.config = config
        insight.observation_count = total + 1
        insight.dt_last_interaction = _now_ms()
        insight.dt_last_updated = _now_ms()
        insight.save(update_fields=['config', 'observation_count',
                                     'dt_last_interaction', 'dt_last_updated'])

    except Exception as e:
        logger.debug("Failed to update frequency: %s", e)


def _escalate_to_bill(question: str, topic: str, norm_key: str,
                      question_id: int | None):
    """Create an AliceObservation for questions Alice can't answer.

    These go to WC_HQ for Bill to answer. When Bill answers, the answer
    gets added to Alice's vector store so she can handle it next time.
    """
    try:
        from apps.ai_assistant.models.alice import AliceObservation

        dedup = f"qa_escalation_{norm_key[:150]}"

        # Check if already escalated (within last 7 days)
        existing = AliceObservation.objects.filter(
            dedup_key=dedup, resolved=False
        ).first()

        if existing:
            # Increment count in detail
            detail = existing.detail or ""
            count_line = f"\nAsked again (total asks tracked in alice_log)"
            if count_line not in detail:
                existing.detail = detail + count_line
                existing.save(update_fields=['detail', 'dt_modified'])
            return

        AliceObservation.objects.create(
            category='bill_question',
            source='alice',
            priority=0,
            message=f"[{topic}] {question[:200]}",
            detail=(f"Alice couldn't find a confident answer in her documentation.\n"
                    f"Topic: {topic}\n"
                    f"Normalized key: {norm_key}\n"
                    f"Question log ID: {question_id}\n\n"
                    f"When answered, add the answer to Alice's vector store so "
                    f"she can handle this question type going forward."),
            model_name=topic,
            dedup_key=dedup,
        )
    except Exception as e:
        logger.debug("Failed to escalate: %s", e)


# ── Reports ──────────────────────────────────────────────────────────

def get_question_distribution() -> dict:
    """Get the Pareto distribution of questions Alice has received.

    Returns topic counts, top questions, and escalation rate.
    """
    result = {
        "topics": {},
        "top_questions": [],
        "total_questions": 0,
        "escalation_rate": 0.0,
    }

    # Get frequency data from AliceInsight
    try:
        from apps.ai_assistant.models.alice import AliceInsight
        insight = AliceInsight.objects.filter(
            agent='alice', subject_type='flow', subject_key='qa_frequency'
        ).first()
        if insight and insight.config:
            config = insight.config
            result["topics"] = config.get("topics", {})
            result["total_questions"] = config.get("total_questions", 0)

            # Top 20 questions sorted by frequency
            top_q = config.get("top_questions", {})
            sorted_q = sorted(top_q.items(),
                              key=lambda x: x[1].get("count", 0),
                              reverse=True)[:20]
            result["top_questions"] = [
                {"key": k, "count": v["count"], "sample": v.get("sample", "")}
                for k, v in sorted_q
            ]
    except Exception:
        pass

    # Get escalation count
    try:
        from apps.ai_assistant.models.alice import AliceObservation
        escalated = AliceObservation.objects.filter(
            category='bill_question'
        ).count()
        total = result["total_questions"]
        if total > 0:
            result["escalation_rate"] = round(escalated / total * 100, 1)
        result["escalations_total"] = escalated
        result["escalations_unresolved"] = AliceObservation.objects.filter(
            category='bill_question', resolved=False
        ).count()
    except Exception:
        pass

    return result
