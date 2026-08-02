"""
Base envelope schemas — shared structures reused across all models.

These are the building blocks. Model-specific schemas compose from these.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ── .metadata shared types ──────────────────────────────────────────

class AuditEntry(BaseModel):
    """One entry in the audit trail. Append-only."""
    action: str
    dt: int = 0                           # epoch ms
    details: dict = Field(default_factory=dict)
    user_id: Optional[int] = None


class GlStage(BaseModel):
    """GL posting stage — written by journalizer or ledger_balance."""
    event: str = ''                       # invoice_created, payment_journalized, etc.
    posted: bool = False
    dt_posted: int = 0                    # epoch ms
    postings: list[dict] = Field(default_factory=list)
    journal_count: int = 0


class ImportProvenance(BaseModel):
    """Where this record came from during import."""
    source: str = ''                      # mac_contacts, csv, sync, manual
    dt_imported: int = 0
    risk: str = ''                        # low, medium, high
    original: dict = Field(default_factory=dict)


class ReconciliationData(BaseModel):
    """Reconciliation state for financial records."""
    batch_id: Optional[str] = None
    statement_date: Optional[str] = None
    notes: str = ''


class LedgerSync(BaseModel):
    """Ledger ↔ invoice sync state."""
    entries: list[dict] = Field(default_factory=list)
    total_original: float = 0.0
    dt_sync: int = 0                      # 0 = not yet confirmed


# ── .prefs shared types ─────────────────────────────────────────────

class UserDefined(BaseModel):
    """Freeform user-defined fields. Keys are field names, values are anything."""
    class Config:
        extra = 'allow'


class RecordPrefsBase(BaseModel):
    """Base for any record's .prefs."""
    userdefined: dict = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    pinned: bool = False


# ── .refs shared types ──────────────────────────────────────────────

class SourceRef(BaseModel):
    """Points back to the originating document."""
    type: str = ''                        # invoice, order, purchase, etc.
    id: int = 0


class RefsBase(BaseModel):
    """Base for any record's .refs. Links are denormalized cache — FKs are truth."""
    links: dict = Field(default_factory=dict)
    source: Optional[SourceRef] = None


# ── Setting .prefs types ────────────────────────────────────────────

class SettingDefaults(BaseModel):
    """Installation-level defaults for new records. Lives in Setting.prefs.defaults."""
    class Config:
        extra = 'allow'                   # model-specific keys (type, method, category, etc.)


class DisplayPrefs(BaseModel):
    """DataBrowser display preferences. Lives in Setting.prefs.display."""
    detail_width: int = 420
    font_size: int = 12
    theme: str = ''
    density: str = 'comfortable'          # comfortable, compact, spacious
