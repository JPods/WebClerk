"""
Pydantic schemas for Sync Bundle JSON envelopes.

Inherits standard bases. Add model-specific fields only.

Import bundles carry an ImportBundleHeader (from connection schema)
that must be signed off before processing. Athena reviews for hidden harms.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef
from .connection import ImportBundleHeader


# -- .config ----------------------------------------------------------------

class BundleConfig(ConfigBase):
    """Bundle configuration — includes import header when channel='import'."""
    import_header: Optional[ImportBundleHeader] = None


# -- .metadata (inherits MetadataBase) --------------------------------------

class BundleMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class BundlePrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class BundleRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None
