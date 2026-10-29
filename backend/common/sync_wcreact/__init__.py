"""
common.sync_wcreact — r25 ↔ wc3 data synchronization package.

Centralizes canonical data definitions and sync logic for keeping
the React2025 frontend (r25) and WebClerk3 backend (wc3) aligned.

Modules:
    terms          Canonical cash term definitions + sync to Term model
    reports        Canonical report definitions + sync to Report model

Management commands (thin wrappers):
    python manage.py sync_terms         → common.sync_wcreact.terms
    python manage.py sync_reports       → common.sync_wcreact.reports
"""

from .terms import TERM_DEFS, SYNC_FIELDS as TERM_SYNC_FIELDS, sync_terms, list_terms
from .reports import (
    REPORT_DEFS,
    SYNC_FIELDS as REPORT_SYNC_FIELDS,
    sync_reports,
    list_reports,
    show_reports_for_r25,
)

__all__ = [
    # Terms
    "TERM_DEFS",
    "TERM_SYNC_FIELDS",
    "sync_terms",
    "list_terms",
    # Select lists
    # Reports
    "REPORT_DEFS",
    "REPORT_SYNC_FIELDS",
    "sync_reports",
    "list_reports",
    "show_reports_for_r25",
]
