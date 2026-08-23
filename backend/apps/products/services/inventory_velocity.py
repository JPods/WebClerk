"""Inventory velocity — capital flow analysis for Products dashboard (Tab 3).

Shows where capital is working vs parked across five stages:
  1. Purchase (POs)  — capital committed but not yet received
  2. Receipt         — vendor reliability: avg days PO → receipt
  3. On Hand         — ABC classification + margin velocity (stars vs dead capital)
  4. Sales           — turns per item category
  5. Reorder         — items below velocity reorder point

Entry point: get_inventory_velocity(year, month, category)
"""
from __future__ import annotations

import time
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.apps import apps as dj_apps
from django.db.models import Sum, Count, Avg, Q

# ---------------------------------------------------------------------------
# Optional import of existing inventory helpers — graceful fallback if absent
# ---------------------------------------------------------------------------
try:
    from apps.products.services.inventory_services import (
        classify_abc,
        compute_margin_velocity,
    )
    _HAS_INVENTORY_SERVICES = True
except ImportError:
    _HAS_INVENTORY_SERVICES = False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_MS_PER_DAY = 86_400_000  # epoch-ms per calendar day


def _safe_decimal(val: Any, default: Decimal = Decimal("0")) -> Decimal:
    """Coerce *val* to Decimal; return *default* on failure."""
    try:
        return Decimal(str(val))
    except Exception:
        return default


def _epoch_ms_to_days(ms: int | None) -> float | None:
    """Convert epoch-ms timestamp to days-since-epoch, or None."""
    if ms and ms > 0:
        return ms / _MS_PER_DAY
    return None


def _build_date_filter_ms(year: Optional[int], month: Optional[int]) -> tuple[int | None, int | None]:
    """Return (start_ms, end_ms) for the given year/month, or (None, None)."""
    if year is None:
        return None, None
    import datetime, calendar
    if month:
        start = datetime.date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end = datetime.date(year, month, last_day)
    else:
        start = datetime.date(year, 1, 1)
        end = datetime.date(year, 12, 31)
    start_ms = int(start.strftime("%s")) * 1000 if hasattr(start, 'strftime') else int(
        datetime.datetime(year, month or 1, 1).timestamp() * 1000
    )
    end_ms = int(
        datetime.datetime(
            end.year, end.month, end.day, 23, 59, 59
        ).timestamp() * 1000
    )
    return start_ms, end_ms


# ---------------------------------------------------------------------------
# Stage 1 — PO exposure (capital committed)
# ---------------------------------------------------------------------------

def _po_exposure(
    start_ms: int | None,
    end_ms: int | None,
    category: Optional[str],
) -> Dict[str, Any]:
    """Open PO value by vendor — capital committed but not yet received."""
    Purchase = dj_apps.get_model("transactions", "Purchase")
    PurchaseLine = dj_apps.get_model("transactions", "PurchaseLine")

    open_statuses = [
        Purchase.STATUS_PLANNED,
        Purchase.STATUS_RELEASED,
        Purchase.STATUS_IN_PROGRESS,
        Purchase.STATUS_HOLD,
    ]

    po_qs = Purchase.objects.filter(status__in=open_statuses, is_deleted=False)
    if start_ms:
        po_qs = po_qs.filter(dt_created__gte=start_ms)
    if end_ms:
        po_qs = po_qs.filter(dt_created__lte=end_ms)

    open_po_ids = list(po_qs.values_list("id", flat=True))

    line_qs = PurchaseLine.objects.filter(
        purchase_id__in=open_po_ids,
        is_deleted=False,
    )

    # Aggregate per vendor via header join
    vendor_rows: Dict[int, Dict] = {}
    total_value = Decimal("0")
    open_po_count = len(open_po_ids)

    for purchase in po_qs.select_related("vendor"):
        vendor = purchase.vendor
        v_id = vendor.id if vendor else 0
        v_name = str(vendor) if vendor else "Unknown"

        # Sum cost.total from the purchase header; fall back to totals.cost
        cost_blob = purchase.cost if isinstance(purchase.cost, dict) else {}
        totals_blob = purchase.totals if isinstance(purchase.totals, dict) else {}
        po_value = _safe_decimal(
            cost_blob.get("total") or totals_blob.get("cost") or totals_blob.get("total") or 0
        )

        total_value += po_value
        if v_id not in vendor_rows:
            vendor_rows[v_id] = {
                "vendor_id": v_id,
                "vendor_name": v_name,
                "po_count": 0,
                "total_value": Decimal("0"),
            }
        vendor_rows[v_id]["po_count"] += 1
        vendor_rows[v_id]["total_value"] += po_value

    by_vendor = sorted(
        [
            {
                "vendor_id": r["vendor_id"],
                "vendor_name": r["vendor_name"],
                "po_count": r["po_count"],
                "total_value": float(r["total_value"]),
            }
            for r in vendor_rows.values()
        ],
        key=lambda x: x["total_value"],
        reverse=True,
    )

    return {
        "total_value": float(total_value),
        "by_vendor": by_vendor,
        "open_po_count": open_po_count,
    }


