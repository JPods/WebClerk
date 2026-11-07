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


# -- Setting.config.defaults.fields (readme 106: each model's own defaults) ----

class WorkOrderSettingDefaults(BaseModel):
    """What a new workorder is born with when nobody says (core/services/defaults.py)."""
    terms: str = ""
    price_level: str = ""
    dt_needed_days: int = 0
    priority: str = ""
    source_name: str = ""
    ship_via: str = ""

    class Config:
        extra = "forbid"
