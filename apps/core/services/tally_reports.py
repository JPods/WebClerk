from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, Optional

from django.apps import apps as dj_apps
from django.utils.dateparse import parse_date


@dataclass(frozen=True)
class SummaryModelSpec:
    app_label: str
    model_name: str
    key: str
    label: str


SUMMARY_MODEL_SPECS: tuple[SummaryModelSpec, ...] = (
    SummaryModelSpec("transactions", "Invoice", "invoice", "Invoices"),
    SummaryModelSpec("transactions", "Order", "order", "Orders"),
    SummaryModelSpec("transactions", "Proposal", "proposal", "Proposals"),
    SummaryModelSpec("transactions", "Purchase", "purchase", "Purchases"),
    SummaryModelSpec("transactions", "Payment", "payment", "Payments"),
    SummaryModelSpec("transactions", "Workorder", "workorder", "Work Orders"),
)


def _as_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def _resolve_period(params: Dict[str, Any]) -> tuple[date, date]:
    start_raw = params.get("start_date")
    end_raw = params.get("end_date")

    if start_raw:
        start_date = parse_date(str(start_raw))
        if start_date is None:
            raise ValueError(f"Invalid start_date: {start_raw}")
    else:
        today = date.today()
        start_date = today.replace(day=1)

    if end_raw:
        end_date = parse_date(str(end_raw))
        if end_date is None:
            raise ValueError(f"Invalid end_date: {end_raw}")
    else:
        end_date = date.today()

    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")

    return start_date, end_date


def _iter_totals(rows: Iterable[tuple[Optional[dict], Any]]) -> Decimal:
    total = Decimal("0")
    for totals_json, scalar_total in rows:
        if isinstance(totals_json, dict):
            total += _as_decimal(totals_json.get("total"))
        else:
            total += _as_decimal(scalar_total)
    return total


