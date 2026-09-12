"""
Pydantic schemas for Episode JSON envelopes.

Episode — episodic memory for AI assistant. Stores observations,
incidents, and learnings with review workflow.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import (
    ConfigBase, MetadataBase, RecordPrefsBase, RefsBase,
    CommentsBase, ActionsBase, SourceRef,
)


# ── .config ──────────────────────────────────────────────────────────

class EpisodeConfig(ConfigBase):
    """Episode-specific config. extra='forbid' inherited."""
    pass


# ── .metadata ────────────────────────────────────────────────────────

class EpisodeMetadata(MetadataBase):
    """Standard metadata inherited."""
    pass


# ── .prefs ───────────────────────────────────────────────────────────

class EpisodePrefs(RecordPrefsBase):
    """Standard prefs inherited."""
    pass


# ── .refs ────────────────────────────────────────────────────────────

class EpisodeRefs(RefsBase):
    """Relationship cache — related episodes tracked via model fields."""
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


# ── .comments ────────────────────────────────────────────────────────

class EpisodeComments(CommentsBase):
    """Standard comments inherited."""
    pass


# ── .actions ─────────────────────────────────────────────────────────

class EpisodeActions(ActionsBase):
    """Standard actions inherited."""
    pass


# ── Setting defaults ─────────────────────────────────────────────────

class EpisodeSettingDefaults(BaseModel):
    status: str = "draft"
