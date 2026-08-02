"""
Pydantic schemas for {Model} JSON envelopes.

Copy this template for each model. Define exactly what goes in each envelope.
Delete sections that don't apply (not every model needs reconciliation or GL).

Schema review cycle:
  1. Developer adds fields → runs validation → commits schema
  2. Local Alice flags new/changed schemas → reports to WC_HQ
  3. WC_HQ reviews across all installations → approves or corrects
  4. Corrected schemas sync back to all installations
  5. Before the pattern spreads, the data is clean
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import (
    AuditEntry, GlStage, ImportProvenance, ReconciliationData,
    RecordPrefsBase, RefsBase, SourceRef,
)


# ── {Model} .metadata ───────────────────────────────────────────────

class ModelMetadata(BaseModel):
    """System-written. What goes here: GL state, sync state, audit trail, import provenance."""
    gl_accounts: Optional[GlStage] = None
    audit_trail: list[AuditEntry] = Field(default_factory=list)
    import_data: Optional[ImportProvenance] = None


# ── {Model} .prefs ──────────────────────────────────────────────────

class ModelPrefs(RecordPrefsBase):
    """User-initiated. What goes here: userdefined fields, tags, pinned."""
    pass


# ── {Model} .refs ───────────────────────────────────────────────────

class ModelRefsLinks(BaseModel):
    """Denormalized cache. List the FKs this model commonly queries by."""
    customer_id: Optional[int] = None
    contact_id: Optional[int] = None


class ModelRefs(RefsBase):
    """Relationship pointers. FKs are truth, these are cache."""
    links: ModelRefsLinks = Field(default_factory=ModelRefsLinks)  # type: ignore[assignment]
    source: Optional[SourceRef] = None


# ── Setting({model}, field_access).prefs ────────────────────────────

class ModelSettingDefaults(BaseModel):
    """Installation defaults for new records. Admin sets, Alice recommends."""
    status: str = 'draft'


class ModelSettingPrefs(BaseModel):
    """Full prefs for the field_access Setting."""
    defaults: ModelSettingDefaults = Field(default_factory=ModelSettingDefaults)
