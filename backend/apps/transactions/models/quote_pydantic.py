"""
Pydantic schemas for Quote JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef
from common.schemas.transaction_envelopes import TransactionSignoff


# -- .config ----------------------------------------------------------------

class QuoteConfig(ConfigBase):
    """Quote config. Signoff written by validate_status.py."""
    signoff: Optional[TransactionSignoff] = None


# -- .metadata (inherits MetadataBase) --------------------------------------

class QuoteMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class QuotePrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class QuoteRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


# -- Setting.config.defaults.fields (readme 106: each model's own defaults) ----

class QuoteSettingDefaults(BaseModel):
    """What a new quote is born with when nobody says (core/services/defaults.py)."""
    terms: str = ""
    price_level: str = ""
    dt_needed_days: int = 0
    priority: str = ""
    source_name: str = ""
    ship_via: str = ""

    class Config:
        extra = "forbid"
