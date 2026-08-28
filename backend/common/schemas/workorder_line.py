"""
Pydantic schemas for WorkOrderLine JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import (
    ConfigBase, MetadataBase, RecordPrefsBase, RefsBase,
    CommentsBase, ActionsBase, SourceRef,
)


class WorkorderLineConfig(ConfigBase):
    pass


class WorkorderLineMetadata(MetadataBase):
    pass


class WorkorderLinePrefs(RecordPrefsBase):
    pass


class WorkorderLineRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


class WorkorderLineComments(CommentsBase):
    pass


class WorkorderLineActions(ActionsBase):
    pass
