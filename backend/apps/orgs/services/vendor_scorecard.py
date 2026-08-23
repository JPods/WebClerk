"""Vendor Scorecard Service — compute vendor performance from Receipt vs PO data.

Metrics per vendor:
  - On-time delivery %   (receipts within lead_time_days of PO date)
  - Fill rate %          (qty received vs qty ordered)
  - Quality score        (from complaints in vendor.financial.vendor.complaints)
  - Pricing accuracy %   (PO cost vs receipt cost variance)
  - Overall score        (weighted composite)

Weights: on_time 40%, fill_rate 30%, quality 20%, pricing 10%.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)

WEIGHTS = {
    "on_time":  Decimal("0.40"),
    "fill_rate": Decimal("0.30"),
    "quality":  Decimal("0.20"),
    "pricing":  Decimal("0.10"),
}

# Maximum complaints before quality score hits 0.  Tunable.
COMPLAINT_CAP = 20


def _epoch_ms_cutoff(period_days: int) -> int:
    """Return epoch-millisecond timestamp for `period_days` ago."""
    cutoff = timezone.now() - timedelta(days=period_days)
    return int(cutoff.timestamp() * 1000)


def _safe_decimal(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    """Coerce jsonb numeric to Decimal safely."""
    if value is None:
        return default
    try:
        return Decimal(str(value))
    except Exception:
        return default


def _jsonb_qty(quantity_jsonb: dict | None, key: str = "active") -> Decimal:
    """Extract quantity from the jsonb quantity field."""
    if not quantity_jsonb or not isinstance(quantity_jsonb, dict):
        return Decimal("0")
    return _safe_decimal(quantity_jsonb.get(key, 0))


def _jsonb_cost_extended(cost_jsonb: dict | None) -> Decimal:
    """Extract extended cost from the jsonb cost field."""
    if not cost_jsonb or not isinstance(cost_jsonb, dict):
        return Decimal("0")
    return _safe_decimal(cost_jsonb.get("extended", 0))


# ---------------------------------------------------------------------------
# Core metric computation
# ---------------------------------------------------------------------------

def _compute_on_time(purchases, receipts_by_po, lead_time_days: int) -> dict:
    """On-time delivery %: receipt received within lead_time_days of PO date."""
    total = 0
    on_time = 0
    details = []

    for po in purchases:
        po_receipts = receipts_by_po.get(po.id, [])
        if not po_receipts:
            continue
        total += 1
        # PO date is epoch-ms; receipt dt_received is a datetime
        po_dt = po.dt_created  # epoch ms
        deadline_ms = po_dt + (lead_time_days * 86_400_000)
        # Check if ANY receipt arrived on time
        earliest_receipt_ms = min(
            int(r.dt_received.timestamp() * 1000) for r in po_receipts
        )
        arrived_on_time = earliest_receipt_ms <= deadline_ms
        if arrived_on_time:
            on_time += 1
        details.append({
            "purchase_id": po.id,
            "po_date_ms": po_dt,
            "deadline_ms": deadline_ms,
            "receipt_date_ms": earliest_receipt_ms,
            "on_time": arrived_on_time,
        })

    pct = Decimal("100") * Decimal(on_time) / Decimal(total) if total else Decimal("100")
    return {
        "on_time_count": on_time,
        "total_pos_with_receipts": total,
        "pct": pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "details": details,
    }


def _compute_fill_rate(po_lines, receipt_lines_by_pol) -> dict:
    """Fill rate %: total qty received / total qty ordered."""
    total_ordered = Decimal("0")
    total_received = Decimal("0")

    for pol in po_lines:
        qty_ordered = _jsonb_qty(pol.quantity, "active")
        if qty_ordered <= 0:
            # Also try top-level 'ordered' key
            qty_ordered = _jsonb_qty(pol.quantity, "ordered")
        if qty_ordered <= 0:
            continue
        total_ordered += qty_ordered

        matched_rls = receipt_lines_by_pol.get(pol.id, [])
        for rl in matched_rls:
            total_received += _jsonb_qty(rl.quantity, "active")

    if total_ordered == 0:
        pct = Decimal("100")
    else:
        pct = (Decimal("100") * total_received / total_ordered).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        # Cap at 100 — over-shipment doesn't improve score
        pct = min(pct, Decimal("100"))

    return {
        "total_ordered": float(total_ordered),
        "total_received": float(total_received),
        "pct": pct,
    }


def _compute_quality_score(vendor) -> dict:
    """Quality score (0–100) based on complaint counts in financial JSON."""
    fin = vendor.financial or {}
    vendor_fin = fin.get("vendor", {})
    complaints = vendor_fin.get("complaints", {})

    our_fault = int(complaints.get("our_fault", 0))
    their_fault = int(complaints.get("their_fault", 0))
    unresolved = int(complaints.get("unresolved", 0))

    # Only vendor-attributable complaints count against them
    chargeable = their_fault + unresolved
    # Linear scale: 0 complaints = 100, COMPLAINT_CAP+ = 0
    score = max(
        Decimal("0"),
        Decimal("100") - (Decimal("100") * Decimal(chargeable) / Decimal(COMPLAINT_CAP))
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "our_fault": our_fault,
        "their_fault": their_fault,
        "unresolved": unresolved,
        "chargeable": chargeable,
        "score": score,
    }


def _compute_pricing_accuracy(po_lines, receipt_lines_by_pol) -> dict:
    """Pricing accuracy %: how close receipt costs match PO costs."""
    total_po_cost = Decimal("0")
    total_variance = Decimal("0")
    compared = 0

    for pol in po_lines:
        po_ext = _jsonb_cost_extended(pol.cost)
        if po_ext <= 0:
            continue
        matched_rls = receipt_lines_by_pol.get(pol.id, [])
        for rl in matched_rls:
            rl_ext = _jsonb_cost_extended(rl.cost)
            if rl_ext <= 0:
                continue
            total_po_cost += po_ext
            total_variance += abs(po_ext - rl_ext)
            compared += 1

    if total_po_cost == 0 or compared == 0:
        pct = Decimal("100")
    else:
        variance_pct = (total_variance / total_po_cost) * Decimal("100")
        pct = max(Decimal("0"), Decimal("100") - variance_pct).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    return {
        "total_po_cost": float(total_po_cost),
        "total_variance": float(total_variance),
        "lines_compared": compared,
        "pct": pct,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_vendor_scorecard(vendor_id: int, period_days: int = 90) -> dict:
    """Compute vendor performance scorecard.

    Returns dict with on_time_pct, fill_rate_pct, quality_score,
    pricing_accuracy_pct, overall_score, and details.
    """
    from apps.orgs.models import OrgBase
    from apps.transactions.models.purchase import Purchase
    from apps.transactions.models.purchase_line import PurchaseLine
    from apps.transactions.models.receipt import Receipt
    from apps.transactions.models.receipt_line import ReceiptLine

    try:
        vendor = OrgBase.objects.get(pk=vendor_id)
    except OrgBase.DoesNotExist:
        return {"error": f"Vendor {vendor_id} not found"}

    cutoff_ms = _epoch_ms_cutoff(period_days)

    # -- Fetch POs for this vendor in the period --
    purchases = list(
        Purchase.objects.filter(
            vendor_id=vendor_id,
            dt_created__gte=cutoff_ms,
            is_deleted=False,
        ).order_by("dt_created")
    )
    po_ids = [po.id for po in purchases]

    # -- Fetch receipts linked to those POs --
    receipts = list(
        Receipt.objects.filter(
            purchase_id__in=po_ids,
            is_deleted=False,
        )
    ) if po_ids else []
    receipts_by_po: dict[int, list] = {}
    for r in receipts:
        receipts_by_po.setdefault(r.purchase_id, []).append(r)

    # -- Fetch PO lines --
    po_lines = list(
        PurchaseLine.objects.filter(
            purchase_id__in=po_ids,
            is_deleted=False,
        )
    ) if po_ids else []

    # -- Fetch receipt lines matched to PO lines --
    receipt_ids = [r.id for r in receipts]
    receipt_lines = list(
        ReceiptLine.objects.filter(
            receipt_id__in=receipt_ids,
            is_deleted=False,
        )
    ) if receipt_ids else []
    receipt_lines_by_pol: dict[int, list] = {}
    for rl in receipt_lines:
        if rl.purchase_line_id:
            receipt_lines_by_pol.setdefault(rl.purchase_line_id, []).append(rl)

    # -- Lead time from vendor financial JSON --
    fin = vendor.financial or {}
    mfr_fin = fin.get("manufacturer", {})
    lead_time_days = int(mfr_fin.get("lead_time_days", 14))
    if lead_time_days <= 0:
        lead_time_days = 14  # sensible default

    # -- Compute each metric --
    on_time = _compute_on_time(purchases, receipts_by_po, lead_time_days)
    fill_rate = _compute_fill_rate(po_lines, receipt_lines_by_pol)
    quality = _compute_quality_score(vendor)
    pricing = _compute_pricing_accuracy(po_lines, receipt_lines_by_pol)

    # -- Weighted overall score --
    overall = (
        WEIGHTS["on_time"]  * on_time["pct"] +
        WEIGHTS["fill_rate"] * fill_rate["pct"] +
        WEIGHTS["quality"]  * quality["score"] +
        WEIGHTS["pricing"]  * pricing["pct"]
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "vendor_id": vendor_id,
        "vendor_name": getattr(vendor, "name", str(vendor_id)),
        "period_days": period_days,
        "on_time_pct": float(on_time["pct"]),
        "fill_rate_pct": float(fill_rate["pct"]),
        "quality_score": float(quality["score"]),
        "pricing_accuracy_pct": float(pricing["pct"]),
        "overall_score": float(overall),
        "details": {
            "on_time": {k: v for k, v in on_time.items() if k != "details"},
            "fill_rate": fill_rate,
            "quality": quality,
            "pricing": pricing,
            "lead_time_days": lead_time_days,
            "po_count": len(purchases),
            "receipt_count": len(receipts),
        },
    }


def update_vendor_scorecard(vendor_id: int) -> dict:
    """Compute scorecard and persist it in vendor.financial.vendor.scorecard."""
    from apps.orgs.models import OrgBase

    scorecard = compute_vendor_scorecard(vendor_id)
    if "error" in scorecard:
        return scorecard

    try:
        vendor = OrgBase.objects.get(pk=vendor_id)
    except OrgBase.DoesNotExist:
        return {"error": f"Vendor {vendor_id} not found"}

    fin = vendor.financial or {}
    if "vendor" not in fin:
        fin["vendor"] = {}

    fin["vendor"]["scorecard"] = {
        "on_time_pct": scorecard["on_time_pct"],
        "fill_rate_pct": scorecard["fill_rate_pct"],
        "quality_score": scorecard["quality_score"],
        "pricing_accuracy_pct": scorecard["pricing_accuracy_pct"],
        "overall_score": scorecard["overall_score"],
        "period_days": scorecard["period_days"],
        "dt_computed": int(timezone.now().timestamp() * 1000),
    }

    vendor.financial = fin
    vendor.save(update_fields=["financial", "dt_modified"])
    logger.info("Vendor scorecard updated for vendor_id=%s, overall=%.1f",
                vendor_id, scorecard["overall_score"])

    return scorecard


def get_all_vendor_scores() -> list[dict]:
    """Return all vendors with their scorecard, sorted by overall_score desc."""
    from apps.orgs.models.vendor import Vendor

    vendors = Vendor.objects.filter(is_deleted=False, is_active=True)
    results = []

    for v in vendors:
        fin = v.financial or {}
        vendor_fin = fin.get("vendor", {})
        sc = vendor_fin.get("scorecard")
        if sc:
            results.append({
                "vendor_id": v.pk,
                "vendor_name": getattr(v, "name", str(v.pk)),
                "overall_score": sc.get("overall_score", 0),
                "on_time_pct": sc.get("on_time_pct", 0),
                "fill_rate_pct": sc.get("fill_rate_pct", 0),
                "quality_score": sc.get("quality_score", 0),
                "pricing_accuracy_pct": sc.get("pricing_accuracy_pct", 0),
                "period_days": sc.get("period_days", 90),
                "dt_computed": sc.get("dt_computed"),
            })
        else:
            # No stored scorecard — compute live
            scorecard = compute_vendor_scorecard(v.pk)
            if "error" not in scorecard:
                results.append({
                    "vendor_id": v.pk,
                    "vendor_name": getattr(v, "name", str(v.pk)),
                    "overall_score": scorecard["overall_score"],
                    "on_time_pct": scorecard["on_time_pct"],
                    "fill_rate_pct": scorecard["fill_rate_pct"],
                    "quality_score": scorecard["quality_score"],
                    "pricing_accuracy_pct": scorecard["pricing_accuracy_pct"],
                    "period_days": scorecard["period_days"],
                    "dt_computed": None,
                })

    results.sort(key=lambda r: r["overall_score"], reverse=True)
    return results
