"""
Pydantic schemas for Pending JSON envelopes.

Pending — lightweight ephemeral queue (CoreModel, config only).
"""
from __future__ import annotations

from typing import Optional

from common.schemas.envelopes import ConfigBase


# ── .config (CoreModel — only envelope) ──────────────────────────────

class PendingConfig(ConfigBase):
    """Pending config. Changes payload lives on the `changes` field.

    What a pending is for goes in the `purpose` scalar and which record in
    `model_name` / `record_id` — never duplicated here.
    """
    # Keyword re-index queue: fields whose change triggered the enqueue
    # (writer: apps/docs/models/document.py save()).
    tracked_fields: list[str] = []
    # Stale inventory alert de-dup (apps/products/tasks.py stale check).
    stale_alert_sent: bool = False
    stale_alert_time: Optional[str] = None   # UTC ISO-8601
