"""
Pydantic schemas for Exchange Rate JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# -- .config ----------------------------------------------------------------

class ExchangeRateConfig(ConfigBase):
    pass


# -- .metadata (inherits MetadataBase) --------------------------------------

class ExchangeRateMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class ExchangeRatePrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class ExchangeRateRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None
