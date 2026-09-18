"""
Pydantic schemas for Report JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# -- Purpose categories — what this report record IS --------------------------
# Stored in Report.purpose (inherited from BaseModel).
# Category (form, report, statement, list, ...) is the menu grouping.
# Purpose is the functional classification.

REPORT_PURPOSE_CHOICES = [
    {"value": "form-detail",  "label": "Form (Detail)",   "description": "Screen form for editing one record"},
    {"value": "form-list",    "label": "Form (List)",      "description": "Screen layout for list/grid views"},
    {"value": "print",        "label": "Print",            "description": "PDF/paper output — invoices, statements, pick tickets"},
    {"value": "export",       "label": "Export",           "description": "CSV/JSON/Excel data download"},
    {"value": "label",        "label": "Label",            "description": "Physical labels — mailing, barcode, shipping"},
    {"value": "letter",       "label": "Letter",           "description": "Mail merge or templated email"},
    {"value": "query",        "label": "Saved Query",      "description": "Saved search/filter definition"},
    {"value": "sort",         "label": "Saved Sort",       "description": "Saved sort order"},
    {"value": "dashboard",    "label": "Dashboard",        "description": "Dashboard widget or panel definition"},
    {"value": "script",       "label": "Script",           "description": "Automation action or batch process"},
    {"value": "onboarding",   "label": "Onboarding",       "description": "Training, parade, or guided sequence"},
]


# -- .config ----------------------------------------------------------------

class FormRow(BaseModel):
    """One row of a detail form layout (DynamicDetail)."""
    cols: int = 1
    fields: list[str] = Field(default_factory=list)

    class Config:
        extra = 'forbid'


class ToolParam(BaseModel):
    """One admin-tool parameter (AdminTools.tsx ToolParam)."""
    name: str
    type: str = 'text'                      # text | boolean
    label: str = ''
    required: bool = False
    default: Optional[object] = None

    class Config:
        extra = 'forbid'


class ParadeFeedback(BaseModel):
    """report_parade.save_parade_feedback."""
    decision: Optional[str] = None          # Keep | Modify | Don't Need
    notes: str = ''
    user_id: Optional[int] = None
    dt_feedback: Optional[str] = None       # ISO UTC

    class Config:
        extra = 'forbid'


class LibraryOriginal(BaseModel):
    """form_library checkout snapshot, kept for restore."""
    form: dict = Field(default_factory=dict)
    source_uuid: Optional[str] = None
    checked_out_at: Optional[int] = None    # epoch ms

    class Config:
        extra = 'forbid'


class ReportConfig(ConfigBase):
    """Extended config for Report records.

    The form/layout data lives here (config.form for PrintLayout,
    or config.rows + config.fields for detail forms).
    Library checkout stores the original in config.library_original.
    """
    # -- print / render --
    template: Optional[str] = None          # built-in template key (render_report._resolve_template_key)
    form: Optional[dict] = None             # PrintLayout (UniversalPrint)
    pdfme_template: Optional[dict] = None   # pdfme {basePdf, schemas}
    statement: Optional[dict] = None        # conditional_text rules, e.g. statement.comments
    sample_data: Optional[dict] = None      # parade preview data

    # -- detail form layout (DynamicDetail) --
    rows: list[FormRow] = Field(default_factory=list)
    fields: dict[str, dict] = Field(default_factory=dict)

    # -- letters / touch templates --
    subject: Optional[str] = None
    body: Optional[str] = None
    channel: Optional[str] = None           # email | text | letter
    topic: Optional[str] = None

    # -- toolbar actions (DetailToolbar) --
    action: Optional[str] = None            # manage action name, open_url, import_vcard_dialog
    url: Optional[str] = None
    confirm: Optional[str] = None
    params: dict = Field(default_factory=dict)
    params_from_record: dict[str, str] = Field(default_factory=dict)
    download: Optional[bool] = None
    download_ext: Optional[str] = None
    download_mime: Optional[str] = None
    download_field: Optional[str] = None

    # -- admin tools (AdminTools) --
    command: Optional[str] = None
    parameters: list[ToolParam] = Field(default_factory=list)
    default_args: list[str] = Field(default_factory=list)

    # -- shared saved search (save_search_view writes; wcapi reads) --
    keyword: Optional[str] = None
    search_fields: list[str] = Field(default_factory=list)
    filters: dict = Field(default_factory=dict)
    ordering: Optional[str] = None
    limit: Optional[int] = None
    pagination: Optional[dict] = None
    relative_period: Optional[dict] = None  # {field, preset}
    request_filters: Optional[dict] = None
    request_keyword: Optional[str] = None

    # -- hooks (Report.save gate + report_hooks.validate_hooks own the shape) --
    hooks: Optional[dict] = None

    # -- parade + library --
    parade_feedback: Optional[ParadeFeedback] = None
    library_original: Optional[LibraryOriginal] = None


# -- .metadata (inherits MetadataBase) --------------------------------------

class ReportMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class ReportPrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class ReportRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None
