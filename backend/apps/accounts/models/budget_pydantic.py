"""
Pydantic schemas for Budget JSON envelopes.

Budget — one row per GL account per period. BaseModel with financial
metadata (account_debit/credit, dt_journaled).
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import (
    ConfigBase, MetadataBase, RecordPrefsBase, RefsBase,
    CommentsBase, ActionsBase, SourceRef, FinancialMetadataMixin,
)


# ── .config ──────────────────────────────────────────────────────────

class BudgetConfig(ConfigBase):
    """Budget-specific config. extra='forbid' inherited."""
    pass


# ── .metadata ────────────────────────────────────────────────────────

class BudgetMetadata(FinancialMetadataMixin, MetadataBase):
    """Budget metadata with financial mixin for GL posting."""
    pass


# ── .prefs ───────────────────────────────────────────────────────────

class BudgetPrefs(RecordPrefsBase):
    """Standard prefs inherited."""
    pass


# ── .refs ────────────────────────────────────────────────────────────

class BudgetRefs(RefsBase):
    """Relationship cache. FKs (purchase, bundle) are truth."""
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


# ── .comments ────────────────────────────────────────────────────────

class BudgetComments(CommentsBase):
    """Standard comments inherited."""
    pass


# ── .actions ─────────────────────────────────────────────────────────

class BudgetActions(ActionsBase):
    """Standard actions inherited."""
    pass


# ── Setting defaults ─────────────────────────────────────────────────

class BudgetSettingDefaults(BaseModel):
    status: str = "draft"
