"""
Pydantic schemas for Report JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


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

class ReportConfig(ConfigBase):
    """Extended config for Report records.

    The form/layout data lives here (config.form for PrintLayout,
    or config.rows + config.fields for detail forms).
    Library checkout stores the original in config.library_original.
    """
    pass


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
