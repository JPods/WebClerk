"""
Pydantic schemas for RefsMismatchLog JSON envelopes.

RefsMismatchLog — diagnostic record when FK and refs disagree.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import (
    ConfigBase, MetadataBase, RecordPrefsBase, RefsBase,
    CommentsBase, ActionsBase, SourceRef,
)


# ── .config ──────────────────────────────────────────────────────────

class RefsMismatchLogConfig(ConfigBase):
    """RefsMismatchLog config. Diff data on model fields."""
    pass


# ── .metadata ────────────────────────────────────────────────────────

class RefsMismatchLogMetadata(MetadataBase):
    pass


# ── .prefs ───────────────────────────────────────────────────────────

class RefsMismatchLogPrefs(RecordPrefsBase):
    pass


# ── .refs ────────────────────────────────────────────────────────────

class RefsMismatchLogRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


# ── .comments ────────────────────────────────────────────────────────

class RefsMismatchLogComments(CommentsBase):
    pass


# ── .actions ─────────────────────────────────────────────────────────

class RefsMismatchLogActions(ActionsBase):
    pass


# ── Setting defaults ─────────────────────────────────────────────────

class RefsMismatchLogSettingDefaults(BaseModel):
    status: str = "active"
