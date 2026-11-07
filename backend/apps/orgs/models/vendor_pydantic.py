"""
Pydantic schemas for Vendor JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import ConfigBase, OrgDefaults, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# -- .config ----------------------------------------------------------------

class VendorConfig(ConfigBase):
    # The org's own defaults for its documents (readme 106): what it has no column for, and
    # its formatting (party_fill, utils/formatting).
    defaults: OrgDefaults = Field(default_factory=OrgDefaults)


# -- .metadata (inherits MetadataBase) --------------------------------------

class VendorMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class VendorPrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class VendorRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


# -- Setting.config.defaults.fields (readme 106: each model's own defaults) ----

class VendorSettingDefaults(BaseModel):
    """What a new vendor is born with when nobody says (core/services/defaults.py)."""
    terms: str = ""
    price_level: str = ""
    source_name: str = ""
    is_active: bool = True

    class Config:
        extra = "forbid"
