"""
Pydantic schemas for Payment JSON envelopes.

These define exactly what goes in payment.metadata, payment.prefs, payment.refs.
Validation on write. Documentation by existence. Alice reads these.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import (
    AuditEntry, ConfigBase, GlStage, ImportProvenance, MetadataBase,
    ReconciliationData, RecordPrefsBase, RefsBase, SourceRef,
)


# ── Payment gateway (Setting-level registry) ────────────────────────
#
# Setting is the menu — scannable, one line per gateway.
# Connection.config carries the depth: rules, statement_source,
# credentials, operational details.

class GatewayEntry(BaseModel):
    """One payment gateway in the config.gateway array.

    Thin registry entry. Denormalized from Connection for scanning.
    Manual gateways (wire/check): connection_id is null, type is 'manual'.
    Spreedly gateways: connection_id points to a Connection record.
    Payment.method and StatementLine.source both map to gateway.name.
    """
    name: str                                     # unique key — matches Payment.method
    type: str = 'manual'                          # manual | spreedly
    account: str = ''                             # display label: "Wells Fargo ****3425"
    gl_account: str = ''                          # cash-side GL account
    is_default: bool = False
    # Connection pointer — denormalized for scanning
    connection_id: Optional[int] = None           # null = manual, no API
    connection_purpose: str = ''                  # Connection.purpose (e.g. 'wc:spreedly')
    connection_status: str = ''                   # Connection.status (active/inactive/...)

    class Config:
        extra = "forbid"


class PaymentGatewayConfig(BaseModel):
    """Setting(purpose='wc:payment_gateway').config structure.

    gateway[] is the scannable registry.
    token_rule and currency are installation-level.
    """
    gateway: list[GatewayEntry] = Field(default_factory=list)
    token_rule: dict = Field(default_factory=dict)
    currency: str = 'USD'
    test_mode: bool = True

    class Config:
        extra = "forbid"


# ── Payment .config (record-level) ──────────────────────────────────

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
    contact: list = Field(default_factory=list)
    item: list = Field(default_factory=list)

    class Config:
        extra = "forbid"


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

    class Config:
        extra = "forbid"


class PaymentSettingPrefs(BaseModel):
    """Full prefs structure for the payment field_access Setting."""
    defaults: PaymentSettingDefaults = Field(default_factory=PaymentSettingDefaults)

    class Config:
        extra = "forbid"
