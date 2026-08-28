"""
Pydantic schemas for Workspace JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import (
    ConfigBase, MetadataBase, RecordPrefsBase, RefsBase,
    CommentsBase, ActionsBase, SourceRef,
)


class WorkspaceConfig(ConfigBase):
    pass


class WorkspaceMetadata(MetadataBase):
    pass


class WorkspacePrefs(RecordPrefsBase):
    pass


class WorkspaceRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


class WorkspaceComments(CommentsBase):
    pass


class WorkspaceActions(ActionsBase):
    pass
