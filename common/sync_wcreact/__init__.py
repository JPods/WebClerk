"""
common.sync_wcreact — r25 ↔ wc3 data synchronization package.

Centralizes canonical data definitions and sync logic for keeping
the React2025 frontend (r25) and WebClerk3 backend (wc3) aligned.

Modules:
    terms          Canonical payment term definitions + sync to Term model
    selectlists    Canonical select list definitions + sync to Setting records

Management commands (thin wrappers):
    python manage.py sync_terms         → common.sync_wcreact.terms
    python manage.py sync_selectlists   → common.sync_wcreact.selectlists
"""

from .terms import TERM_DEFS, SYNC_FIELDS as TERM_SYNC_FIELDS, sync_terms, list_terms
from .selectlists import (
    R25_DYNAMIC_LISTS,
    PURPOSE as SELECTLIST_PURPOSE,
    push_selectlists_to_wc3,
    show_selectlists_for_r25,
    list_selectlist_settings,
)

__all__ = [
    # Terms
    "TERM_DEFS",
    "TERM_SYNC_FIELDS",
    "sync_terms",
    "list_terms",
    # Select lists
    "R25_DYNAMIC_LISTS",
    "SELECTLIST_PURPOSE",
    "push_selectlists_to_wc3",
    "show_selectlists_for_r25",
    "list_selectlist_settings",
]
