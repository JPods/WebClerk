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

from typing import Any, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator


# ═══════════════════════════════════════════════════════════════════════
# userdefined constraints — flat scalar bag, bounded
# ═══════════════════════════════════════════════════════════════════════

USERDEFINED_MAX_KEYS = 20          # max name:value pairs
USERDEFINED_KEY_MAX_LEN = 64       # max chars per key name
USERDEFINED_VALUE_MAX_LEN = 255    # max chars per string value

# Allowed scalar types — no dicts, no lists, no nesting
UserDefinedValue = Union[str, int, float, bool, None]


def validate_userdefined(v: Any) -> dict[str, UserDefinedValue]:
    """Validate userdefined dict: flat scalars only, bounded count and length."""
    if not isinstance(v, dict):
        return {}

    if len(v) > USERDEFINED_MAX_KEYS:
        raise ValueError(
            f"userdefined exceeds {USERDEFINED_MAX_KEYS} keys "
            f"(has {len(v)})"
        )

    clean: dict[str, UserDefinedValue] = {}
    for key, val in v.items():
        if not isinstance(key, str):
            raise ValueError(f"userdefined key must be str, got {type(key).__name__}")
        if len(key) > USERDEFINED_KEY_MAX_LEN:
            raise ValueError(
                f"userdefined key '{key[:20]}...' exceeds "
                f"{USERDEFINED_KEY_MAX_LEN} chars"
            )
        if isinstance(val, (dict, list)):
            raise ValueError(
                f"userdefined['{key}'] must be a flat scalar "
                f"(str/int/float/bool/None), got {type(val).__name__}"
            )
        if isinstance(val, str) and len(val) > USERDEFINED_VALUE_MAX_LEN:
            raise ValueError(
                f"userdefined['{key}'] string exceeds "
                f"{USERDEFINED_VALUE_MAX_LEN} chars"
            )
        clean[key] = val
    return clean


# ═══════════════════════════════════════════════════════════════════════
# Envelope-wide size and count limits
# ═══════════════════════════════════════════════════════════════════════

import re as _re

TAGS_MAX_COUNT = 50                 # max tags per record
TAG_MAX_LEN = 64                    # max chars per tag
COMMENT_TEXT_MAX_LEN = 1000         # max chars per comment entry
COMMENT_CHANNEL_MAX_COUNT = 500     # max entries per comment channel
SAVED_SEARCH_MAX_COUNT = 25         # max saved searches per record
SAVED_SEARCH_FIELDS_MAX = 20       # max fields in a saved search
SAVED_SEARCH_FILTERS_MAX_KEYS = 10  # max filter keys per saved search
SAVED_ADDRESSES_MAX_COUNT = 10      # max saved addresses per contact
AUDIT_TRAIL_MAX_ENTRIES = 500       # max audit entries before archival needed
AUDIT_DETAIL_MAX_SIZE = 2048        # max bytes per audit detail dict
EROSION_MAX_COUNT = 50              # max erosion entries
SMALL_STING_MAX_COUNT = 100         # max small-sting entries
TEMP_MAX_COUNT = 50                 # max temp entries
NOTIFICATIONS_MAX_KEYS = 20        # max notification preference keys
JSON_MAX_DEPTH = 8                  # max nesting depth for any JSON field
STRING_FIELD_MAX_LEN = 10000        # max chars for any string field in envelopes

# Base64 / binary detection — documents go through Document.path ONLY
_BASE64_PATTERN = _re.compile(
    r'^(?:[A-Za-z0-9+/]{4}){10,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$'
)
_DATA_URI_PATTERN = _re.compile(r'^data:[^;]+;base64,')

BINARY_MIN_LEN = 500  # strings shorter than this are never flagged as binary


def looks_like_binary(value: str) -> bool:
    """Return True if a string value looks like base64 or a data URI.

    Documents go through Document.path — binary content in any other
    field is rejected.
    """
    if len(value) < BINARY_MIN_LEN:
        return False
    if _DATA_URI_PATTERN.match(value):
        return True
    # Check first 200 chars for base64 pattern (avoid scanning huge strings)
    sample = value[:200].strip()
    if _BASE64_PATTERN.match(sample):
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════
# Shared types — building blocks
# ═══════════════════════════════════════════════════════════════════════

