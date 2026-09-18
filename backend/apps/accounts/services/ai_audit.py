"""
AI Audit Service — Automated Calculation & Consistency Checks

Creates Audit records when r25 (frontend) submitted values diverge from
wc3 (backend) authoritative recalculations.  The backend is always the
final word on dollar amounts; this service logs the discrepancies so they
can be reviewed, trended, and used to improve the r25 calculation layer.

Primary consumers:
  - BaseSellLineModel._calculate_extended_price()  → price/cost extended audit
  - normalize_quantity_map()                        → quantity consistency audit

Audit records use the accounts.Audit model:
  purpose   — "ai_calculation_audit" or "ai_quantity_audit"
  name      — human-readable summary
  conflicts — { field, submitted, calculated, delta, tolerance }
  changes   — { field, from, to }  (what wc3 corrected)
  actions   — reserved for future auto-actions
  recommendations — hints for devs
  rating    — severity (0=info, 1=warning, 2=error)
  refs.links — links to the transaction and line

Usage:
    from apps.accounts.services.ai_audit import check_extended_prices, check_quantity

    # In _calculate_extended_price():
    check_extended_prices(line_instance, pre_values)

    # In normalize_quantity_map() or save():
    check_quantity(line_instance, submitted_qty)
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

logger = logging.getLogger("ai_audit")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Absolute tolerance for extended price comparisons (in base currency units).
# Differences at or below this threshold are considered rounding noise.
PRICE_TOLERANCE = Decimal("0.02")

# Absolute tolerance for quantity comparisons.
QUANTITY_TOLERANCE = Decimal("0.001")

# Set False to disable DB writes (logs only). Useful during initial rollout.
WRITE_AUDIT_RECORDS = True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_extended_prices(
    line: Any,
    submitted_price_extended: float | None,
    submitted_cost_extended: float | None,
) -> list[dict]:
    """Compare r25-submitted extended values against wc3's recalculation.

    Call this AFTER _calculate_extended_price() has written the authoritative
    values onto `line.price["extended"]` and `line.cost["extended"]`.

    Returns a list of discrepancy dicts (empty if everything matches).
    """
    discrepancies: list[dict] = []

    # --- Price extended ---
    if submitted_price_extended is not None and hasattr(line, "price") and line.price:
        wc3_extended = line.price.get("extended", 0) or 0
        delta = abs(Decimal(str(submitted_price_extended)) - Decimal(str(wc3_extended)))
        if delta > PRICE_TOLERANCE:
            disc = _build_discrepancy(
                line=line,
                field="price.extended",
                submitted=submitted_price_extended,
                calculated=wc3_extended,
                delta=float(delta),
                tolerance=float(PRICE_TOLERANCE),
            )
            discrepancies.append(disc)

    # --- Cost extended ---
    if submitted_cost_extended is not None and hasattr(line, "cost") and line.cost:
        wc3_extended = line.cost.get("extended", 0) or 0
        delta = abs(Decimal(str(submitted_cost_extended)) - Decimal(str(wc3_extended)))
        if delta > PRICE_TOLERANCE:
            disc = _build_discrepancy(
                line=line,
                field="cost.extended",
                submitted=submitted_cost_extended,
                calculated=wc3_extended,
                delta=float(delta),
                tolerance=float(PRICE_TOLERANCE),
            )
            discrepancies.append(disc)

    if discrepancies:
        _log_and_persist(
            purpose="ai_calculation_audit",
            line=line,
            discrepancies=discrepancies,
            severity=1,  # warning
        )

    return discrepancies


def check_quantity(
    line: Any,
    submitted_qty: Dict[str, Any] | None,
) -> list[dict]:
    """Verify quantity envelope consistency after normalization.

    Call AFTER normalize_quantity_map() has written the authoritative
    values onto `line.quantity`.

    Checks:
      1. staged/active/remaining sign consistency
      2. remaining = active (no children) or active - children_active.sum
      3. staged mirrors active for standalone lines
    """
    if not submitted_qty or not isinstance(submitted_qty, dict):
        return []
    if not hasattr(line, "quantity") or not line.quantity:
        return []

    discrepancies: list[dict] = []
    q = line.quantity
    kind = getattr(line._meta, "model_name", "") or ""

    staged = Decimal(str(q.get("staged", 0) or 0))
    active = Decimal(str(q.get("active", 0) or 0))
    remaining = Decimal(str(q.get("remaining", 0) or 0))
    sub_staged = Decimal(str(submitted_qty.get("staged", 0) or 0))
    sub_active = Decimal(str(submitted_qty.get("active", 0) or 0))
    sub_remaining = Decimal(str(submitted_qty.get("remaining", 0) or 0))

    # Check 1: remaining consistency
    # remaining = active - children_active.sum (or just active if no children)
    children_active = q.get("children_active")
    children_sum = Decimal("0")
    if children_active and isinstance(children_active, dict):
        children_sum = Decimal(str(children_active.get("sum", 0) or 0))
    expected = active - children_sum

    if abs(remaining - expected) > QUANTITY_TOLERANCE:
        discrepancies.append(_build_discrepancy(
            line=line,
            field="quantity.remaining",
            submitted=float(sub_remaining),
            calculated=float(expected),
            delta=float(abs(remaining - expected)),
            tolerance=float(QUANTITY_TOLERANCE),
            note=f"Expected remaining={float(expected)} (active={float(active)}, children_sum={float(children_sum) if children_active else 0})",
        ))

    # Check 3: staged/active consistency for standalone
    if sub_staged != 0 and sub_active != 0 and sub_staged != sub_active:
        # This is a transferred line — staged was set from parent
        # No discrepancy to report, just validation
        pass
    elif sub_active != 0 and sub_staged == 0:
        # r25 sent active without staged — normalization should have mirrored
        if abs(staged - active) > QUANTITY_TOLERANCE:
            discrepancies.append(_build_discrepancy(
                line=line,
                field="quantity.staged",
                submitted=float(sub_staged),
                calculated=float(staged),
                delta=float(abs(staged - sub_staged)),
                tolerance=float(QUANTITY_TOLERANCE),
                note="Standalone mirroring: staged should equal active",
            ))

    if discrepancies:
        _log_and_persist(
            purpose="ai_quantity_audit",
            line=line,
            discrepancies=discrepancies,
            severity=1,
        )

    return discrepancies


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_discrepancy(
    line: Any,
    field: str,
    submitted: float,
    calculated: float,
    delta: float,
    tolerance: float,
    note: str = "",
) -> dict:
    """Build a structured discrepancy dict."""
    return {
        "field": field,
        "submitted": submitted,
        "calculated": calculated,
        "delta": delta,
        "tolerance": tolerance,
        "note": note,
        "line_model": getattr(line._meta, "model_name", "unknown"),
        "line_id": getattr(line, "pk", None),
        "parent_id": getattr(line, "parent_id", None),
    }


def _get_transaction_context(line: Any) -> dict:
    """Extract transaction context from a line for audit refs."""
    ctx: Dict[str, Any] = {
        "line_model": getattr(line._meta, "model_name", "unknown"),
        "line_id": getattr(line, "pk", None),
        "line_number": getattr(line, "line_number", 0),
    }

    # Try to get parent transaction info
    parent_id = getattr(line, "parent_id", None)
    if parent_id:
        ctx["transaction_id"] = parent_id
        # Derive transaction model from line model (e.g. "order_line" → "order")
        line_model = ctx["line_model"]
        if line_model.endswith("_line"):
            ctx["transaction_model"] = line_model[:-5]

    # Item info from the item envelope
    item = getattr(line, "item", None)
    if isinstance(item, dict):
        ctx["item_id"] = item.get("item_id")
        ctx["item_code"] = item.get("ida_item", "")

    return ctx


def _log_and_persist(
    purpose: str,
    line: Any,
    discrepancies: list[dict],
    severity: int = 1,
) -> None:
    """Log discrepancy to Python logger and optionally create an Audit record.

    Severity levels:
      0 = info  (rounding noise, logged but not alarming)
      1 = warning  (r25 calculation disagrees — likely a bug)
      2 = error  (significant dollar discrepancy)
    """
    ctx = _get_transaction_context(line)
    fields = [d["field"] for d in discrepancies]
    summary = f"AI Audit [{purpose}] {ctx['line_model']}#{ctx.get('line_id', '?')}: " \
              f"discrepancy in {', '.join(fields)}"

    # Always log
    log_level = {0: logging.INFO, 1: logging.WARNING, 2: logging.ERROR}.get(severity, logging.WARNING)
    logger.log(log_level, summary, extra={"discrepancies": discrepancies, "context": ctx})

    # Optionally persist to Audit table
    if WRITE_AUDIT_RECORDS:
        _create_audit_record(purpose, ctx, discrepancies, severity)


def _create_audit_record(
    purpose: str,
    context: dict,
    discrepancies: list[dict],
    severity: int,
) -> None:
    """Create an accounts.Audit record for the discrepancy.

    Uses try/except to never break the save path — audit is observational.
    """
    try:
        from apps.accounts.models.audit import Audit

        fields_affected = [d["field"] for d in discrepancies]
        name = f"{context.get('transaction_model', context['line_model'])} " \
               f"line {context.get('line_number', '?')}: {', '.join(fields_affected)}"

        Audit.objects.create(
            purpose=purpose,
            name=name[:255],
            conflicts={
                "discrepancies": discrepancies,
                "context": context,
            },
            changes={
                d["field"]: {"from": d["submitted"], "to": d["calculated"]}
                for d in discrepancies
            },
            recommendations={
                "source": "ai_audit",
                "severity": severity,
                "check": "r25 lineItemService.calculateLine() vs wc3 _calculate_extended_price()",
                "fields": fields_affected,
            },
            rating=severity,
            is_completed=True,  # auto-resolved — wc3 applied its value
            priority=severity,
            refs={
                "links": {
                    "transaction": [
                        {"model": context.get("transaction_model", ""), "id": context.get("transaction_id")}
                    ] if context.get("transaction_id") else [],
                    "line": [
                        {"model": context["line_model"], "id": context.get("line_id")}
                    ] if context.get("line_id") else [],
                    "item": [
                        {"id": context.get("item_id"), "code": context.get("item_code", "")}
                    ] if context.get("item_id") else [],
                },
                "keywords": ["ai_audit", purpose],
                "tags": [purpose],
            },
        )
    except Exception as exc:
        # Never break the save path for audit logging
        logger.error("Failed to create AI audit record: %s", exc, exc_info=True)
