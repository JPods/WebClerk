"""
Pydantic schemas for Touch JSON envelopes.

Touch records log communication events (calls, emails, visits, texts, meetings).
Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# ── .config ────────────────────────────────────────────────────────

class TouchConfig(ConfigBase):
    class Config:
        extra = 'allow'


# ── .metadata (inherits MetadataBase) ──────────────────────────────

class TouchMetadata(MetadataBase):
    pass


# ── .prefs (inherits RecordPrefsBase) ──────────────────────────────

class TouchPrefs(RecordPrefsBase):
    pass


# ── .refs (inherits RefsBase) ─────────────────────────────────────

class TouchRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None
