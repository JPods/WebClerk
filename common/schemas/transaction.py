"""
Pydantic schemas for Transaction JSON envelopes (Order, Invoice, Proposal, Purchase).

Inherits MetadataBase + FinancialMetadataMixin.
All four transaction types share the same envelope structure.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import (
    MetadataBase, FinancialMetadataMixin,
    RecordPrefsBase, RefsBase, SourceRef,
)


# ── .config ────────────────────────────────────────────────────────

class ShipTo(BaseModel):
    """Shipping address snapshot — copied at order time."""
    attention: str = ""
    company: str = ""
    address1: str = ""
    address2: str = ""
    city: str = ""
    state: str = ""
    zip: str = ""
    country: str = ""
    phone: str = ""
    email: str = ""


class TransactionConfig(BaseModel):
    ship_to: ShipTo = Field(default_factory=ShipTo)

    class Config:
        extra = "allow"


# ── .metadata (inherits MetadataBase + FinancialMetadataMixin) ────

class TransactionMetadata(MetadataBase, FinancialMetadataMixin):
    """Transaction metadata. Standard + financial fields."""
    pass


# ── .prefs ─────────────────────────────────────────────────────────

class TransactionPrefs(RecordPrefsBase):
    pass


# ── .refs ──────────────────────────────────────────────────────────

class TransactionRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    parents: list = Field(default_factory=list)
    depends_on: list = Field(default_factory=list)
    related_ids: list[int] = Field(default_factory=list)
    source: Optional[SourceRef] = None
