"""
agent_bus_bridge.py — Alice's connection to the inter-agent message bus.

The agent bus lives in the 'allie' PostgreSQL database, separate from
commerce_expert. This bridge lets Alice (and any WC3 agent) send and
receive messages without importing the full agent_bus module.

Usage:
    from apps.core.services.agent_bus_bridge import send_to_bus, check_inbox

    send_to_bus('alice', 'noelle', 'Order fulfilled', body='Invoice #1234')
    messages = check_inbox('alice')
"""

import json
import os
import time

import psycopg2
import psycopg2.extras


def _connect():
    """Connect to the allie database (not commerce_expert)."""
    return psycopg2.connect(
        dbname="allie",
        user="williamjames",
        host="localhost",
    )


def _now_ms():
    return int(time.time() * 1000)


def send_to_bus(from_agent, to_agent, subject, body="", priority=0,
                category=None, context=None):
    """Send a message from Alice (or any WC3 agent) to the agent bus.

    Returns dict with message id on success, or error info on failure.
    """
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO agent_messages
                   (dt_created, from_agent, to_agent, subject, body,
                    priority, category, context)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (_now_ms(), from_agent, to_agent, subject, body,
                 priority, category,
                 json.dumps(context) if context else "{}"),
            )
            msg_id = cur.fetchone()[0]
            conn.commit()
            return {"success": True, "message_id": msg_id}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def check_inbox(agent_name="alice", unread_only=True):
    """Check an agent's inbox on the message bus.

    Returns dict with messages list on success, or error info on failure.
    """
    conn = _connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            where = "WHERE (to_agent = %s OR to_agent = 'all')"
            params = [agent_name]
            if unread_only:
                where += " AND NOT read"
            where += " ORDER BY dt_created DESC LIMIT 50"
            cur.execute(
                f"""SELECT id, dt_created, from_agent, to_agent, subject,
                           body, priority, category, context
                    FROM agent_messages {where}""",
                params,
            )
            messages = [dict(row) for row in cur.fetchall()]
            return {"success": True, "messages": messages, "count": len(messages)}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()
