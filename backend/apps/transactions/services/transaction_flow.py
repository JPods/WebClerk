from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone as _tz
from decimal import Decimal
from typing import Optional, Sequence


def _now_ms() -> int:
    """UTC epoch ms — every stored datetime in WC3 (Axiom 14)."""
    return int(datetime.now(_tz.utc).timestamp() * 1000)

from django.db import transaction
from django.core.exceptions import ValidationError

from apps.transactions.models import (
    Quote, QuoteLine,
    Order, OrderLine,
    Invoice, InvoiceLine,
    Purchase, PurchaseLine,
    WorkOrder, WorkOrderLine
)
# NOTE: Linkage functionality removed - use LinkageEntry if needed
# from apps.docs.models.linkage_entry import LinkageEntry
from apps.products.models.item import Item
from apps.products.models.warehouse import Warehouse
from apps.products.models.inventory_layer import InventoryLayer

# ---------------------------------------------------------------------------
# Central review list of JSON-esque line attributes we expect to deep-copy
# when creating a new transactional line from another (quote -> order,
# order -> invoice, PO -> receipt derived lines, etc.).
#
# IMPORTANT (review process):
# 1. If you add a new JSONField to BaseLineModel (or concrete line models),
#    append its name here AND add a sample value in the line copy parity test.
# 2. The test `tests/test_line_copy_field_parity.py` will fail if a JSONField
#    exists on a representative line model (OrderLine) that's not listed.
# 3. Fields that are scalar (status, type_sale, probability) are handled
#    explicitly below and are not part of this list.
# 4. Missing attributes are skipped safely so forward additions won't break
#    runtime before migrations / code sync complete.
#
# Header-only JSON (if ever) should NOT be added here (those belong to parent
# transaction models, not lines). Keep this strictly for line-level fields.
# ---------------------------------------------------------------------------
LINE_JSON_FIELDS_TO_COPY = (
    'item', 'quantity', 'cost', 'price', 'tax',
    'actions', 'physical',
    # Results: copied as they are, then recomputed by the totals engine on the new document.
    'totals',
    # Extended / newer additions (may be no-ops until fields are present):
    'metadata', 'refs', 'prefs', 'comments',
    # Carried forward by the convert services (convert.py, convert_quote_to_order.py,
    # convert_order_to_invoice.py) into lines returned for review.
    'commission', 'config',
)


# ---------------------------------------------------------------------------
# Linkage helpers (DISABLED - use LinkageEntry if needed)
# ---------------------------------------------------------------------------
def _resolve_item_id_from_line(line: PurchaseLine | OrderLine | QuoteLine | WorkOrderLine) -> Optional[int]:
    item = getattr(line, 'item', {}) or {}
    # Prefer id_num, fallback: try 'id' or 'item_id' if present
    return item.get('id_num') or item.get('id') or item.get('item_id')


# Receiving is a convert on the purchase (convert.py, purchase→receipt); building is a
# production workorder (workorder_bom).
__all__: list[str] = []