# ---------------------------------------------------------------------------
# Stage 2 — Receipt performance (vendor reliability)
# ---------------------------------------------------------------------------

def _receipt_performance(
    start_ms: int | None,
    end_ms: int | None,
) -> Dict[str, Any]:
    """Avg days from PO creation to receipt, by vendor."""
    Receipt = dj_apps.get_model("transactions", "Receipt")

    receipt_qs = Receipt.objects.filter(
        source_type=Receipt.SOURCE_PURCHASE,
    ).select_related("purchase__vendor")

    if start_ms:
        receipt_qs = receipt_qs.filter(purchase__dt_created__gte=start_ms)
    if end_ms:
        receipt_qs = receipt_qs.filter(purchase__dt_created__lte=end_ms)

    vendor_days: Dict[int, List[float]] = {}
    all_days: List[float] = []
    on_time_count = 0
    total_count = 0

    for receipt in receipt_qs:
        purchase = receipt.purchase
        if not purchase:
            continue

        po_created_ms = purchase.dt_created or 0
        # dt_received is a DateTimeField — convert to epoch ms for diff
        if receipt.dt_received and po_created_ms:
            import datetime
            recv_ms = int(receipt.dt_received.timestamp() * 1000)
            diff_days = (recv_ms - po_created_ms) / _MS_PER_DAY
            if diff_days >= 0:
                all_days.append(diff_days)
                vendor = purchase.vendor
                v_id = vendor.id if vendor else 0
                vendor_days.setdefault(v_id, []).append(diff_days)

                # "on time" = within 30 days (reasonable default; no dt_needed on PO base model)
                dt_needed_ms = getattr(purchase, "dt_needed", None) or 0
                if dt_needed_ms and recv_ms <= dt_needed_ms:
                    on_time_count += 1
                elif diff_days <= 30:
                    on_time_count += 1
                total_count += 1

    avg_days = round(sum(all_days) / len(all_days), 1) if all_days else 0.0
    on_time_pct = round(on_time_count / total_count * 100, 1) if total_count else 0.0

    by_vendor = []
    for v_id, days_list in vendor_days.items():
        by_vendor.append({
            "vendor_id": v_id,
            "avg_days": round(sum(days_list) / len(days_list), 1),
        })
    by_vendor.sort(key=lambda x: x["avg_days"])

    return {
        "avg_days_to_receive": avg_days,
        "on_time_pct": on_time_pct,
        "by_vendor": by_vendor,
    }


# ---------------------------------------------------------------------------
# Stage 3 — On-hand analysis (ABC + margin velocity)
# ---------------------------------------------------------------------------

