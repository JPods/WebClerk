"""
End of Month (EOM) Close Service
=================================

Period closing procedure: aging recalculation, GL balance verification,
period summary generation, transaction locking, and audit trail.

WebClerk is commerce, not accounting. EOM produces summary data and locks
transactions so they feed cleanly into an accounting program. It does not
produce financial statements.

All datetimes are UTC (Axiom 14).
"""
from __future__ import annotations

import copy
import logging
import time
from datetime import date, datetime, timezone as dt_tz
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.apps import apps as dj_apps
from django.db import transaction
from django.db.models import Sum, Q, F

logger = logging.getLogger(__name__)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _period_range(year: int, month: int):
    """Return (start_dt, end_dt) as timezone-aware datetimes for a period."""
    start = datetime(year, month, 1, tzinfo=dt_tz.utc)
    # End of month: first day of next month
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=dt_tz.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=dt_tz.utc)
    return start, end


def _period_range_ms(year: int, month: int):
    """Return (start_ms, end_ms) as epoch milliseconds for a period."""
    start, end = _period_range(year, month)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def _compute_aging_for_source(source: str, as_of: date) -> int:
    """Recalculate aging buckets for all orgs with open ledger entries.

    Args:
        source: 'AR' for customers, 'AP' for vendors
        as_of: date to compute aging against

    Returns:
        Number of orgs aged.
    """
    Ledger = dj_apps.get_model("accounts", "Ledger")
    OrgBase = dj_apps.get_model("orgs", "OrgBase")

    # Fetch all open ledger entries for this source
    entries = (
        Ledger.objects
        .filter(source=source, is_settled=False)
        .exclude(value_available=0)
        .exclude(value_available__isnull=True)
        .values("org_id", "dt_due", "value_available")
    )

    # Build per-org aging buckets
    org_buckets: Dict[int, Dict[str, Decimal]] = {}
    for rec in entries:
        oid = rec["org_id"]
        if oid is None:
            continue

        if oid not in org_buckets:
            org_buckets[oid] = {
                "current": Decimal("0"),
                "past_30": Decimal("0"),
                "past_60": Decimal("0"),
                "past_90": Decimal("0"),
                "total": Decimal("0"),
            }

        bucket = org_buckets[oid]
        value = Decimal(str(rec["value_available"] or 0))
        bucket["total"] += value

        dt_due = rec["dt_due"]
        if dt_due is None:
            bucket["current"] += value
            continue

        due_date = dt_due.date() if isinstance(dt_due, datetime) else dt_due
        days = (as_of - due_date).days

        if days < 30:
            bucket["current"] += value
        elif days < 60:
            bucket["past_30"] += value
        elif days < 90:
            bucket["past_60"] += value
        else:
            bucket["past_90"] += value

    # Update org financial data with aging
    aging_key = "customer" if source == "AR" else "vendor"
    orgs_aged = 0

    for oid, buckets in org_buckets.items():
        try:
            org = OrgBase.objects.get(pk=oid)
            financial = copy.deepcopy(getattr(org, "financial", None) or {})
            entity = financial.setdefault(aging_key, {})
            entity["aging"] = {
                "current": float(buckets["current"]),
                "past_30": float(buckets["past_30"]),
                "past_60": float(buckets["past_60"]),
                "past_90": float(buckets["past_90"]),
                "total": float(buckets["total"]),
                "as_of": as_of.isoformat(),
                "dt_computed": _now_ms(),
            }
            org.financial = financial
            org.save(update_fields=["financial", "dt_modified", "version"])
            orgs_aged += 1
        except Exception as e:
            logger.warning("EOM aging update failed for org %s: %s", oid, e)

    return orgs_aged


