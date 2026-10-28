"""
Pydantic schemas for AliceObservation and AlicePreset JSON envelopes.

Mirrors alice.py — three models in one file.
(AliceInsight became core.Lesson, 2026-10-28.)
"""
from __future__ import annotations

from typing import Optional
from pydantic import Field

from common.schemas.envelopes import (
    ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef,
)


# ═══════════════════════════════════════════════════════════════════════
# AliceObservation
# ═══════════════════════════════════════════════════════════════════════

class AliceObservationConfig(ConfigBase):
    pass

class AliceObservationMetadata(MetadataBase):
    pass

class AliceObservationPrefs(RecordPrefsBase):
    pass

class AliceObservationRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


# ═══════════════════════════════════════════════════════════════════════
# AlicePreset
# ═══════════════════════════════════════════════════════════════════════

class AlicePresetConfig(ConfigBase):
    pass

class AlicePresetMetadata(MetadataBase):
    pass

class AlicePresetPrefs(RecordPrefsBase):
    pass

class AlicePresetRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None
