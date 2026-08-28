"""
Pydantic schemas for WC (system-level Setting) JSON envelopes.

WC is a virtual model — maps to Setting. This schema covers
the system-level configuration envelope.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import (
    ConfigBase, MetadataBase, RecordPrefsBase, RefsBase,
    CommentsBase, ActionsBase, SourceRef,
)


class WcConfig(ConfigBase):
    pass


class WcMetadata(MetadataBase):
    pass


class WcPrefs(RecordPrefsBase):
    pass


class WcRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


class WcComments(CommentsBase):
    pass


class WcActions(ActionsBase):
    pass
