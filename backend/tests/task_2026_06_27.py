"""Task runner for 2026-06-27 session tests.

Run all tests created during the wc2→wc3 translation session:
    ./bin/python -m pytest tests/task_2026_06_27.py -v --no-cov

Or run individual groups:
    ./bin/python -m pytest tests/task_2026_06_27.py -k "gl" -v --no-cov
    ./bin/python -m pytest tests/task_2026_06_27.py -k "pricing" -v --no-cov
    ./bin/python -m pytest tests/task_2026_06_27.py -k "inventory" -v --no-cov

Session summary:
    51 tests across 6 files covering GL posting, commerce cycle,
    pricing, inventory availability, cross-reference lookup,
    inventory bucket flow, and GL manage action.

To re-run the original files individually:
    ./bin/python -m pytest tests/test_gl_posting.py -v --no-cov
    ./bin/python -m pytest tests/test_commerce_cycle_e2e.py -v --no-cov
    ./bin/python -m pytest tests/test_pricing.py -v --no-cov
    ./bin/python -m pytest tests/test_inventory_and_xref.py -v --no-cov
    ./bin/python -m pytest tests/test_inventory_bucket_flow.py -v --no-cov
    ./bin/python -m pytest tests/test_gl_manage_action.py -v --no-cov

All at once:
    ./bin/python -m pytest tests/test_gl_posting.py tests/test_commerce_cycle_e2e.py tests/test_pricing.py tests/test_inventory_and_xref.py tests/test_inventory_bucket_flow.py tests/test_gl_manage_action.py -v --no-cov
"""
import pytest

# ─────────────────────────────────────────────────────────────────────
# GL Posting — post_staged_gl_entries() converts metadata → GlJournal
# ─────────────────────────────────────────────────────────────────────
from tests.test_gl_posting import TestPostStagedGlEntries  # noqa: F401

# ─────────────────────────────────────────────────────────────────────
# GL Manage Action — POST /wcapi/_manage/ {action: "post_gl_entries"}
# User-initiated journalizing: posts GL entries + locks record
# ─────────────────────────────────────────────────────────────────────
from tests.test_gl_manage_action import TestPostGLManageAction  # noqa: F401

# ─────────────────────────────────────────────────────────────────────
# Commerce Cycle E2E — GL posting, contact/org linking, pending verify
# ─────────────────────────────────────────────────────────────────────
from tests.test_commerce_cycle_e2e import (  # noqa: F401
    TestGLPosting,
    TestContactOrgLinking,
    TestInventoryPending,
)

# ─────────────────────────────────────────────────────────────────────
# Pricing — price level chain (line > header > customer > base),
#           quantity breaks, fallback behavior
# ─────────────────────────────────────────────────────────────────────
from tests.test_pricing import (  # noqa: F401
    TestResolvePriceLevel,
    TestResolveUnitPrice,
    TestGetPriceForLine,
)

# ─────────────────────────────────────────────────────────────────────
# Inventory Availability — on_hand - reserved = available, per-warehouse
# ─────────────────────────────────────────────────────────────────────
from tests.test_inventory_and_xref import (  # noqa: F401
    TestInventoryAvailability,
    TestXRefLookup,
)

# ─────────────────────────────────────────────────────────────────────
# Inventory Bucket Flow — full lifecycle:
#   Proposal(5) → Order(4) → Invoice(3) → PO(10) → Receive(8)
#   Verifies Pending bucket rules and availability transitions
# ─────────────────────────────────────────────────────────────────────
from tests.test_inventory_bucket_flow import TestInventoryBucketFlow  # noqa: F401

# ─────────────────────────────────────────────────────────────────────
# GL Reversal — contra entries for journalized records
# Post → Reverse → Edit → Re-post correction workflow
# ─────────────────────────────────────────────────────────────────────
from tests.test_gl_manage_action import TestReverseGLManageAction  # noqa: F401

# ─────────────────────────────────────────────────────────────────────
# Data Integrity — export/import roundtrip, refs↔FK consistency,
# soft delete exclusion, version conflict detection
# ─────────────────────────────────────────────────────────────────────
from tests.test_data_integrity import (  # noqa: F401
    TestExportImportRoundtrip,
    TestRefsFKConsistency,
    TestSoftDeleteConsistency,
    TestVersionConflict,
)

# ─────────────────────────────────────────────────────────────────────
# Alice Training Flow — guided commerce cycle for user training
# and system health checks. All records flagged metadata.training=True.
# ─────────────────────────────────────────────────────────────────────
from tests.test_training_flow import TestTrainingFlow  # noqa: F401

# ─────────────────────────────────────────────────────────────────────
# Orphan Detection — admin dashboard data health: null + dangling FK counts
# ─────────────────────────────────────────────────────────────────────
from tests.test_orphan_detection import TestOrphanDetection  # noqa: F401

# ─────────────────────────────────────────────────────────────────────
# Accounting Dashboard — GL balance, journal status, aging, orphans,
# transaction volume, locked records, pending inventory
# ─────────────────────────────────────────────────────────────────────
from tests.test_accounting_dashboard import TestAccountingDashboard  # noqa: F401
