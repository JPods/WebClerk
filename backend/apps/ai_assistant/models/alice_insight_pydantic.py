"""
Pydantic schemas for AliceInsight JSON envelopes.

AliceInsight — per-agent per-contact per-subject insight records.
Config varies by subject_type so uses extra='allow'.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import (
    ConfigBase, MetadataBase, RecordPrefsBase, RefsBase,
    CommentsBase, ActionsBase, SourceRef,
)


# ── .config ──────────────────────────────────────────────────────────

class AliceInsightConfig(ConfigBase):
    """Config varies by subject_type — allow extra fields."""

    class Config:
        extra = 'allow'


# ── .metadata ────────────────────────────────────────────────────────

class AliceInsightMetadata(MetadataBase):
    """Standard metadata inherited."""
    pass


# ── .prefs ───────────────────────────────────────────────────────────

class AliceInsightPrefs(RecordPrefsBase):
    """Standard prefs inherited."""
    pass


# ── .refs ────────────────────────────────────────────────────────────

class AliceInsightRefs(RefsBase):
    """Relationship cache. contact_id is a value field, not FK."""
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


# ── .comments ────────────────────────────────────────────────────────

class AliceInsightComments(CommentsBase):
    """Standard comments inherited."""
    pass


# ── .actions ─────────────────────────────────────────────────────────

class AliceInsightActions(ActionsBase):
    """Standard actions inherited."""
    pass


# ── Setting defaults ─────────────────────────────────────────────────

class AliceInsightSettingDefaults(BaseModel):
    status: str = "active"
