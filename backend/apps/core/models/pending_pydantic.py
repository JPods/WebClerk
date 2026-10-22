"""
Pydantic schemas for Pending JSON envelopes.

Pending — lightweight ephemeral queue (CoreModel, config only).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from common.schemas.envelopes import ConfigBase, MetadataBase


# ── .config (CoreModel — only envelope) ──────────────────────────────

class PendingConfig(ConfigBase):
    """Pending config. Changes payload lives on the `changes` field.

    What a pending is for goes in the `purpose` scalar and which record in
    `model_name` / `record_id` — never duplicated here.
    """
    # Stale inventory alert de-dup (apps/products/tasks.py stale check).
    stale_alert_sent: bool = False
    stale_alert_time: Optional[str] = None   # UTC ISO-8601


# ── .metadata — what has happened to the Pending since it was made ──────

class IncrementalApply(BaseModel):
    """One partial apply (Bill, 2026-09-21); remaining = the change's qty − Σ qty.
    Writer: apps/products/services/inventory/inventory_layers.py."""
    qty: float = 0
    dt: Optional[int] = None
    unit_cost: Optional[float] = None
    layer_id: Optional[int] = None
    source_pending_id: Optional[int] = None
    gl_journal_ids: list[int] = []
    variance: Optional[float] = None


class PendingMetadata(MetadataBase):
    incremental_apply: list[IncrementalApply] = []