def get_tally_summary_by_period(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return a period summary across core transaction families.

    Parameters:
        start_date (optional): ISO date; defaults to first day of current month
        end_date (optional): ISO date; defaults to today
    """

    start_date, end_date = _resolve_period(params)
    rows: list[Dict[str, Any]] = []
    missing_models: list[str] = []

    grand_count = 0
    grand_total = Decimal("0")

    for spec in SUMMARY_MODEL_SPECS:
        try:
            Model = dj_apps.get_model(spec.app_label, spec.model_name)
        except LookupError:
            missing_models.append(f"{spec.app_label}.{spec.model_name}")
            continue

        qs = Model.objects.all()

        field_names = {f.name for f in Model._meta.get_fields()}
        if "is_deleted" in field_names:
            qs = qs.filter(is_deleted=False)
        if "is_archived" in field_names:
            qs = qs.filter(is_archived=False)

        if "dt_created" in field_names:
            dt_field = Model._meta.get_field("dt_created")
            internal_type = dt_field.get_internal_type()

            if internal_type in {"DateField", "DateTimeField"}:
                qs = qs.filter(
                    dt_created__date__gte=start_date,
                    dt_created__date__lte=end_date,
                )
            else:
                # wc3 BaseModel commonly stores dt_created as epoch milliseconds.
                start_ms = int(
                    datetime.combine(start_date, time.min, tzinfo=timezone.utc).timestamp() * 1000
                )
                end_ms = int(
                    datetime.combine(end_date, time.max, tzinfo=timezone.utc).timestamp() * 1000
                )
                qs = qs.filter(dt_created__gte=start_ms, dt_created__lte=end_ms)
        elif "created_at" in field_names:
            qs = qs.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
        else:
            # If no date field exists we cannot place records in a period safely.
            continue

        if "totals" in field_names or "total" in field_names:
            totals_rows = qs.values_list("totals", "total")
            model_total = _iter_totals(totals_rows)
        else:
            model_total = Decimal("0")

        model_count = qs.count()
        grand_count += model_count
        grand_total += model_total

        rows.append(
            {
                "model_name": spec.key,
                "label": spec.label,
                "count": model_count,
                "total": float(model_total),
            }
        )

    rows.sort(key=lambda r: r["total"], reverse=True)

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "rows": rows,
        "totals": {
            "count": grand_count,
            "total": float(grand_total),
        },
        "missing_models": missing_models,
    }


def _month_key_from_ms(epoch_ms: int | None) -> str:
    if not epoch_ms:
        return "unknown"
    try:
        dt = datetime.fromtimestamp(int(epoch_ms) / 1000, tz=timezone.utc)
    except Exception:
        return "unknown"
    return f"{dt.year:04d}-{dt.month:02d}"


def _sales_by_dimension_month(params: Dict[str, Any], *, dimension_field: str) -> Dict[str, Any]:
    start_date, end_date = _resolve_period(params)

    Invoice = dj_apps.get_model("transactions", "Invoice")
    OrgBase = dj_apps.get_model("orgs", "OrgBase")

    start_ms = int(datetime.combine(start_date, time.min, tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.combine(end_date, time.max, tzinfo=timezone.utc).timestamp() * 1000)

    qs = Invoice.objects.filter(dt_created__gte=start_ms, dt_created__lte=end_ms)
    field_names = {f.name for f in Invoice._meta.get_fields()}
    if "is_deleted" in field_names:
        qs = qs.filter(is_deleted=False)
    if "is_archived" in field_names:
        qs = qs.filter(is_archived=False)

    value_fields = [dimension_field, "dt_created", "totals", "total"]
    grouped: dict[tuple[int, str], dict[str, Any]] = {}
    org_ids: set[int] = set()

    for dim_id, dt_created, totals_json, scalar_total in qs.values_list(*value_fields):
        dim_pk = int(dim_id or 0)
        if dim_pk <= 0:
            continue

        month = _month_key_from_ms(dt_created)
        amount = _as_decimal(totals_json.get("total") if isinstance(totals_json, dict) else scalar_total)

        key = (dim_pk, month)
        entry = grouped.get(key)
        if entry is None:
            entry = {
                "dimension_id": dim_pk,
                "month": month,
                "count": 0,
                "total": Decimal("0"),
            }
            grouped[key] = entry
        entry["count"] += 1
        entry["total"] += amount
        org_ids.add(dim_pk)

    names: dict[int, str] = {}
    if org_ids:
        for org in OrgBase.objects.filter(id__in=org_ids).values("id", "display_name"):
            names[int(org["id"])] = org.get("display_name") or f"Org #{org['id']}"

    rows: list[dict[str, Any]] = []
    grand_count = 0
    grand_total = Decimal("0")
    for (dim_pk, month), entry in grouped.items():
        total = entry["total"]
        count = entry["count"]
        grand_total += total
        grand_count += count
        rows.append(
            {
                "dimension_id": dim_pk,
                "dimension_name": names.get(dim_pk, f"Org #{dim_pk}"),
                "month": month,
                "count": count,
                "total": float(total),
            }
        )

    rows.sort(key=lambda r: (r["month"], r["total"]), reverse=True)

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "rows": rows,
        "totals": {
            "count": grand_count,
            "total": float(grand_total),
        },
    }


def get_tally_sales_by_customer_month(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return invoice sales grouped by customer and month."""
    return _sales_by_dimension_month(params, dimension_field="customer_id")


def get_tally_sales_by_manufacturer_month(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return invoice sales grouped by manufacturer and month."""
    return _sales_by_dimension_month(params, dimension_field="manufacturer_id")


def get_tally_sales_by_customer_year(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return invoice sales grouped by customer and year with year-over-year deltas."""
    start_date, end_date = _resolve_period(params)

    Invoice = dj_apps.get_model("transactions", "Invoice")
    OrgBase = dj_apps.get_model("orgs", "OrgBase")

    start_ms = int(datetime.combine(start_date, time.min, tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.combine(end_date, time.max, tzinfo=timezone.utc).timestamp() * 1000)

    qs = Invoice.objects.filter(dt_created__gte=start_ms, dt_created__lte=end_ms)
    field_names = {f.name for f in Invoice._meta.get_fields()}
    if "is_deleted" in field_names:
        qs = qs.filter(is_deleted=False)
    if "is_archived" in field_names:
        qs = qs.filter(is_archived=False)

    grouped: dict[tuple[int, int], dict[str, Any]] = {}
    org_ids: set[int] = set()

    for customer_id, dt_created, totals_json, scalar_total in qs.values_list("customer_id", "dt_created", "totals", "total"):
        dim_pk = int(customer_id or 0)
        if dim_pk <= 0:
            continue
        try:
            year = datetime.fromtimestamp(int(dt_created) / 1000, tz=timezone.utc).year
        except Exception:
            continue

        amount = _as_decimal(totals_json.get("total") if isinstance(totals_json, dict) else scalar_total)
        key = (dim_pk, year)
        entry = grouped.get(key)
        if entry is None:
            entry = {
                "dimension_id": dim_pk,
                "year": year,
                "count": 0,
                "total": Decimal("0"),
            }
            grouped[key] = entry
        entry["count"] += 1
        entry["total"] += amount
        org_ids.add(dim_pk)

    names: dict[int, str] = {}
    if org_ids:
        for org in OrgBase.objects.filter(id__in=org_ids).values("id", "display_name"):
            names[int(org["id"])] = org.get("display_name") or f"Org #{org['id']}"

    yearly_totals: dict[int, dict[int, Decimal]] = {}
    for (dim_pk, year), entry in grouped.items():
        yearly_totals.setdefault(dim_pk, {})[year] = entry["total"]

    rows: list[dict[str, Any]] = []
    grand_count = 0
    grand_total = Decimal("0")
    for (dim_pk, year), entry in grouped.items():
        total = entry["total"]
        previous_total = yearly_totals.get(dim_pk, {}).get(year - 1, Decimal("0"))
        delta = total - previous_total
        delta_percent = float((delta / previous_total) * 100) if previous_total != Decimal("0") else None
        count = entry["count"]
        grand_count += count
        grand_total += total
        rows.append(
            {
                "dimension_id": dim_pk,
                "dimension_name": names.get(dim_pk, f"Org #{dim_pk}"),
                "year": year,
                "count": count,
                "total": float(total),
                "previous_total": float(previous_total),
                "delta": float(delta),
                "delta_percent": delta_percent,
            }
        )

    rows.sort(key=lambda r: (r["year"], r["total"]), reverse=True)

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "rows": rows,
        "totals": {
            "count": grand_count,
            "total": float(grand_total),
        },
    }


def _resolve_inventory_unit_cost(movement) -> Decimal:
    layer = getattr(movement, "inventory_layer", None)
    if layer is not None:
        layer_cost = getattr(layer, "cost", {}) or {}
        for key in ("landed", "moving_avg", "unit_po", "fifo_snapshot", "lifo_snapshot"):
            value = layer_cost.get(key)
            cost = _as_decimal(value)
            if cost != Decimal("0"):
                return cost

    item = getattr(movement, "item", None)
    if item is not None:
        item_cost = getattr(item, "cost", {}) or {}
        for key in ("landed", "avg", "last", "standard"):
            value = item_cost.get(key)
            cost = _as_decimal(value)
            if cost != Decimal("0"):
                return cost

    return Decimal("0")


def _inventory_period_bounds(params: Dict[str, Any]) -> tuple[date, date, int, int]:
    start_date, end_date = _resolve_period(params)
    start_ms = int(datetime.combine(start_date, time.min, tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.combine(end_date, time.max, tzinfo=timezone.utc).timestamp() * 1000)
    return start_date, end_date, start_ms, end_ms


def get_tally_inventory_usage_by_month(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return inventory movement usage grouped by item and month."""
    start_date, end_date, start_ms, end_ms = _inventory_period_bounds(params)

    InventoryMovement = dj_apps.get_model("products", "InventoryMovement")
    Item = dj_apps.get_model("products", "Item")

    qs = (
        InventoryMovement.objects
        .select_related("item", "inventory_layer")
        .filter(dt_created__gte=start_ms, dt_created__lte=end_ms)
    )

    grouped: dict[tuple[int, str], dict[str, Any]] = {}
    item_ids: set[int] = set()

    for movement in qs:
        item_id = getattr(movement, "item_id", 0) or 0
        if item_id <= 0:
            continue

        month = _month_key_from_ms(getattr(movement, "dt_created", 0))
        key = (int(item_id), month)
        row = grouped.get(key)
        if row is None:
            row = {
                "item_id": int(item_id),
                "month": month,
                "receipt_qty": Decimal("0"),
                "issue_qty": Decimal("0"),
                "adjust_qty": Decimal("0"),
                "receipt_value": Decimal("0"),
                "issue_value": Decimal("0"),
                "adjust_value": Decimal("0"),
                "count": 0,
            }
            grouped[key] = row

        qty = _as_decimal(getattr(movement, "quantity", 0))
        unit_cost = _resolve_inventory_unit_cost(movement)
        movement_value = qty * unit_cost
        movement_type = getattr(movement, "movement_type", "") or ""

        row["count"] += 1
        if movement_type == "receipt":
            row["receipt_qty"] += qty
            row["receipt_value"] += movement_value
        elif movement_type == "issue":
            row["issue_qty"] += qty
            row["issue_value"] += movement_value
        else:
            row["adjust_qty"] += qty
            row["adjust_value"] += movement_value
        item_ids.add(int(item_id))

    item_names: dict[int, str] = {}
    if item_ids:
        for item in Item.objects.filter(id__in=item_ids).values("id", "name", "sku"):
            label = item.get("name") or item.get("sku") or f"Item #{item['id']}"
            item_names[int(item["id"])] = label

    rows: list[dict[str, Any]] = []
    totals = {
        "count": 0,
        "receipt_qty": Decimal("0"),
        "issue_qty": Decimal("0"),
        "adjust_qty": Decimal("0"),
        "net_qty": Decimal("0"),
        "receipt_value": Decimal("0"),
        "issue_value": Decimal("0"),
        "adjust_value": Decimal("0"),
        "net_value": Decimal("0"),
    }

    for (item_id, month), row in grouped.items():
        net_qty = row["receipt_qty"] - row["issue_qty"] + row["adjust_qty"]
        net_value = row["receipt_value"] - row["issue_value"] + row["adjust_value"]
        rows.append(
            {
                "item_id": item_id,
                "item_name": item_names.get(item_id, f"Item #{item_id}"),
                "month": month,
                "count": row["count"],
                "receipt_qty": float(row["receipt_qty"]),
                "issue_qty": float(row["issue_qty"]),
                "adjust_qty": float(row["adjust_qty"]),
                "net_qty": float(net_qty),
                "receipt_value": float(row["receipt_value"]),
                "issue_value": float(row["issue_value"]),
                "adjust_value": float(row["adjust_value"]),
                "net_value": float(net_value),
            }
        )
        totals["count"] += row["count"]
        totals["receipt_qty"] += row["receipt_qty"]
        totals["issue_qty"] += row["issue_qty"]
        totals["adjust_qty"] += row["adjust_qty"]
        totals["net_qty"] += net_qty
        totals["receipt_value"] += row["receipt_value"]
        totals["issue_value"] += row["issue_value"]
        totals["adjust_value"] += row["adjust_value"]
        totals["net_value"] += net_value

    rows.sort(key=lambda r: (r["month"], r["net_value"]), reverse=True)

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "rows": rows,
        "totals": {k: float(v) if isinstance(v, Decimal) else v for k, v in totals.items()},
    }


def get_tally_inventory_yearly_summary(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return yearly inventory usage and valuation summary grouped by item/year."""
    start_date, end_date, start_ms, end_ms = _inventory_period_bounds(params)

    InventoryMovement = dj_apps.get_model("products", "InventoryMovement")
    Item = dj_apps.get_model("products", "Item")

    qs = (
        InventoryMovement.objects
        .select_related("item", "inventory_layer")
        .filter(dt_created__gte=start_ms, dt_created__lte=end_ms)
    )

    grouped: dict[tuple[int, int], dict[str, Any]] = {}
    item_ids: set[int] = set()

    for movement in qs:
        item_id = getattr(movement, "item_id", 0) or 0
        if item_id <= 0:
            continue
        try:
            year = datetime.fromtimestamp(int(getattr(movement, "dt_created", 0)) / 1000, tz=timezone.utc).year
        except Exception:
            continue

        key = (int(item_id), int(year))
        row = grouped.get(key)
        if row is None:
            row = {
                "item_id": int(item_id),
                "year": int(year),
                "receipt_qty": Decimal("0"),
                "issue_qty": Decimal("0"),
                "adjust_qty": Decimal("0"),
                "receipt_value": Decimal("0"),
                "issue_value": Decimal("0"),
                "adjust_value": Decimal("0"),
                "count": 0,
            }
            grouped[key] = row

        qty = _as_decimal(getattr(movement, "quantity", 0))
        movement_value = qty * _resolve_inventory_unit_cost(movement)
        movement_type = getattr(movement, "movement_type", "") or ""

        row["count"] += 1
        if movement_type == "receipt":
            row["receipt_qty"] += qty
            row["receipt_value"] += movement_value
        elif movement_type == "issue":
            row["issue_qty"] += qty
            row["issue_value"] += movement_value
        else:
            row["adjust_qty"] += qty
            row["adjust_value"] += movement_value
        item_ids.add(int(item_id))

    item_names: dict[int, str] = {}
    if item_ids:
        for item in Item.objects.filter(id__in=item_ids).values("id", "name", "sku"):
            label = item.get("name") or item.get("sku") or f"Item #{item['id']}"
            item_names[int(item["id"])] = label

    rows: list[dict[str, Any]] = []
    grand_count = 0
    grand_value = Decimal("0")
    for (item_id, year), row in grouped.items():
        net_qty = row["receipt_qty"] - row["issue_qty"] + row["adjust_qty"]
        net_value = row["receipt_value"] - row["issue_value"] + row["adjust_value"]
        usage_value = row["issue_value"]
        rows.append(
            {
                "item_id": item_id,
                "item_name": item_names.get(item_id, f"Item #{item_id}"),
                "year": year,
                "count": row["count"],
                "usage_qty": float(row["issue_qty"]),
                "usage_value": float(usage_value),
                "receipt_qty": float(row["receipt_qty"]),
                "adjust_qty": float(row["adjust_qty"]),
                "net_qty": float(net_qty),
                "net_value": float(net_value),
            }
        )
        grand_count += row["count"]
        grand_value += net_value

    rows.sort(key=lambda r: (r["year"], r["usage_value"]), reverse=True)

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "rows": rows,
        "totals": {
            "count": grand_count,
            "net_value": float(grand_value),
        },
    }
