"""
Pydantic schemas for Receipt JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# -- .config ----------------------------------------------------------------

class ReceiptConfig(ConfigBase):
    pass


# -- .metadata (inherits MetadataBase) --------------------------------------

class ReceiptMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class ReceiptPrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class ReceiptRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


# -- Setting.config.defaults.fields (readme 106: each model's own defaults) ----

class ReceiptSettingDefaults(BaseModel):
    """What a new receipt is born with when nobody says (core/services/defaults.py)."""
    terms: str = ""
    price_level: str = ""
    dt_needed_days: int = 0
    priority: str = ""
    source_name: str = ""
    ship_via: str = ""

    class Config:
        extra = "forbid"
