"""
Pydantic schemas for Order Line JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef
from common.schemas.transaction_envelopes import LineContact


# -- .config ----------------------------------------------------------------

class OrderLineConfig(ConfigBase):
    pass


# -- .metadata (inherits MetadataBase) --------------------------------------

class OrderLineMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class OrderLinePrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class OrderLineRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    contacts: list[LineContact] = Field(default_factory=list)   # readme 109 P6
    source: Optional[SourceRef] = None
