"""
Pydantic schemas for JournalBatch JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import (
    ConfigBase, MetadataBase, RecordPrefsBase, RefsBase,
    CommentsBase, ActionsBase, SourceRef,
)


class JournalBatchConfig(ConfigBase):
    pass


class JournalBatchMetadata(MetadataBase):
    pass


class JournalBatchPrefs(RecordPrefsBase):
    pass


class JournalBatchRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


class JournalBatchComments(CommentsBase):
    pass


class JournalBatchActions(ActionsBase):
    pass
