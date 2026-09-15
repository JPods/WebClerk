"""
Pydantic schemas for InventoryCheck and InventoryCheckLine JSON envelopes.

Mirrors inventory_check.py — both models in one file.
"""
from __future__ import annotations

from typing import Optional
from pydantic import Field

from common.schemas.envelopes import (
    ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef,
)


# ═══════════════════════════════════════════════════════════════════════
# InventoryCheck
# ═══════════════════════════════════════════════════════════════════════

class InventoryCheckConfig(ConfigBase):
    pass

class InventoryCheckMetadata(MetadataBase):
    pass

class InventoryCheckPrefs(RecordPrefsBase):
    pass

class InventoryCheckRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


# ═══════════════════════════════════════════════════════════════════════
# InventoryCheckLine
# ═══════════════════════════════════════════════════════════════════════

class InventoryCheckLineConfig(ConfigBase):
    pass

class InventoryCheckLineMetadata(MetadataBase):
    pass

class InventoryCheckLinePrefs(RecordPrefsBase):
    pass

class InventoryCheckLineRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None
