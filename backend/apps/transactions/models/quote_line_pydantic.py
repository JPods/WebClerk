"""
Pydantic schemas for Quote Line JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef
from common.schemas.transaction_envelopes import LineContact


# -- .config ----------------------------------------------------------------

class QuoteLineConfig(ConfigBase):
    pass


# -- .metadata (inherits MetadataBase) --------------------------------------

class QuoteLineMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class QuoteLinePrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class QuoteLineRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    contacts: list[LineContact] = Field(default_factory=list)   # readme 109 P6
    source: Optional[SourceRef] = None
