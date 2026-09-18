"""
Pydantic schemas for AliceObservation, AlicePreset, and AliceCoachingLog JSON envelopes.

Mirrors alice.py — three models in one file.
AliceInsight has its own file (alice_insight_pydantic.py).
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


# ═══════════════════════════════════════════════════════════════════════
# AliceCoachingLog
# ═══════════════════════════════════════════════════════════════════════

class AliceCoachingLogConfig(ConfigBase):
    pass

class AliceCoachingLogMetadata(MetadataBase):
    pass

class AliceCoachingLogPrefs(RecordPrefsBase):
    pass

class AliceCoachingLogRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None
