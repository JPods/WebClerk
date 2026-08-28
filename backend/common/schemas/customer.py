"""
Pydantic schemas for Customer JSON envelopes.

Inherits standard bases. Customer = the commercial relationship.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# ── .config ────────────────────────────────────────────────────────

class CustomerConfig(ConfigBase):
    pass


# ── .metadata (inherits MetadataBase) ─────────────────────────────

class CustomerMetadata(MetadataBase):
    """Customer-specific metadata. Standard fields inherited."""
    pass  # no additional fields yet — standard base covers it


# ── .prefs ─────────────────────────────────────────────────────────

class CustomerPrefs(RecordPrefsBase):
    pass


# ── .refs ──────────────────────────────────────────────────────────

class CustomerRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    parents: list = Field(default_factory=list)
    depends_on: dict = Field(default_factory=dict)
    related_ids: list[int] = Field(default_factory=list)
    source: Optional[SourceRef] = None


# ── Setting defaults ──────────────────────────────────────────────

class CustomerSettingDefaults(BaseModel):
    terms: str = ""
    price_level: str = ""
    is_active: bool = True

    class Config:
        extra = "forbid"
