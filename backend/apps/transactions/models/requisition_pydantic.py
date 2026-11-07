"""
Pydantic schemas for Requisition JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# -- .config ----------------------------------------------------------------

class RequisitionConfig(ConfigBase):
    pass


# -- .metadata (inherits MetadataBase) --------------------------------------

class RequisitionMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class RequisitionPrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class RequisitionRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


# -- Setting.config.defaults.fields (readme 106: each model's own defaults) ----

class RequisitionSettingDefaults(BaseModel):
    """What a new requisition is born with when nobody says (core/services/defaults.py)."""
    status: str = ""

    class Config:
        extra = "forbid"