class AuditEntry(BaseModel):
    """One entry in the audit trail. Append-only."""
    action: str
    dt: int = 0                           # epoch ms
    details: dict = Field(default_factory=dict)
    user_id: Optional[int] = None

    @field_validator('details', mode='before')
    @classmethod
    def _cap_details_size(cls, v: Any) -> dict:
        if isinstance(v, dict):
            import json as _json
            size = len(_json.dumps(v).encode('utf-8'))
            if size > AUDIT_DETAIL_MAX_SIZE:
                raise ValueError(
                    f"audit detail exceeds {AUDIT_DETAIL_MAX_SIZE} bytes"
                )
        return v if isinstance(v, dict) else {}

    @field_validator('action', mode='before')
    @classmethod
    def _cap_action(cls, v: Any) -> str:
        if isinstance(v, str) and len(v) > 255:
            raise ValueError("audit action exceeds 255 chars")
        return v or ''


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
    userdefined: dict[str, UserDefinedValue] = Field(default_factory=dict)
    images: dict = Field(default_factory=lambda: {
        "source": "", "tn": False, "display": False, "hires": False,
    })

    @field_validator('userdefined', mode='before')
    @classmethod
    def _validate_userdefined(cls, v: Any) -> dict:
        return validate_userdefined(v)

    @field_validator('audit_trail', mode='before')
    @classmethod
    def _cap_audit_trail(cls, v: Any) -> list:
        if isinstance(v, list) and len(v) > AUDIT_TRAIL_MAX_ENTRIES:
            raise ValueError(
                f"audit_trail exceeds {AUDIT_TRAIL_MAX_ENTRIES} entries"
            )
        return v if isinstance(v, list) else []

    @field_validator('erosions', mode='before')
    @classmethod
    def _cap_erosions(cls, v: Any) -> list:
        if isinstance(v, list) and len(v) > EROSION_MAX_COUNT:
            raise ValueError(
                f"erosions exceed {EROSION_MAX_COUNT} entries"
            )
        return v if isinstance(v, list) else []

    @field_validator('small_stings', mode='before')
    @classmethod
    def _cap_small_stings(cls, v: Any) -> list:
        if isinstance(v, list) and len(v) > SMALL_STING_MAX_COUNT:
            raise ValueError(
                f"small_stings exceed {SMALL_STING_MAX_COUNT} entries"
            )
        return v if isinstance(v, list) else []

    @field_validator('temp', mode='before')
    @classmethod
    def _cap_temp(cls, v: Any) -> list:
        if isinstance(v, list) and len(v) > TEMP_MAX_COUNT:
            raise ValueError(
                f"temp exceeds {TEMP_MAX_COUNT} entries"
            )
        return v if isinstance(v, list) else []

    @field_validator('explanation', 'publish', 'priority', 'security', mode='before')
    @classmethod
    def _cap_metadata_strings(cls, v: Any) -> str:
        if isinstance(v, str) and len(v) > STRING_FIELD_MAX_LEN:
            raise ValueError(
                f"metadata string field exceeds {STRING_FIELD_MAX_LEN} chars"
            )
        if isinstance(v, str) and looks_like_binary(v):
            raise ValueError(
                "binary/base64 content not allowed — use Document.path"
            )
        return v if isinstance(v, str) else ''


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
        extra = "forbid"

    @field_validator('search_fields', mode='before')
    @classmethod
    def _cap_search_fields(cls, v: Any) -> list:
        if isinstance(v, list) and len(v) > SAVED_SEARCH_FIELDS_MAX:
            raise ValueError(
                f"search_fields exceeds {SAVED_SEARCH_FIELDS_MAX} items"
            )
        return v if isinstance(v, list) else []

    @field_validator('filters', mode='before')
    @classmethod
    def _cap_filters(cls, v: Any) -> dict:
        if isinstance(v, dict) and len(v) > SAVED_SEARCH_FILTERS_MAX_KEYS:
            raise ValueError(
                f"search filters exceed {SAVED_SEARCH_FILTERS_MAX_KEYS} keys"
            )
        return v if isinstance(v, dict) else {}

    @field_validator('name', 'model_name', mode='before')
    @classmethod
    def _cap_names(cls, v: Any) -> str:
        if isinstance(v, str) and len(v) > 255:
            raise ValueError("search name/model_name exceeds 255 chars")
        return v or ''


