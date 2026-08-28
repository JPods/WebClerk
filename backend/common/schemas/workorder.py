"""
Pydantic schemas for WorkOrder JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import (
    ConfigBase, MetadataBase, RecordPrefsBase, RefsBase,
    CommentsBase, ActionsBase, SourceRef,
)


class WorkorderConfig(ConfigBase):
    pass


class WorkorderMetadata(MetadataBase):
    pass


class WorkorderPrefs(RecordPrefsBase):
    pass


class WorkorderRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


class WorkorderComments(CommentsBase):
    pass


class WorkorderActions(ActionsBase):
    pass
