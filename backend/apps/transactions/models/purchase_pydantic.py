"""
Pydantic schemas for Purchase JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef
from common.schemas.transaction_envelopes import TransactionSignoff


# -- .capital_asset ---------------------------------------------------------

DEPRECIATION_METHOD_CHOICES = ('straight_line', 'declining_balance', 'units_of_production')

class CapitalAsset(BaseModel):
    """Schema for Purchase.capital_asset JSON field."""
    asset_name: str = ''
    useful_life_months: Optional[int] = None
    salvage_value: Optional[float] = None
    depreciation_method: str = 'straight_line'
    placed_in_service: Optional[str] = None       # ISO date string YYYY-MM-DD
    location: str = ''
    serial_number: str = ''
    category: str = ''                             # user-defined asset category
    notes: str = ''


# -- .config ----------------------------------------------------------------

class PurchaseConfig(ConfigBase):
    """Purchase config. Signoff written by validate_status.py."""
    signoff: Optional[TransactionSignoff] = None


# -- .metadata (inherits MetadataBase) --------------------------------------

class PurchaseMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class PurchasePrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class PurchaseRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None
