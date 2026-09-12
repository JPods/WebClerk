"""
Pydantic schemas for DeliveryVisit and DeliveryLine JSON envelopes.

Mirrors flow.py — both models in one file.
"""
from __future__ import annotations

from typing import Optional
from pydantic import Field

from common.schemas.envelopes import (
    ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef,
)


# ═══════════════════════════════════════════════════════════════════════
# DeliveryVisit
# ═══════════════════════════════════════════════════════════════════════

class DeliveryVisitConfig(ConfigBase):
    pass

class DeliveryVisitMetadata(MetadataBase):
    pass

class DeliveryVisitPrefs(RecordPrefsBase):
    pass

class DeliveryVisitRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


# ═══════════════════════════════════════════════════════════════════════
# DeliveryLine
# ═══════════════════════════════════════════════════════════════════════

class DeliveryLineConfig(ConfigBase):
    pass

class DeliveryLineMetadata(MetadataBase):
    pass

class DeliveryLinePrefs(RecordPrefsBase):
    pass

class DeliveryLineRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None
