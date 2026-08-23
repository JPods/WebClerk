"""
Base envelope schemas — shared structures reused across all models.

Architecture (established 2026-08-04):
  Every BaseModel record inherits from these bases.
  Model-specific schemas extend, never duplicate.

  MetadataBase — every record gets this (history, health, flags, etc.)
  RecordPrefsBase — every record gets this (userdefined, tags, pinned)
  RefsBase — every record gets this (links, source)

  Mixins — composed into model schemas only where needed:
  FinancialMetadataMixin — GL, reconciliation, ledger (transactions, payments)
  StaffPrefsMixin — nav, wcui, databrowser (contacts with is_staff)
  RepPrefsMixin — territory, commission (contacts with rep FK)
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════
# Shared types — building blocks
# ═══════════════════════════════════════════════════════════════════════

class AuditEntry(BaseModel):
    """One entry in the audit trail. Append-only."""
    action: str
    dt: int = 0                           # epoch ms
    details: dict = Field(default_factory=dict)
    user_id: Optional[int] = None


class HistoryTimestamp(BaseModel):
    """Timestamp + who did it."""
    dt: int = 0                           # epoch ms
    contact_id: int = 0


class RecordHistory(BaseModel):
    """Record lifecycle timestamps — every record gets this."""
    synced: HistoryTimestamp = Field(default_factory=HistoryTimestamp)
    created: HistoryTimestamp = Field(default_factory=HistoryTimestamp)
    accessed: HistoryTimestamp = Field(default_factory=HistoryTimestamp)
    modified: HistoryTimestamp = Field(default_factory=HistoryTimestamp)
    verified: HistoryTimestamp = Field(default_factory=HistoryTimestamp)


class HealthScores(BaseModel):
    """Data quality scores — machine-calculated."""
    rating: int = 0
    accuracy: int = 0
    freshness: int = 0
    consistency: int = 0
    completeness: int = 0


class RecordFlags(BaseModel):
    """System flags — schema version, processing state."""
    schema_rev: int = 1
    keywords_pending: bool = False


class AccessControl(BaseModel):
    """Record-level access control lists."""
    edit: list[int] = Field(default_factory=list)   # contact IDs
    view: list[int] = Field(default_factory=list)


class VersioningInfo(BaseModel):
    """Field change tracking."""
    size_activity: dict = Field(default_factory=dict)
    changed_fields: list[str] = Field(default_factory=list)


class ImportProvenance(BaseModel):
    """Where this record came from during import — with lifecycle management.

    Without dt_delete_on, import artifacts accumulate forever.
    status tracks the record through review: imported → reviewed → cleared → expired.
    """
    source: str = ''                      # mac_contacts, csv, sync, manual
    dt_imported: int = 0                  # epoch ms — when the record was imported
    dt_delete_on: int = 0                 # epoch ms — auto-cleanup deadline; 0 = no expiry
    status: str = ''                      # imported, reviewed, cleared, expired
    risk: str = ''                        # low, medium, high
    original: dict = Field(default_factory=dict)


class SourceRef(BaseModel):
    """Points back to the originating document."""
    type: str = ''                        # invoice, order, purchase, etc.
    id: int = 0


# ═══════════════════════════════════════════════════════════════════════
# MetadataBase — EVERY record inherits this
# ═══════════════════════════════════════════════════════════════════════

class MetadataBase(BaseModel):
    """Standard metadata fields inherited by every BaseModel record.

    Machine-managed. Never user-written.
    Model-specific schemas extend this, never duplicate these fields.
    """
    flow: dict = Field(default_factory=dict)
    temp: list = Field(default_factory=list)
    flags: RecordFlags = Field(default_factory=RecordFlags)
    access: AccessControl = Field(default_factory=AccessControl)
    health: HealthScores = Field(default_factory=HealthScores)
    source: dict = Field(default_factory=dict)
    history: RecordHistory = Field(default_factory=RecordHistory)
    publish: str = ""
    version: str = "1.0"
    erosions: list = Field(default_factory=list)
    priority: str = ""
    security: str = ""
    resources: dict = Field(default_factory=dict)
    versioning: VersioningInfo = Field(default_factory=VersioningInfo)
    small_stings: list = Field(default_factory=list)
    explanation: str = ""
    audit_trail: list[AuditEntry] = Field(default_factory=list)
    import_data: Optional[ImportProvenance] = None
    userdefined: dict = Field(default_factory=dict)
    images: dict = Field(default_factory=lambda: {
        "source": "", "tn": False, "display": False, "hires": False,
    })


# ═══════════════════════════════════════════════════════════════════════
# RecordPrefsBase — EVERY record inherits this
# ═══════════════════════════════════════════════════════════════════════

class SavedSearch(BaseModel):
    """A user's personal saved search definition.

    Stored in prefs.search[] on UserProfile (personal) or in a Report
    record (shared/delivered). Same shape in both places so promotion
    from personal → shared is a copy, not a transform.
    """
    name: str = ""
    model_name: str = ""
    keyword: Optional[str] = None
    search_fields: list[str] = Field(default_factory=list)
    filters: dict = Field(default_factory=dict)
    ordering: Optional[str] = None
    limit: Optional[int] = None
    relative_period: Optional[dict] = None
    dt_saved: int = 0

    class Config:
        extra = "allow"


class RecordPrefsBase(BaseModel):
    """Standard prefs fields inherited by every BaseModel record.

    User-written. Never system-managed.
    """
    userdefined: dict = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    pinned: bool = False
    search: list[SavedSearch] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════
# RefsBase — EVERY record inherits this
# ═══════════════════════════════════════════════════════════════════════

class RefsBase(BaseModel):
    """Standard refs fields. Links are denormalized cache — FKs are truth."""
    links: dict = Field(default_factory=dict)
    source: Optional[SourceRef] = None


# ═══════════════════════════════════════════════════════════════════════
# Financial mixin — transactions + payments only
# ═══════════════════════════════════════════════════════════════════════

class GlStage(BaseModel):
    """GL posting stage — DEPRECATED. Use model.dt_journaled instead.

    dt_journaled on the model (0=editable, non-zero=locked) replaces
    metadata.gl_accounts.posted. This schema remains for reading legacy data.
    """
    event: str = ''
    posted: bool = False
    dt_posted: int = 0
    postings: list[dict] = Field(default_factory=list)
    journal_count: int = 0


class ReconciliationData(BaseModel):
    """Reconciliation state for financial records."""
    batch_id: Optional[str] = None
    statement_date: Optional[str] = None
    notes: str = ''


class LedgerSync(BaseModel):
    """Ledger ↔ invoice sync state."""
    entries: list[dict] = Field(default_factory=list)
    total_original: float = 0.0
    dt_sync: int = 0


class FinancialMetadataMixin(BaseModel):
    """Mixed into transaction/payment metadata. Not on contacts or items."""
    gl_accounts: Optional[GlStage] = None
    ledger: Optional[LedgerSync] = None
    reconciliation: Optional[ReconciliationData] = None
    gateway_metadata: dict = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════
# Staff prefs mixin — contacts with is_staff only
# ═══════════════════════════════════════════════════════════════════════

class NavPrefs(BaseModel):
    """Sidebar navigation customization."""
    models: list[str] = Field(default_factory=lambda: [
        "contact", "customer", "proposal", "order", "invoice", "purchase"
    ])
    dashboards: list[str] = Field(default_factory=lambda: [
        "dashboard", "products", "transactions", "orgs", "administration",
        "kanban", "gantt", "alice", "databrowser"
    ])
    cards: list[str] = Field(default_factory=lambda: [
        "order", "invoice", "proposal", "customer", "contact", "purchase"
    ])


class WcuiPrefs(BaseModel):
    """UI preferences — font, theme, feature toggles."""
    theme: str = "dark"
    font_size: int = 12

    class Config:
        extra = "allow"


class DatabrowserPrefs(BaseModel):
    """Databrowser-specific preferences."""
    theme: str = "dark"
    font_size: str = "L"
    active_layout: str = ""


class ColorModePrefs(BaseModel):
    """Per-zone light/dark mode."""
    list: str = "dark"
    detail: str = "dark"


class LayoutPrefs(BaseModel):
    """Per-model detail view preferences."""
    detail_view: str = "app"           # "app" or "db" — which detail renderer
    active_view: dict[str, str] = Field(default_factory=dict)  # model → named view

    class Config:
        extra = "allow"


class StaffPrefsMixin(BaseModel):
    """Mixed into contact.prefs.staff for internal users only."""
    nav: NavPrefs = Field(default_factory=NavPrefs)
    wcui: WcuiPrefs = Field(default_factory=WcuiPrefs)
    databrowser: DatabrowserPrefs = Field(default_factory=DatabrowserPrefs)
    color_mode: ColorModePrefs = Field(default_factory=ColorModePrefs)
    layout: LayoutPrefs = Field(default_factory=LayoutPrefs)
    gantt: dict = Field(default_factory=dict)
    training: bool = False


# ═══════════════════════════════════════════════════════════════════════
# Rep prefs mixin — contacts with rep FK only
# ═══════════════════════════════════════════════════════════════════════

class RepPrefsMixin(BaseModel):
    """Mixed into contact.prefs.rep for sales reps."""
    territory: list[str] = Field(default_factory=list)
    commission_display: str = "percentage"
    default_price_level: str = ""
    account_sort: str = "name"
    notifications: dict = Field(default_factory=dict)

    class Config:
        extra = "allow"


# ═══════════════════════════════════════════════════════════════════════
# Employee prefs mixin — contacts with employee FK only
# ═══════════════════════════════════════════════════════════════════════

class EmployeePrefsMixin(BaseModel):
    """Mixed into contact.prefs.employee for employees."""
    department: str = ""
    schedule: dict = Field(default_factory=dict)
    notifications: dict = Field(default_factory=dict)
    dashboard: str = ""

    class Config:
        extra = "allow"


# ═══════════════════════════════════════════════════════════════════════
# Cart prefs mixin — customer-facing contacts only
# ═══════════════════════════════════════════════════════════════════════

class CartPrefsMixin(BaseModel):
    """Mixed into contact.prefs.cart for shopping cart users."""
    language: str = "en"
    currency: str = "USD"
    shipping_default: dict = Field(default_factory=dict)
    payment_method: str = ""
    notifications: dict = Field(default_factory=dict)
    saved_addresses: list[dict] = Field(default_factory=list)

    class Config:
        extra = "allow"


# ═══════════════════════════════════════════════════════════════════════
# CommentsBase — EVERY record inherits this
# ═══════════════════════════════════════════════════════════════════════

class CommentEntry(BaseModel):
    """One entry in a comment channel. Append-only."""
    ts: str = ''                              # ISO timestamp
    by: str = ''                              # contact_id or username
    text: str = ''                            # max 255 chars
    source: str = ''                          # optional origin


class CommentChannels(BaseModel):
    """Three comment channels — public, process, foreign."""
    public: list[CommentEntry] = Field(default_factory=list)
    process: list[CommentEntry] = Field(default_factory=list)
    foreign: list[CommentEntry] = Field(default_factory=list)


class CommentsBase(BaseModel):
    """Standard comments structure inherited by every BaseModel record.

    Two scopes:
      general — about the record itself (3 channels)
      records — about related records, keyed by 'model/id' (same 3 channels)
    """
    general: CommentChannels = Field(default_factory=CommentChannels)
    records: dict = Field(default_factory=dict)  # keyed by 'model/id'


# ═══════════════════════════════════════════════════════════════════════
# ActionsBase — EVERY record inherits this
# ═══════════════════════════════════════════════════════════════════════

class ActionsBase(BaseModel):
    """Standard actions fields inherited by every BaseModel record.

    Next-action metadata — frequently indexed for dashboard queries.
    Kept small (32KB max) for queryability.
    """
    required: bool = False
    status: str = ''                          # pending, done, blocked
    who: Optional[int] = None                 # contact_id
    when: int = 0                             # epoch ms — due/next date
    what: str = ''                            # action description
    kind: str = ''                            # followup, review, ship, approve
    extra: dict = Field(default_factory=dict) # free-form per domain


# ═══════════════════════════════════════════════════════════════════════
# ConfigBase — model-specific structural data
# ═══════════════════════════════════════════════════════════════════════

class ConfigBase(BaseModel):
    """Base config — models with no specific config fields inherit this.

    Default: extra = 'forbid'. Models that need flexibility override
    with their own Config class. This forces deliberate schema decisions.

    Images live in metadata.images (not config) — enforced by
    _init_metadata_if_needed on every save.
    """

    class Config:
        extra = 'forbid'


# ═══════════════════════════════════════════════════════════════════════
# Setting types
# ═══════════════════════════════════════════════════════════════════════

class SettingDefaults(BaseModel):
    """Installation-level defaults for new records. Lives in Setting.prefs.defaults."""
    class Config:
        extra = 'allow'


class DisplayPrefs(BaseModel):
    """DataBrowser display preferences. Lives in Setting.prefs.display."""
    detail_width: int = 420
    font_size: int = 12
    theme: str = ''
    density: str = 'comfortable'
