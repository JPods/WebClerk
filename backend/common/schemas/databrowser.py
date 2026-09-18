"""
Pydantic schemas for DataBrowser JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# -- .config ----------------------------------------------------------------

class DatabrowserConfig(ConfigBase):
    pass


# -- .metadata (inherits MetadataBase) --------------------------------------

class DatabrowserMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class DatabrowserPrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class DatabrowserRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None