def _verify_gl_balance(year: int, month: int) -> Dict[str, Any]:
    """Verify GL balance for a period: total debits must equal total credits.

    Uses GlJournal entries created during the period.
    """
    try:
        GlJournal = dj_apps.get_model("accounts", "GlJournal")
    except LookupError:
        # Model may not exist yet
        return {"balanced": True, "total_debits": 0, "total_credits": 0, "difference": 0}

    start, end = _period_range(year, month)

    totals = GlJournal.objects.filter(
        dt_created__gte=start, dt_created__lt=end
    ).aggregate(
        total_debits=Sum("debit"),
        total_credits=Sum("credit"),
    )

    debits = totals["total_debits"] or Decimal("0")
    credits = totals["total_credits"] or Decimal("0")
    diff = debits - credits

    return {
        "balanced": abs(diff) < Decimal("0.01"),
        "total_debits": float(debits),
        "total_credits": float(credits),
        "difference": float(diff),
    }


def _generate_period_summary(year: int, month: int) -> Dict[str, Any]:
    """Generate summary totals for the period."""
    start, end = _period_range(year, month)

    summary = {
        "total_sales": 0,
        "total_purchases": 0,
        "total_payments": 0,
        "total_commissions": 0,
        "invoice_count": 0,
        "purchase_count": 0,
        "payment_count": 0,
    }

    # Sales (invoices)
    try:
        Invoice = dj_apps.get_model("transactions", "Invoice")
        invoices = Invoice.objects.filter(dt_created__gte=start, dt_created__lt=end)
        agg = invoices.aggregate(total=Sum("total"))
        summary["total_sales"] = float(agg["total"] or 0)
        summary["invoice_count"] = invoices.count()
    except Exception as e:
        logger.warning("EOM: invoice summary failed: %s", e)

    # Purchases
    try:
        Purchase = dj_apps.get_model("transactions", "Purchase")
        purchases = Purchase.objects.filter(dt_created__gte=start, dt_created__lt=end)
        agg = purchases.aggregate(total=Sum("total"))
        summary["total_purchases"] = float(agg["total"] or 0)
        summary["purchase_count"] = purchases.count()
    except Exception as e:
        logger.warning("EOM: purchase summary failed: %s", e)

    # Payments
    try:
        Payment = dj_apps.get_model("transactions", "Payment")
        payments = Payment.objects.filter(dt_created__gte=start, dt_created__lt=end)
        agg = payments.aggregate(total=Sum("total"))
        summary["total_payments"] = float(agg["total"] or 0)
        summary["payment_count"] = payments.count()
    except Exception as e:
        logger.warning("EOM: payment summary failed: %s", e)

    # Commissions — sum from invoice commission JSON where accrued
    try:
        Invoice = dj_apps.get_model("transactions", "Invoice")
        comm_invoices = Invoice.objects.filter(
            dt_created__gte=start, dt_created__lt=end,
            commission__isnull=False,
        ).exclude(commission={})
        total_comm = Decimal("0")
        for inv in comm_invoices:
            comm = inv.commission or {}
            amt = comm.get("amount") or comm.get("total") or 0
            total_comm += Decimal(str(amt))
        summary["total_commissions"] = float(total_comm)
    except Exception as e:
        logger.warning("EOM: commission summary failed: %s", e)

    return summary


