"""
Alice Inbox Processor — Real-time agent bus message processing.

Reads Alice's unread messages from agent_messages (allie DB),
processes each by category, creates AliceObservation records in
commerce_expert, and marks messages as read.

This is Alice's real-time awareness layer. The nightly Celery tasks
(health, margins, velocity, relationships) are her deep analysis.
Two speeds, same brain.

Called by: alice_inbox_task (Celery, every 60s)
Writes to: AliceObservation (commerce_expert), alice_log (allie)
Reads from: agent_messages (allie)
"""
from __future__ import annotations

import json
import logging
import time

import psycopg2
import psycopg2.extras

logger = logging.getLogger('alice.inbox')


def _connect_allie():
    """Connect to the allie database (agent bus)."""
    return psycopg2.connect(dbname="allie", user="williamjames", host="localhost")


def _now_ms():
    return int(time.time() * 1000)


def process_inbox(batch_size: int = 50) -> dict:
    """Read and process Alice's unread agent bus messages.

    Returns dict with counts of processed, observations created, errors.
    """
    conn = _connect_allie()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, dt_created, from_agent, subject, body,
                       category, context, priority
                FROM agent_messages
                WHERE to_agent = 'alice' AND NOT read
                ORDER BY dt_created ASC
                LIMIT %s
            """, (batch_size,))
            messages = [dict(row) for row in cur.fetchall()]
    except Exception as e:
        logger.error("Failed to read inbox: %s", e)
        return {"error": str(e)}
    finally:
        conn.close()

    if not messages:
        return {"processed": 0, "observations": 0}

    processed = 0
    observations = 0
    errors = 0
    msg_ids = []

    for msg in messages:
        try:
            obs = _process_message(msg)
            if obs:
                observations += 1
            processed += 1
            msg_ids.append(msg["id"])
        except Exception as e:
            logger.warning("Failed to process message %s: %s", msg["id"], e)
            errors += 1
            msg_ids.append(msg["id"])  # mark read anyway to avoid infinite retry

    # Mark all processed messages as read
    if msg_ids:
        _mark_read(msg_ids)

    result = {"processed": processed, "observations": observations, "errors": errors}
    if processed > 0:
        logger.info("Alice inbox: %d processed, %d observations, %d errors",
                     processed, observations, errors)
    return result


def _process_message(msg: dict) -> bool:
    """Process a single agent bus message. Returns True if observation created."""
    category = msg.get("category", "")
    context = msg.get("context", {})
    if isinstance(context, str):
        try:
            context = json.loads(context)
        except (json.JSONDecodeError, TypeError):
            context = {}

    subject = msg.get("subject", "")

    # Route by category
    if category == "transaction":
        return _handle_transaction(msg, context)
    elif category == "question":
        return _handle_question(msg, context)
    else:
        # Log but don't create observation for unknown categories
        return False


def _handle_transaction(msg: dict, context: dict) -> bool:
    """Process a transaction event — look for patterns worth observing.

    Not every transaction creates an observation. Alice watches for:
    - Status transitions that might indicate problems
    - Unusual amounts (zero totals, negative balances)
    - Missing data (no customer on an order, no items)
    """
    model = context.get("model", "")
    event = context.get("event", "")
    status = context.get("status", "")
    total = context.get("total", 0)
    balance = context.get("balance", 0)
    ida = context.get("ida", "")
    record_id = context.get("id")

    # Flag: zero-total released invoice
    if model == "invoice" and event == "updated" and status in ("released", "complete"):
        if total == 0:
            _create_observation(
                category="anomaly",
                model_name="invoice",
                record_id=record_id,
                message=f"Invoice {ida} released with $0 total",
                detail=f"Status: {status}. A released invoice with zero total "
                       f"may indicate missing line items or pricing.",
                dedup_key=f"zero_total_invoice_{record_id}",
                priority=1,
            )
            return True

    # Flag: negative balance on invoice (overpayment)
    if model == "invoice" and balance < 0:
        _create_observation(
            category="anomaly",
            model_name="invoice",
            record_id=record_id,
            message=f"Invoice {ida} has negative balance: ${balance}",
            detail="Negative balance indicates overpayment. Check payment applications.",
            dedup_key=f"neg_balance_invoice_{record_id}",
            priority=1,
        )
        return True

    # Flag: payment without matching invoice context
    if model == "payment" and event == "created":
        if not context.get("invoice_id"):
            # Log to alice_log for pattern tracking, but don't observe every payment
            _log_to_alice("observe", "payment", f"Payment #{record_id} created, status={status}")

    return False


def _handle_question(msg: dict, context: dict) -> bool:
    """Process a user question routed through the bus."""
    # Questions are handled by alice_qa service, not inbox
    return False


def _create_observation(
    category: str,
    model_name: str,
    message: str,
    record_id: int | None = None,
    detail: str = "",
    dedup_key: str = "",
    priority: int = 0,
) -> None:
    """Create an AliceObservation in commerce_expert database."""
    try:
        from apps.ai_assistant.models.alice import AliceObservation

        # Check dedup — don't create duplicate observations
        if dedup_key:
            exists = AliceObservation.objects.filter(
                dedup_key=dedup_key, resolved=False
            ).exists()
            if exists:
                return

        AliceObservation.objects.create(
            category=category,
            source="alice",
            priority=priority,
            message=message,
            detail=detail,
            model_name=model_name,
            record_id=record_id,
            dedup_key=dedup_key,
        )
    except Exception as e:
        logger.warning("Failed to create observation: %s", e)


def _log_to_alice(event: str, model_name: str, message: str, data: dict | None = None):
    """Write to alice_log in the allie database."""
    try:
        conn = _connect_allie()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO alice_log (dt_created, event, model_name, message, source, data)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (_now_ms(), event, model_name, message, "alice_inbox",
                  json.dumps(data) if data else None))
            conn.commit()
        conn.close()
    except Exception:
        pass


def _mark_read(msg_ids: list[int]):
    """Mark messages as read in the allie database."""
    try:
        conn = _connect_allie()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE agent_messages
                SET read = TRUE, dt_read = %s
                WHERE id = ANY(%s)
            """, (_now_ms(), msg_ids))
            conn.commit()
        conn.close()
    except Exception as e:
        logger.warning("Failed to mark messages read: %s", e)


def get_inbox_stats() -> dict:
    """Get Alice's inbox statistics for status reporting."""
    try:
        conn = _connect_allie()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    count(*) FILTER (WHERE NOT read) as unread,
                    count(*) FILTER (WHERE read) as read,
                    count(*) as total,
                    count(DISTINCT category) as categories
                FROM agent_messages
                WHERE to_agent = 'alice'
            """)
            row = cur.fetchone()
            conn.close()
            return {
                "unread": row[0],
                "read": row[1],
                "total": row[2],
                "categories": row[3],
            }
    except Exception as e:
        return {"error": str(e)}
