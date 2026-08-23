"""
Pydantic schemas for OtherOrg JSON envelopes.

Other Org is a catch-all org type for organizations that aren't
customers, vendors, manufacturers, or reps.
Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# ── .config ────────────────────────────────────────────────────────

class OtherOrgConfig(ConfigBase):
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
