"""
Pydantic schemas for Payment JSON envelopes.

These define exactly what goes in payment.metadata, payment.prefs, payment.refs.
Validation on write. Documentation by existence. Alice reads these.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import (
    AuditEntry, ConfigBase, GlStage, ImportProvenance, MetadataBase,
    ReconciliationData, RecordPrefsBase, RefsBase, SourceRef,
)


# ── Payment .config ─────────────────────────────────────────────────

class PaymentConfig(ConfigBase):
    """Structural config on a Payment record."""

    class Config:
        extra = "forbid"


# ── Payment .metadata ───────────────────────────────────────────────

class PaymentMetadata(MetadataBase):
    """System-written data on a Payment record."""
    gl_accounts: Optional[GlStage] = None
    reconciliation: Optional[ReconciliationData] = None
    gateway_metadata: dict = Field(default_factory=dict)
    processing_fees: list[dict] = Field(default_factory=list)
    audit_trail: list[AuditEntry] = Field(default_factory=list)
    import_data: Optional[ImportProvenance] = None


# ── Payment .prefs ──────────────────────────────────────────────────

class PaymentPrefs(RecordPrefsBase):
    """User-initiated data on a Payment record.

    Rare on payments — most prefs are installation-level (Setting.prefs.defaults).
    Record-level prefs are for user-defined fields and personal tags only.
    """
    pass


# ── Payment .refs ───────────────────────────────────────────────────

class PaymentRefsLinks(BaseModel):
    """Denormalized relationship cache. FKs are authoritative — these are for fast queries."""
    customer_id: Optional[int] = None
    vendor_id: Optional[int] = None
    contact_id: Optional[int] = None
    invoice_ids: list[int] = Field(default_factory=list)
    order_ids: list[int] = Field(default_factory=list)


class PaymentRefs(RefsBase):
    """Relationship pointers on a Payment record."""
    links: PaymentRefsLinks = Field(default_factory=PaymentRefsLinks)  # type: ignore[assignment]
    source: Optional[SourceRef] = None


# ── Setting(payment, field_access).prefs ────────────────────────────

class PaymentSettingDefaults(BaseModel):
    """Installation-level defaults for new Payment records.
    Lives in Setting(parent_model='payment', purpose='wc:field_access').prefs.defaults
    """
    type: str = 'expense'
    method: str = ''
    category: str = ''


class PaymentSettingPrefs(BaseModel):
    """Full prefs structure for the payment field_access Setting."""
    defaults: PaymentSettingDefaults = Field(default_factory=PaymentSettingDefaults)