def _on_hand_analysis(category: Optional[str]) -> Dict[str, Any]:
    """ABC classification + dead capital vs star identification."""
    Item = dj_apps.get_model("products", "Item")

    item_qs = Item.objects.filter(is_active=True, is_deleted=False)
    if category:
        # category filter — try refs.categories or velocity_category
        item_qs = item_qs.filter(
            Q(velocity_category__iexact=category)
            | Q(refs__categories__icontains=category)
        )

    if _HAS_INVENTORY_SERVICES:
        # Use existing classify_abc + compute_margin_velocity
        item_ids = list(item_qs.values_list("id", flat=True))
        abc_map = classify_abc(item_ids)
        velocity_map = compute_margin_velocity(item_ids)
    else:
        abc_map = {}
        velocity_map = {}

    # Aggregate totals and class buckets
    total_value = Decimal("0")
    dead_capital_value = Decimal("0")
    star_value = Decimal("0")
    class_buckets: Dict[str, Dict] = {
        "A": {"class": "A", "item_count": 0, "value": Decimal("0")},
        "B": {"class": "B", "item_count": 0, "value": Decimal("0")},
        "C": {"class": "C", "item_count": 0, "value": Decimal("0")},
        "U": {"class": "U", "item_count": 0, "value": Decimal("0")},  # unclassified
    }

    for item in item_qs.only("id", "quantity", "cost", "price", "velocity_category"):
        qty_blob = item.quantity if isinstance(item.quantity, dict) else {}
        cost_blob = item.cost if isinstance(item.cost, dict) else {}
        on_hand = _safe_decimal(qty_blob.get("on_hand", 0))
        avg_cost = _safe_decimal(
            cost_blob.get("avg") or cost_blob.get("standard") or cost_blob.get("last") or 0
        )
        item_value = on_hand * avg_cost

        total_value += item_value

        # Velocity category (dead_capital / star come from compute_margin_velocity)
        v_data = velocity_map.get(item.id, {})
        vel_cat = v_data.get("category", "")
        if vel_cat == "dead_capital":
            dead_capital_value += item_value
        elif vel_cat == "star":
            star_value += item_value

        abc_class = abc_map.get(item.id, "U")
        bucket = class_buckets.get(abc_class, class_buckets["U"])
        bucket["item_count"] += 1
        bucket["value"] += item_value

    by_abc = []
    for cls, bucket in class_buckets.items():
        pct = float(bucket["value"] / total_value * 100) if total_value else 0.0
        by_abc.append({
            "class": cls,
            "item_count": bucket["item_count"],
            "value": float(bucket["value"]),
            "pct_of_total": round(pct, 1),
        })
    # Sort A→B→C→U
    sort_order = {"A": 0, "B": 1, "C": 2, "U": 3}
    by_abc.sort(key=lambda x: sort_order.get(x["class"], 9))

    return {
        "total_value": float(total_value),
        "by_abc": by_abc,
        "dead_capital_value": float(dead_capital_value),
        "star_value": float(star_value),
    }


# ---------------------------------------------------------------------------
# Stage 4 — Sales velocity (turns per category)
# ---------------------------------------------------------------------------

def _sales_velocity(
    start_ms: int | None,
    end_ms: int | None,
    category: Optional[str],
) -> Dict[str, Any]:
    """Inventory turns + margin velocity by item category."""
    if _HAS_INVENTORY_SERVICES:
        velocity_map = compute_margin_velocity()
    else:
        velocity_map = {}

    Item = dj_apps.get_model("products", "Item")
    item_qs = Item.objects.filter(is_active=True, is_deleted=False).only(
        "id", "velocity_category", "refs"
    )
    if category:
        item_qs = item_qs.filter(
            Q(velocity_category__iexact=category)
            | Q(refs__categories__icontains=category)
        )

    # Group by velocity_category
    cat_data: Dict[str, Dict] = {}
    for item in item_qs:
        cat = item.velocity_category or "uncategorized"
        if cat not in cat_data:
            cat_data[cat] = {"turns_list": [], "mv_list": []}
        v = velocity_map.get(item.id)
        if v:
            cat_data[cat]["turns_list"].append(v.get("annual_turns", 0))
            cat_data[cat]["mv_list"].append(v.get("margin_velocity", 0))

    by_category = []
    for cat, data in sorted(cat_data.items()):
        turns_list = data["turns_list"]
        mv_list = data["mv_list"]
        by_category.append({
            "category": cat,
            "turns": round(sum(turns_list) / len(turns_list), 2) if turns_list else 0.0,
            "margin_velocity": round(sum(mv_list) / len(mv_list), 4) if mv_list else 0.0,
        })
    by_category.sort(key=lambda x: x["turns"], reverse=True)

    return {"by_category": by_category}


