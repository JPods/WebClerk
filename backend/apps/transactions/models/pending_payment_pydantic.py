"""
Pydantic schemas for PendingPaymentApplication JSON envelopes.

PendingPaymentApplication — CoreModel (config only). Payment/invoice
FKs, amount, state, reason on model fields.
"""
from __future__ import annotations

from common.schemas.envelopes import ConfigBase


# ── .config (CoreModel — only envelope) ──────────────────────────────

class PendingPaymentApplicationConfig(ConfigBase):
    """PendingPaymentApplication config. Transaction data on model fields."""
    pass