class RecordPrefsBase(BaseModel):
    """Standard prefs fields inherited by every BaseModel record.

    User-written. Never system-managed.
    """
    userdefined: dict[str, UserDefinedValue] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    pinned: bool = False
    search: list[SavedSearch] = Field(default_factory=list)

    @field_validator('userdefined', mode='before')
    @classmethod
    def _validate_userdefined(cls, v: Any) -> dict:
        return validate_userdefined(v)

    @field_validator('tags', mode='before')
    @classmethod
    def _validate_tags(cls, v: Any) -> list:
        if not isinstance(v, list):
            return []
        if len(v) > TAGS_MAX_COUNT:
            raise ValueError(f"tags exceed {TAGS_MAX_COUNT} entries")
        for i, tag in enumerate(v):
            if not isinstance(tag, str):
                raise ValueError(f"tag[{i}] must be a string")
            if len(tag) > TAG_MAX_LEN:
                raise ValueError(
                    f"tag '{tag[:20]}...' exceeds {TAG_MAX_LEN} chars"
                )
        return v

    @field_validator('search', mode='before')
    @classmethod
    def _validate_search_count(cls, v: Any) -> list:
        if isinstance(v, list) and len(v) > SAVED_SEARCH_MAX_COUNT:
            raise ValueError(
                f"saved searches exceed {SAVED_SEARCH_MAX_COUNT}"
            )
        return v if isinstance(v, list) else []


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
        extra = "forbid"


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
        extra = "forbid"


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
        extra = "forbid"

    @field_validator('notifications', mode='before')
    @classmethod
    def _cap_notifications(cls, v: Any) -> dict:
        if isinstance(v, dict) and len(v) > NOTIFICATIONS_MAX_KEYS:
            raise ValueError(
                f"notifications exceeds {NOTIFICATIONS_MAX_KEYS} keys"
            )
        return v if isinstance(v, dict) else {}


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
        extra = "forbid"

    @field_validator('notifications', mode='before')
    @classmethod
    def _cap_notifications(cls, v: Any) -> dict:
        if isinstance(v, dict) and len(v) > NOTIFICATIONS_MAX_KEYS:
            raise ValueError(
                f"notifications exceeds {NOTIFICATIONS_MAX_KEYS} keys"
            )
        return v if isinstance(v, dict) else {}


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
        extra = "forbid"

    @field_validator('saved_addresses', mode='before')
    @classmethod
    def _cap_addresses(cls, v: Any) -> list:
        if isinstance(v, list) and len(v) > SAVED_ADDRESSES_MAX_COUNT:
            raise ValueError(
                f"saved_addresses exceeds {SAVED_ADDRESSES_MAX_COUNT}"
            )
        return v if isinstance(v, list) else []

    @field_validator('notifications', mode='before')
    @classmethod
    def _cap_notifications(cls, v: Any) -> dict:
        if isinstance(v, dict) and len(v) > NOTIFICATIONS_MAX_KEYS:
            raise ValueError(
                f"notifications exceeds {NOTIFICATIONS_MAX_KEYS} keys"
            )
        return v if isinstance(v, dict) else {}


# ═══════════════════════════════════════════════════════════════════════
# CommentsBase — EVERY record inherits this
# ═══════════════════════════════════════════════════════════════════════

class CommentEntry(BaseModel):
    """One entry in a comment channel. Append-only."""
    ts: str = ''                              # ISO timestamp
    by: str = ''                              # contact_id or username
    text: str = ''                            # max 1000 chars — enforced
    source: str = ''                          # optional origin

    @field_validator('text', mode='before')
    @classmethod
    def _cap_text(cls, v: Any) -> str:
        if isinstance(v, str) and len(v) > COMMENT_TEXT_MAX_LEN:
            raise ValueError(
                f"comment text exceeds {COMMENT_TEXT_MAX_LEN} chars"
            )
        return v or ''

    @field_validator('by', 'source', 'ts', mode='before')
    @classmethod
    def _cap_short_strings(cls, v: Any) -> str:
        if isinstance(v, str) and len(v) > 255:
            raise ValueError("comment field exceeds 255 chars")
        return v or ''


class CommentChannels(BaseModel):
    """Three comment channels — public, process, foreign."""
    public: list[CommentEntry] = Field(default_factory=list)
    process: list[CommentEntry] = Field(default_factory=list)
    foreign: list[CommentEntry] = Field(default_factory=list)

    @field_validator('public', 'process', 'foreign', mode='before')
    @classmethod
    def _cap_channel_count(cls, v: Any) -> list:
        if isinstance(v, list) and len(v) > COMMENT_CHANNEL_MAX_COUNT:
            raise ValueError(
                f"comment channel exceeds {COMMENT_CHANNEL_MAX_COUNT} entries"
            )
        return v if isinstance(v, list) else []


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
