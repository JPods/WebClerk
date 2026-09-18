"""
Pydantic schemas for Cash, CashMethod, and Term JSON envelopes.

Mirrors cash.py — all three models in one file.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import (
    AuditEntry, ConfigBase, GlStage, ImportProvenance, MetadataBase,
    ReconciliationData, RecordPrefsBase, RefsBase, SourceRef,
)


# ═══════════════════════════════════════════════════════════════════════
# Cash
# ═══════════════════════════════════════════════════════════════════════

# ── Cash gateway (Setting-level registry) ────────────────────────

class GatewayEntry(BaseModel):
    """One cash gateway in the config.gateway array.

    Thin registry entry. Denormalized from Connection for scanning.
    Manual gateways (wire/check): connection_id is null, type is 'manual'.
    Spreedly gateways: connection_id points to a Connection record.
    Cash.method and StatementLine.source both map to gateway.name.
    """
    name: str                                     # unique key — matches Cash.method
    type: str = 'manual'                          # manual | spreedly
    account: str = ''                             # display label: "Wells Fargo ****3425"
    gl_account: str = ''                          # cash-side GL account
    is_default: bool = False
    connection_id: Optional[int] = None           # null = manual, no API
    connection_purpose: str = ''                  # Connection.purpose (e.g. 'wc:spreedly')
    connection_status: str = ''                   # Connection.status (active/inactive/...)

    class Config:
        extra = "forbid"


class CashGatewayConfig(BaseModel):
    """Setting(purpose='wc:cash_gateway').config structure.

    gateway[] is the scannable registry.
    token_rule and currency are installation-level.
    """
    gateway: list[GatewayEntry] = Field(default_factory=list)
    token_rule: dict = Field(default_factory=dict)
    currency: str = 'USD'
    test_mode: bool = True

    class Config:
        extra = "forbid"


# ── Cash .config (record-level) ──────────────────────────────────

class CashConfig(ConfigBase):
    """Structural config on a Cash record."""

    class Config:
        extra = "forbid"


# ── Cash .metadata ───────────────────────────────────────────────

class CashMetadata(MetadataBase):
    """System-written data on a Cash record."""
    gl_accounts: Optional[GlStage] = None
    reconciliation: Optional[ReconciliationData] = None
    gateway_metadata: dict = Field(default_factory=dict)
    processing_fees: list[dict] = Field(default_factory=list)
    audit_trail: list[AuditEntry] = Field(default_factory=list)
    import_data: Optional[ImportProvenance] = None


# ── Cash .prefs ──────────────────────────────────────────────────

class CashPrefs(RecordPrefsBase):
    """User-initiated data on a Cash record.

    Rare on cash — most prefs are installation-level (Setting.prefs.defaults).
    Record-level prefs are for user-defined fields and personal tags only.
    """
    pass


# ── Cash .refs ───────────────────────────────────────────────────

class CashRefsLinks(BaseModel):
    """Denormalized relationship cache. FKs are authoritative — these are for fast queries."""
    customer_id: Optional[int] = None
    vendor_id: Optional[int] = None
    contact_id: Optional[int] = None
    invoice_ids: list[int] = Field(default_factory=list)
    receipt_ids: list[int] = Field(default_factory=list)
    order_ids: list[int] = Field(default_factory=list)
    contact: list = Field(default_factory=list)
    item: list = Field(default_factory=list)

    class Config:
        extra = "forbid"


class CashRefs(RefsBase):
    """Relationship pointers on a Cash record."""
    links: CashRefsLinks = Field(default_factory=CashRefsLinks)  # type: ignore[assignment]
    source: Optional[SourceRef] = None


# ── Dual Pricing (Setting-level config) ───────────────────────────

class DualPricingConfig(BaseModel):
    """Setting(purpose='wc:dual_pricing').config structure.

    Dual pricing / cash discount program. The merchant stores one price
    (the cash price). Card customers see a higher total. Legal in all
    50 US states when framed as a cash discount, not a surcharge.
    """
    enabled: bool = False
    card_rate: float = Field(
        3.5, ge=0, le=4.0,
        description="Card surcharge rate as percentage (e.g. 3.5 = 3.5%)",
    )
    disclosure_text: str = Field(
        "Save {rate}% by paying with ACH, check, or cash.",
        description="Shown at checkout. {rate} is replaced with card_rate.",
    )
    gl_account: str = Field(
        '',
        description="GL account for surcharge revenue; blank posts to the company other_income account",
    )
    exempt_methods: list[str] = Field(
        default_factory=lambda: ['cash', 'check', 'ach', 'wire', 'debit'],
        description="Cash methods that receive the cash (base) price",
    )
    apply_before_tax: bool = Field(
        True,
        description="If True, surcharge is computed on subtotal before tax. "
                    "If False, computed on grand total.",
    )

    class Config:
        extra = "forbid"


class DualPricingProjection(BaseModel):
    """Computed dual pricing for a specific transaction.

    Returned by the dual_pricing service. Not stored — computed on demand.
    """
    enabled: bool = False
    cash_total: float = 0.0
    card_total: float = 0.0
    card_rate: float = 0.0
    adjustment_amount: float = 0.0
    disclosure_text: str = ''

    class Config:
        extra = "forbid"


class CashSettingDefaults(BaseModel):
    """Installation-level defaults for new Cash records."""
    type: str = 'cash_out'
    method: str = ''
    category: str = ''

    class Config:
        extra = "forbid"


class CashSettingPrefs(BaseModel):
    """Full prefs structure for the cash field_access Setting."""
    defaults: CashSettingDefaults = Field(default_factory=CashSettingDefaults)

    class Config:
        extra = "forbid"