# ---------------------------------------------------------------------------
# Stage 5 — Reorder alerts
# ---------------------------------------------------------------------------

def _reorder_alerts(category: Optional[str]) -> List[Dict[str, Any]]:
    """Items below their velocity-based reorder point."""
    Item = dj_apps.get_model("products", "Item")

    item_qs = Item.objects.filter(is_active=True, is_deleted=False)
    if category:
        item_qs = item_qs.filter(
            Q(velocity_category__iexact=category)
            | Q(refs__categories__icontains=category)
        )

    if _HAS_INVENTORY_SERVICES:
        item_ids = list(item_qs.values_list("id", flat=True))
        velocity_map = compute_margin_velocity(item_ids)
    else:
        velocity_map = {}

    alerts = []
    for item in item_qs.only("id", "ida", "quantity"):
        qty_blob = item.quantity if isinstance(item.quantity, dict) else {}
        on_hand = float(_safe_decimal(qty_blob.get("on_hand", 0)))
        # inventory_min from quantity JSON is the canonical reorder floor
        reorder_point = float(_safe_decimal(qty_blob.get("inventory_min", 0)))

        v = velocity_map.get(item.id, {})
        annual_turns = float(v.get("annual_turns", 0))
        margin_velocity = float(v.get("margin_velocity", 0))

        # days_of_supply = (on_hand / daily_demand) where daily_demand = annual_turns * avg_on_hand / 365
        # Simplified: if annual_turns > 0, days_of_supply = on_hand / (annual_turns / 365)
        daily_demand = annual_turns / 365 if annual_turns > 0 else 0
        days_of_supply = round(on_hand / daily_demand, 0) if daily_demand > 0 else None

        if on_hand <= reorder_point:
            alerts.append({
                "item_id": item.id,
                "item_ida": item.ida or "",
                "on_hand": on_hand,
                "reorder_point": reorder_point,
                "velocity": round(annual_turns, 2),
                "days_of_supply": days_of_supply,
            })

    # Sort: most urgent first (fewest days of supply, or on_hand=0)
    alerts.sort(key=lambda x: (x["days_of_supply"] is None, x.get("days_of_supply") or 0))
    return alerts


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def get_inventory_velocity(
    year: Optional[int] = None,
    month: Optional[int] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """Capital flow analysis across the five inventory stages.

    Args:
        year:     Filter by year (e.g. 2026). None = all time.
        month:    Filter by month 1-12. Requires year. None = full year.
        category: Item velocity_category slug filter. None = all categories.

    Returns:
        dict with keys:
          po_exposure, receipt_performance, on_hand_analysis,
          sales_velocity, reorder_alerts, summary, dt_generated
    """
    start_ms, end_ms = _build_date_filter_ms(year, month)

    po_exposure = _po_exposure(start_ms, end_ms, category)
    receipt_performance = _receipt_performance(start_ms, end_ms)
    on_hand = _on_hand_analysis(category)
    sales = _sales_velocity(start_ms, end_ms, category)
    reorder = _reorder_alerts(category)

    total_inventory_value = on_hand["total_value"]
    total_po_exposure = po_exposure["total_value"]
    dead_capital_pct = (
        round(on_hand["dead_capital_value"] / total_inventory_value * 100, 1)
        if total_inventory_value
        else 0.0
    )

    return {
        "po_exposure": po_exposure,
        "receipt_performance": receipt_performance,
        "on_hand_analysis": on_hand,
        "sales_velocity": sales,
        "reorder_alerts": reorder,
        "summary": {
            "total_inventory_value": total_inventory_value,
            "total_po_exposure": total_po_exposure,
            "items_below_reorder": len(reorder),
            "dead_capital_pct": dead_capital_pct,
        },
        "dt_generated": int(time.time() * 1000),
    }


__all__ = ["get_inventory_velocity"]
