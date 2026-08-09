"""
Pydantic schemas for Serial Log JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# -- .config ----------------------------------------------------------------

class SerialLogConfig(ConfigBase):
    """Audit context for serial state changes."""
    doc_type: str = ''                       # purchase, order, invoice
    doc_id: Optional[int] = None
    status_before: str = ''
    notes: str = ''

    class Config:
        extra = "allow"  # action-specific context varies


# -- .metadata (inherits MetadataBase) --------------------------------------

class SerialLogMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class SerialLogPrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class SerialLogRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None
