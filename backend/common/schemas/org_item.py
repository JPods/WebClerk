"""
Pydantic schemas for Org Item JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# -- .config ----------------------------------------------------------------

class OrgItemConfig(ConfigBase):
    """Inventory management parameters for this org's relationship to an item."""
    quantity_minimum: Optional[float] = None
    quantity_maximum: Optional[float] = None
    inventory_frequency: Optional[str] = None    # daily, weekly, 30d, etc.
    dt_next_check: Optional[int] = None          # epoch ms
    dt_last_check: Optional[int] = None          # epoch ms
    count_last_check: Optional[float] = None
    checked_by_attention: bool = False
    checked_by_id: Optional[int] = None

    class Config:
        extra = "forbid"


# -- .metadata (inherits MetadataBase) --------------------------------------

class OrgItemMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class OrgItemPrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class OrgItemRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None
