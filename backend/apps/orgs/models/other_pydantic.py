"""
Pydantic schemas for OtherOrg JSON envelopes.

Other Org is a catch-all org type for organizations that aren't
customers, vendors, manufacturers, or reps.
Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import ConfigBase, OrgDefaults, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# ── .config ────────────────────────────────────────────────────────

class OtherOrgConfig(ConfigBase):
    defaults: OrgDefaults = Field(default_factory=OrgDefaults)

    class Config:
        extra = 'allow'


# ── .metadata (inherits MetadataBase) ──────────────────────────────

class OtherOrgMetadata(MetadataBase):
    pass


# ── .prefs (inherits RecordPrefsBase) ──────────────────────────────

class OtherOrgPrefs(RecordPrefsBase):
    pass


# ── .refs (inherits RefsBase) ─────────────────────────────────────

class OtherOrgRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


# -- Setting.config.defaults.fields (readme 106: each model's own defaults) ----

class OtherOrgSettingDefaults(BaseModel):
    """What a new other is born with when nobody says (core/services/defaults.py)."""
    terms: str = ""
    price_level: str = ""
    source_name: str = ""
    is_active: bool = True

    class Config:
        extra = "forbid"
