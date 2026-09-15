"""
Pydantic schemas for WorkOrder JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import (
    ConfigBase, MetadataBase, RecordPrefsBase, RefsBase,
    CommentsBase, ActionsBase, SourceRef,
)
from common.schemas.transaction_envelopes import TransactionSignoff


class WorkorderConfig(ConfigBase):
    """WorkOrder config. Signoff written by validate_status.py."""
    signoff: Optional[TransactionSignoff] = None


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
