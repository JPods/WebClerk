"""
Pydantic schemas for Item JSON envelopes.

Inherits standard bases. Item has the richest prefs (import, display, shipping, variants).
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# ── .config ────────────────────────────────────────────────────────

class ItemConfig(ConfigBase):
    pass


# ── .metadata (inherits MetadataBase) ─────────────────────────────

class ItemMetadata(MetadataBase):
    """Item-specific metadata. Standard fields inherited."""
    variants: Optional[dict] = None    # system-managed variant matrix


# ── .prefs ─────────────────────────────────────────────────────────

class ItemPrefs(RecordPrefsBase):
    """Item prefs — import rules, display, shipping, variants, restrictions."""
    import_prefs: Optional[dict] = Field(None, alias="import")
    import_details: dict = Field(default_factory=dict)
    display: Optional[dict] = None
    shipping: Optional[dict] = None
    variants: Optional[dict] = None
    restrictions: Optional[dict] = None


# ── .refs ──────────────────────────────────────────────────────────

class ItemRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    variants: list = Field(default_factory=list)
    depends_on: list = Field(default_factory=list)
    related_ids: list[int] = Field(default_factory=list)
    source: Optional[SourceRef] = None


# ── Setting defaults ──────────────────────────────────────────────

class ItemSettingDefaults(BaseModel):
    status: str = "active"
    is_active: bool = True
    type: str = ""
    category: str = ""
