"""
Pydantic schemas for Rep JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import ConfigBase, OrgDefaults, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# -- .config ----------------------------------------------------------------

class RepConfig(ConfigBase):
    # The org's own defaults for its documents (readme 106): what it has no column for, and
    # its formatting (party_fill, utils/formatting).
    defaults: OrgDefaults = Field(default_factory=OrgDefaults)


# -- .metadata (inherits MetadataBase) --------------------------------------

class RepMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class RepPrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class RepRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


# -- Setting.config.defaults.fields (readme 106: each model's own defaults) ----

class RepSettingDefaults(BaseModel):
    """What a new rep is born with when nobody says (core/services/defaults.py)."""
    terms: str = ""
    price_level: str = ""
    source_name: str = ""
    is_active: bool = True

    class Config:
        extra = "forbid"
