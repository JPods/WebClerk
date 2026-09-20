"""The report registry — Report records, and the executors behind the ones that run.

A report is a record (apps/core/models/report.py), one per report per model.
Most are templates: the record carries the layout and the content. Some
execute — the record names an action in config.action, and the table below
maps that name to the function that runs it.

What makes a report executable is the action on its record, not the category
it is filed under. ("Tally" was WC2's word for this class of report. There is
no Tally model here, so there is no tally category: an executable is a report.)

An installation with no reports has not failed — it has not been given them
yet. See apps/core/services/installation_init.py.
"""
from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict

from apps.core.services.report_executors import (
    get_inventory_usage_by_month,
    get_inventory_yearly_summary,
    get_sales_by_customer_month,
    get_sales_by_customer_year,
    get_sales_by_manufacturer_month,
    get_summary_by_period,
)


# Why a report record exists (BaseModel.purpose).
REPORT_PURPOSE_EXECUTABLE = "report_executable"
REPORT_PURPOSE_SEARCH = "search_stored"

RegistryEntry = Dict[str, Any]
ReportExecutor = Callable[[Dict[str, Any]], Dict[str, Any]]


EXECUTORS: dict[str, ReportExecutor] = {
    "summary_by_period": get_summary_by_period,
    "sales_by_customer_month": get_sales_by_customer_month,
    "sales_by_manufacturer_month": get_sales_by_manufacturer_month,
    "sales_by_customer_year": get_sales_by_customer_year,
    "inventory_usage_by_month": get_inventory_usage_by_month,
    "inventory_yearly_summary": get_inventory_yearly_summary,
}

# The manage actions that run a report — used to decide what Alice observes.
EXECUTOR_ACTIONS = frozenset(f"get_{key}" for key in EXECUTORS)


# This release's shipped executable reports. These are seeded into Report
# records, which is what the installation actually reads and what WC_HQ
# distributes in the recommended set. The tuple is the seed of last resort —
# when HQ is unreachable and the shipped bundle carries none.
SHIPPED_REPORTS: tuple[RegistryEntry, ...] = (
    {
        "report_key": "summary_by_period",
        "action": "get_summary_by_period",
        "label": "summary_by_period",
        "description": "period totals across core transaction models",
        "default_params": {},
    },
    {
        "report_key": "sales_by_customer_month",
        "action": "get_sales_by_customer_month",
        "label": "sales_by_customer_month",
        "description": "sales grouped by customer and month",
        "default_params": {},
    },
    {
        "report_key": "sales_by_manufacturer_month",
        "action": "get_sales_by_manufacturer_month",
        "label": "sales_by_manufacturer_month",
        "description": "sales grouped by manufacturer and month",
        "default_params": {},
    },
    {
        "report_key": "sales_by_customer_year",
        "action": "get_sales_by_customer_year",
        "label": "sales_by_customer_year",
        "description": "year-over-year sales grouped by customer and year",
        "default_params": {},
    },
    {
        "report_key": "inventory_usage_by_month",
        "action": "get_inventory_usage_by_month",
        "label": "inventory_usage_by_month",
        "description": "inventory movement grouped by item and month",
        "default_params": {},
    },
    {
        "report_key": "inventory_yearly_summary",
        "action": "get_inventory_yearly_summary",
        "label": "inventory_yearly_summary",
        "description": "yearly inventory usage summary and valuation metrics",
        "default_params": {},
    },
)


# Stable across every installation and WC_HQ, so the same report is the same
# record everywhere and the bundle's uuid-keyed merge lands on it.
REPORT_UUID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://www.webclerk.com/reports/")


def report_uuid(report_key: str) -> uuid.UUID:
    return uuid.uuid5(REPORT_UUID_NAMESPACE, report_key)


def _entry_from_report(report) -> RegistryEntry | None:
    """A registry entry from a Report record. config carries the registry fields."""
    config = report.config if isinstance(report.config, dict) else {}
    report_key = (config.get("report_key") or report.ida or "").strip()
    if not report_key:
        return None
    return {
        "report_key": report_key,
        "action": config.get("action") or f"get_{report_key}",
        "label": report.name or report_key,
        "description": report.description or "",
        "default_params": config.get("default_params") or {},
    }


def _reports_from_records(*, purpose: str | None = None,
                          executable: bool = False) -> list[RegistryEntry]:
    """Registry entries for Report records — all of them, or a narrowed set."""
    from django.apps import apps as dj_apps

    try:
        Report = dj_apps.get_model("core", "Report")
    except LookupError:
        return []
    rows = Report.objects.filter(is_active=True)
    if purpose:
        rows = rows.filter(purpose=purpose)
    rows = rows.order_by("category", "sort_order", "name")
    entries = [e for e in (_entry_from_report(r) for r in rows) if e]
    if executable:
        entries = [e for e in entries if e["report_key"] in EXECUTORS]
    return entries


