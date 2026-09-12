"""
Pydantic schemas for Erosion JSON envelopes.

Erosion — value-loss tracker (returns, breakage, shrinkage, etc.).
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import (
    ConfigBase, MetadataBase, RecordPrefsBase, RefsBase,
    CommentsBase, ActionsBase, SourceRef,
)


# ── .config ──────────────────────────────────────────────────────────

class ErosionConfig(ConfigBase):
    """Erosion-specific config. extra='forbid' inherited."""
    pass


# ── .metadata ────────────────────────────────────────────────────────

class ErosionMetadata(MetadataBase):
    """Standard metadata inherited."""
    pass


# ── .prefs ───────────────────────────────────────────────────────────

class ErosionPrefs(RecordPrefsBase):
    """Standard prefs inherited."""
    pass


# ── .refs ────────────────────────────────────────────────────────────

class ErosionRefs(RefsBase):
    """Relationship cache. FKs (org, contact) are truth."""
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


# ── .comments ────────────────────────────────────────────────────────

class ErosionComments(CommentsBase):
    """Standard comments inherited."""
    pass


# ── .actions ─────────────────────────────────────────────────────────

class ErosionActions(ActionsBase):
    """Standard actions inherited."""
    pass


# ── Setting defaults ─────────────────────────────────────────────────

class ErosionSettingDefaults(BaseModel):
    status: str = "draft"
