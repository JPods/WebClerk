"""
Pydantic schemas for {Model} JSON envelopes.

Copy this template. Inherit from bases — never duplicate standard fields.

Six envelopes — every record inherits all six:
  ConfigBase — model-specific structural data (extra='forbid' by default)
  MetadataBase — system-managed: history, health, flags, audit trail
  RecordPrefsBase — user-managed: userdefined, tags, pinned
  RefsBase — relationship cache: links, source (FKs are truth)
  CommentsBase — structured comments: public, process, partner, notes[]
  ActionsBase — next-action metadata: required, status, who, when, what, kind

Mixins (compose only where needed):
  FinancialMetadataMixin — GL, reconciliation, ledger (transactions, payments)
  StaffPrefsMixin — nav, wcui, databrowser (contacts with is_staff)
  RepPrefsMixin — territory, commission (contacts with rep FK)
  EmployeePrefsMixin — department, schedule (contacts with employee FK)
  CartPrefsMixin — shopping cart prefs (customer-facing contacts)
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import (
    ConfigBase, MetadataBase, RecordPrefsBase, RefsBase,
    CommentsBase, ActionsBase, SourceRef,
)


# ── .config (inherits ConfigBase — extra='forbid' by default) ─────
# If this model stores specific fields in config, define them here.
# If not, inherit ConfigBase unchanged — unknown fields will be rejected.

class ModelConfig(ConfigBase):
    """Add model-specific config fields here. extra='forbid' inherited."""
    pass


# ── .metadata (inherits MetadataBase) ─────────────────────────────

class ModelMetadata(MetadataBase):
    """Add model-specific metadata fields here. Standard fields inherited."""
    pass


# ── .prefs (inherits RecordPrefsBase) ─────────────────────────────

class ModelPrefs(RecordPrefsBase):
    """Add model-specific prefs here. userdefined/tags/pinned inherited."""
    pass


# ── .refs (inherits RefsBase) ─────────────────────────────────────

class ModelRefs(RefsBase):
    """Add model-specific refs here. links/source inherited."""
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


# ── .comments (inherits CommentsBase) ─────────────────────────────

class ModelComments(CommentsBase):
    """Add model-specific comment fields here. public/process/partner/notes inherited."""
    pass


# ── .actions (inherits ActionsBase) ───────────────────────────────

class ModelActions(ActionsBase):
    """Add model-specific action fields here. required/status/who/when/what/kind inherited."""
    pass


# ── Setting defaults ──────────────────────────────────────────────

class ModelSettingDefaults(BaseModel):
    status: str = "draft"