def list_reports(*, purpose: str | None = None) -> Dict[str, Any]:
    """The reports this installation has, optionally of one purpose."""
    reports = _reports_from_records(purpose=purpose)
    return {"reports": reports, "count": len(reports)}


def seed_shipped_reports() -> list[RegistryEntry]:
    """Write this release's executable reports as Report records. Never overwrites."""
    from django.apps import apps as dj_apps

    try:
        Report = dj_apps.get_model("core", "Report")
    except LookupError:
        return list(SHIPPED_REPORTS)

    for order, entry in enumerate(SHIPPED_REPORTS):
        report_key = entry["report_key"]
        uuid_val = report_uuid(report_key)
        if Report.objects.filter(uuid=uuid_val).exists():
            continue
        Report.objects.create(
            uuid=uuid_val,
            ida=report_key,
            name=entry["label"],
            description=entry["description"],
            category="report",
            purpose=REPORT_PURPOSE_EXECUTABLE,
            output_type="json",
            model_name="report",
            sort_order=order,
            config={
                "report_key": report_key,
                "action": entry["action"],
                "default_params": entry.get("default_params") or {},
            },
            metadata={"foundational": True, "source": "shipped"},
        )
    return _reports_from_records(executable=True)


def list_executable_reports() -> Dict[str, Any]:
    """The tally reports this installation has.

    An installation with none has not been given them yet. Ask WC_HQ for the
    reports bundle; if that cannot be reached, seed this release's own. Either
    way the caller gets a list, not a failure.
    """
    reports = _reports_from_records("tally")

    if not reports:
        from apps.core.services.installation_init import ensure_defined

        if ensure_defined("tally_reports"):
            reports = _reports_from_records("tally")

    if not reports:
        reports = seed_shipped_tally_reports()

    return {
        "reports": reports,
        "count": len(reports),
    }


def _get_executor(report_key: str) -> ReportExecutor:
    executor = EXECUTORS.get(report_key)
    if executor is None:
        raise ValueError(f"Unknown report_key: {report_key}")
    return executor


def execute_report(params: Dict[str, Any]) -> Dict[str, Any]:
    report_key = str(params.get("report_key") or "").strip()
    if not report_key:
        raise ValueError("report_key is required")

    report_params = params.get("report_params")
    if report_params is None:
        report_params = {}
    if not isinstance(report_params, dict):
        raise ValueError("report_params must be an object")

    executor = _get_executor(report_key)
    result = executor(report_params)

    return {
        "report_key": report_key,
        "report_params": report_params,
        "result": result,
    }


def _rows_to_csv(rows: list[dict[str, Any]], columns: list[str] | None = None) -> str:
    if not rows:
        selected_columns = columns or []
    else:
        if columns:
            selected_columns = columns
        else:
            ordered_keys: list[str] = []
            seen: set[str] = set()
            for row in rows:
                for key in row.keys():
                    if key not in seen:
                        seen.add(key)
                        ordered_keys.append(key)
            selected_columns = ordered_keys

    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=selected_columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        flat_row = {}
        for key in selected_columns:
            value = row.get(key)
            if isinstance(value, (dict, list)):
                flat_row[key] = json.dumps(value, separators=(",", ":"))
            else:
                flat_row[key] = value
        writer.writerow(flat_row)
    return out.getvalue()


def export_report(params: Dict[str, Any]) -> Dict[str, Any]:
    report_key = str(params.get("report_key") or "").strip()
    if not report_key:
        raise ValueError("report_key is required")

    export_format = str(params.get("format") or "csv").strip().lower()
    if export_format not in {"csv", "json"}:
        raise ValueError("format must be 'csv' or 'json'")

    report_params = params.get("report_params")
    if report_params is None:
        report_params = {}
    if not isinstance(report_params, dict):
        raise ValueError("report_params must be an object")

    columns = params.get("columns")
    if columns is not None and not isinstance(columns, list):
        raise ValueError("columns must be a list when provided")

    result = _get_executor(report_key)(report_params)
    rows = result.get("rows") if isinstance(result, dict) else []
    if not isinstance(rows, list):
        rows = []

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if export_format == "json":
        content = json.dumps(result, indent=2, sort_keys=False)
        filename = f"{report_key}_{stamp}.json"
    else:
        csv_rows = [r for r in rows if isinstance(r, dict)]
        safe_columns = [str(c) for c in columns] if isinstance(columns, list) else None
        content = _rows_to_csv(csv_rows, columns=safe_columns)
        filename = f"{report_key}_{stamp}.csv"

    return {
        "report_key": report_key,
        "format": export_format,
        "filename": filename,
        "row_count": len(rows),
        "content": content,
    }
