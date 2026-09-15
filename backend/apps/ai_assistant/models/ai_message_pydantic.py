"""
Pydantic schemas for AiMessage JSON envelopes.

AiMessage — unified actor-to-actor message (agent, user, system).
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import (
    ConfigBase, MetadataBase, RecordPrefsBase, RefsBase,
    CommentsBase, ActionsBase, SourceRef,
)


# ── .config ──────────────────────────────────────────────────────────

class AiMessageConfig(ConfigBase):
    """AiMessage-specific config. extra='forbid' inherited."""
    pass


# ── .metadata ────────────────────────────────────────────────────────

class AiMessageMetadata(MetadataBase):
    """Standard metadata inherited."""
    pass


# ── .prefs ───────────────────────────────────────────────────────────

class AiMessagePrefs(RecordPrefsBase):
    """Standard prefs inherited."""
    pass


# ── .refs ────────────────────────────────────────────────────────────

class AiMessageRefs(RefsBase):
    """Relationship cache. Parent/forward_of are self-FKs."""
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


# ── .comments ────────────────────────────────────────────────────────

class AiMessageComments(CommentsBase):
    """Standard comments inherited."""
    pass


# ── .actions ─────────────────────────────────────────────────────────

class AiMessageActions(ActionsBase):
    """Standard actions inherited."""
    pass


# ── Setting defaults ─────────────────────────────────────────────────

class AiMessageSettingDefaults(BaseModel):
    status: str = "draft"
