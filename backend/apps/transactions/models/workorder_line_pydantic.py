"""
Pydantic schemas for WorkOrderLine JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import (
    ConfigBase, MetadataBase, RecordPrefsBase, RefsBase,
    CommentsBase, ActionsBase, SourceRef,
)


class WorkorderLineConfig(ConfigBase):
    pass


class WorkorderLineMetadata(MetadataBase):
    pass


class WorkorderLinePrefs(RecordPrefsBase):
    pass


class BomRef(BaseModel):
    """Where an expanded line came from (workorder plan): written by expand, never by a request."""
    bom_id: Optional[int] = None
    root_line_id: Optional[int] = None
    parent_line_id: Optional[int] = None
    depth: Optional[int] = None
    role: str = ''                 # component | subassembly | subassembly_used | scrap
    of_line_id: Optional[int] = None


class BomExpand(BaseModel):
    """How a build line was expanded: depth 1 (one level, editable) or 0 (full BOM, locked)."""
    depth: Optional[int] = None


class WorkorderLineRefs(RefsBase):
    bom: Optional[BomRef] = None
    bom_expand: Optional[BomExpand] = None
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


class WorkorderLineComments(CommentsBase):
    pass


class WorkorderLineActions(ActionsBase):
    pass
