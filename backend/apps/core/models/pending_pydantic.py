"""
Pydantic schemas for Pending JSON envelopes.

Pending — lightweight ephemeral queue (CoreModel, config only).
"""
from __future__ import annotations

from common.schemas.envelopes import ConfigBase


# ── .config (CoreModel — only envelope) ──────────────────────────────

class PendingConfig(ConfigBase):
    """Pending config. Changes payload on model field."""
    pass