def _lock_period_transactions(year: int, month: int) -> int:
    """Lock all journalized transactions for the period.

    Only locks records that have already been journalized (is_locked=True
    is set by the journalize service). This sets a period lock flag
    in metadata to prevent reopening without explicit reopen_period.

    Returns count of records marked.
    """
    start, end = _period_range(year, month)
    locked_count = 0
    period_key = f"{year}-{month:02d}"

    for model_name in ("Invoice", "Payment", "Purchase"):
        try:
            Model = dj_apps.get_model("transactions", model_name)
            records = Model.objects.filter(
                dt_created__gte=start,
                dt_created__lt=end,
                is_locked=True,
            )
            for record in records:
                meta = copy.deepcopy(getattr(record, "metadata", None) or {})
                eom = meta.setdefault("eom", {})
                if eom.get("period_locked") == period_key:
                    continue  # already locked for this period
                eom["period_locked"] = period_key
                eom["dt_period_locked"] = _now_ms()
                record.metadata = meta
                record.save(update_fields=["metadata", "dt_modified", "version"])
                locked_count += 1
        except Exception as e:
            logger.warning("EOM: lock failed for %s: %s", model_name, e)

    return locked_count


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@transaction.atomic
def run_eom_close(
    period_year: int,
    period_month: int,
    contact_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Run end-of-month closing procedure.

    Steps:
        1. Recalculate customer aging (AR)
        2. Recalculate vendor aging (AP)
        3. Verify GL balance (debits = credits)
        4. Generate period summary
        5. Lock journalized transactions for the period
        6. Create EOM document record with summary
        7. Return results

    Args:
        period_year: 4-digit year
        period_month: 1-12
        contact_id: who initiated the close (for audit)

    Returns:
        {period, gl_balanced, total_sales, total_purchases, total_payments,
         customers_aged, vendors_aged, transactions_locked}
    """
    if not (1 <= period_month <= 12):
        raise ValueError("period_month must be 1-12")
    if period_year < 2000 or period_year > 2100:
        raise ValueError("period_year must be 2000-2100")

    period_key = f"{period_year}-{period_month:02d}"
    as_of = date(period_year, period_month, 1)
    # Use last day of month for aging
    if period_month == 12:
        as_of_end = date(period_year, 12, 31)
    else:
        as_of_end = date(period_year, period_month + 1, 1)
        from datetime import timedelta
        as_of_end = as_of_end - timedelta(days=1)

    # 1. Customer aging
    customers_aged = _compute_aging_for_source("AR", as_of_end)

    # 2. Vendor aging
    vendors_aged = _compute_aging_for_source("AP", as_of_end)

    # 3. GL balance verification
    gl_result = _verify_gl_balance(period_year, period_month)

    # 4. Period summary
    summary = _generate_period_summary(period_year, period_month)

    # 5. Lock transactions
    transactions_locked = _lock_period_transactions(period_year, period_month)

    # 6. Create EOM document record
    try:
        Document = dj_apps.get_model("docs", "Document")
        eom_doc = Document(
            name=f"EOM Close — {period_key}",
            model_name="eom_close",
            status="active",
            body=f"End of month close for {period_key}",
            data={
                "period": period_key,
                "period_year": period_year,
                "period_month": period_month,
                "gl_balanced": gl_result["balanced"],
                "gl_debits": gl_result["total_debits"],
                "gl_credits": gl_result["total_credits"],
                "gl_difference": gl_result["difference"],
                "total_sales": summary["total_sales"],
                "total_purchases": summary["total_purchases"],
                "total_payments": summary["total_payments"],
                "total_commissions": summary["total_commissions"],
                "invoice_count": summary["invoice_count"],
                "purchase_count": summary["purchase_count"],
                "payment_count": summary["payment_count"],
                "customers_aged": customers_aged,
                "vendors_aged": vendors_aged,
                "transactions_locked": transactions_locked,
                "dt_closed": _now_ms(),
                "closed_by_contact_id": contact_id,
            },
        )
        eom_doc.save()
        doc_id = eom_doc.pk
    except Exception as e:
        logger.error("EOM: failed to create document record: %s", e)
        doc_id = None

    return {
        "period": period_key,
        "document_id": doc_id,
        "gl_balanced": gl_result["balanced"],
        "gl_debits": gl_result["total_debits"],
        "gl_credits": gl_result["total_credits"],
        "total_sales": summary["total_sales"],
        "total_purchases": summary["total_purchases"],
        "total_payments": summary["total_payments"],
        "total_commissions": summary["total_commissions"],
        "customers_aged": customers_aged,
        "vendors_aged": vendors_aged,
        "transactions_locked": transactions_locked,
    }


def get_eom_status(
    period_year: int,
    period_month: int,
) -> Dict[str, Any]:
    """Check if EOM has been run for a period and what is pending.

    Returns:
        {closed, dt_closed, pending_invoices, pending_payments, gl_balance}
    """
    if not (1 <= period_month <= 12):
        raise ValueError("period_month must be 1-12")

    period_key = f"{period_year}-{period_month:02d}"
    start, end = _period_range(period_year, period_month)

    # Check if EOM document exists
    closed = False
    dt_closed = None
    try:
        Document = dj_apps.get_model("docs", "Document")
        eom_doc = Document.objects.filter(
            model_name="eom_close",
            name__icontains=period_key,
        ).order_by("-dt_created").first()

        if eom_doc and eom_doc.config:
            closed = True
            dt_closed = eom_doc.config.get("dt_closed")
    except Exception:
        pass

    # Count pending (unjournalized) invoices
    pending_invoices = 0
    try:
        Invoice = dj_apps.get_model("transactions", "Invoice")
        pending_invoices = Invoice.objects.filter(
            dt_created__gte=start, dt_created__lt=end,
            is_locked=False,
        ).count()
    except Exception:
        pass

    # Count pending payments
    pending_payments = 0
    try:
        Payment = dj_apps.get_model("transactions", "Payment")
        pending_payments = Payment.objects.filter(
            dt_created__gte=start, dt_created__lt=end,
            is_locked=False,
        ).count()
    except Exception:
        pass

    # GL balance
    gl_result = _verify_gl_balance(period_year, period_month)

    return {
        "period": period_key,
        "closed": closed,
        "dt_closed": dt_closed,
        "pending_invoices": pending_invoices,
        "pending_payments": pending_payments,
        "gl_balance": gl_result,
    }


@transaction.atomic
def reopen_period(
    period_year: int,
    period_month: int,
    contact_id: int,
    reason: str,
) -> Dict[str, Any]:
    """Unlock a closed period for corrections.

    Requires reason for audit trail. Removes period_locked from transaction
    metadata and marks the EOM document as reopened.

    Args:
        period_year: 4-digit year
        period_month: 1-12
        contact_id: who is reopening (required for audit)
        reason: why the period is being reopened (required)

    Returns:
        {period, reopened, transactions_unlocked, reason}
    """
    if not reason or not reason.strip():
        raise ValueError("reason is required to reopen a period")
    if not contact_id:
        raise ValueError("contact_id is required to reopen a period")
    if not (1 <= period_month <= 12):
        raise ValueError("period_month must be 1-12")

    period_key = f"{period_year}-{period_month:02d}"
    start, end = _period_range(period_year, period_month)

    # Remove period lock from transactions
    unlocked = 0
    for model_name in ("Invoice", "Payment", "Purchase"):
        try:
            Model = dj_apps.get_model("transactions", model_name)
            records = Model.objects.filter(
                dt_created__gte=start,
                dt_created__lt=end,
            )
            for record in records:
                meta = copy.deepcopy(getattr(record, "metadata", None) or {})
                eom = meta.get("eom", {})
                if eom.get("period_locked") == period_key:
                    eom.pop("period_locked", None)
                    eom.pop("dt_period_locked", None)
                    # Audit trail
                    reopens = eom.setdefault("reopens", [])
                    reopens.append({
                        "contact_id": contact_id,
                        "reason": reason.strip(),
                        "dt_reopened": _now_ms(),
                    })
                    meta["eom"] = eom
                    record.metadata = meta
                    record.save(update_fields=["metadata", "dt_modified", "version"])
                    unlocked += 1
        except Exception as e:
            logger.warning("EOM reopen: unlock failed for %s: %s", model_name, e)

    # Mark EOM document as reopened
    try:
        Document = dj_apps.get_model("docs", "Document")
        eom_doc = Document.objects.filter(
            model_name="eom_close",
            name__icontains=period_key,
        ).order_by("-dt_created").first()

        if eom_doc:
            data = copy.deepcopy(eom_doc.config or {})
            data["reopened"] = True
            data["dt_reopened"] = _now_ms()
            data["reopened_by_contact_id"] = contact_id
            data["reopen_reason"] = reason.strip()
            eom_doc.config = data
            eom_doc.status = "reopened"
            eom_doc.save(update_fields=["config", "status", "dt_modified", "version"])
    except Exception as e:
        logger.warning("EOM reopen: document update failed: %s", e)

    return {
        "period": period_key,
        "reopened": True,
        "transactions_unlocked": unlocked,
        "reason": reason.strip(),
        "contact_id": contact_id,
    }
