from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Callable, Dict

from apps.core.services.tally_reports import (
    get_tally_inventory_usage_by_month,
    get_tally_inventory_yearly_summary,
    get_tally_sales_by_customer_month,
    get_tally_sales_by_customer_year,
    get_tally_sales_by_manufacturer_month,
    get_tally_summary_by_period,
)


RegistryEntry = Dict[str, Any]
ReportExecutor = Callable[[Dict[str, Any]], Dict[str, Any]]


_REPORT_EXECUTORS: dict[str, ReportExecutor] = {
    "tally_summary_by_period": get_tally_summary_by_period,
    "tally_sales_by_customer_month": get_tally_sales_by_customer_month,
    "tally_sales_by_manufacturer_month": get_tally_sales_by_manufacturer_month,
    "tally_sales_by_customer_year": get_tally_sales_by_customer_year,
    "tally_inventory_usage_by_month": get_tally_inventory_usage_by_month,
    "tally_inventory_yearly_summary": get_tally_inventory_yearly_summary,
}


_REPORT_REGISTRY: tuple[RegistryEntry, ...] = (
    {
        "report_key": "tally_summary_by_period",
        "action": "get_tally_summary_by_period",
        "label": "tally_summary_by_period",
        "description": "period totals across core transaction models",
        "default_params": {},
    },
    {
        "report_key": "tally_sales_by_customer_month",
        "action": "get_tally_sales_by_customer_month",
        "label": "tally_sales_by_customer_month",
        "description": "sales grouped by customer and month",
        "default_params": {},
    },
    {
        "report_key": "tally_sales_by_manufacturer_month",
        "action": "get_tally_sales_by_manufacturer_month",
        "label": "tally_sales_by_manufacturer_month",
        "description": "sales grouped by manufacturer and month",
        "default_params": {},
    },
    {
        "report_key": "tally_sales_by_customer_year",
        "action": "get_tally_sales_by_customer_year",
        "label": "tally_sales_by_customer_year",
        "description": "year-over-year sales grouped by customer and year",
        "default_params": {},
    },
    {
        "report_key": "tally_inventory_usage_by_month",
        "action": "get_tally_inventory_usage_by_month",
        "label": "tally_inventory_usage_by_month",
        "description": "inventory movement grouped by item and month",
        "default_params": {},
    },
    {
        "report_key": "tally_inventory_yearly_summary",
        "action": "get_tally_inventory_yearly_summary",
        "label": "tally_inventory_yearly_summary",
        "description": "yearly inventory usage summary and valuation metrics",
        "default_params": {},
    },
)


def list_tally_reports() -> Dict[str, Any]:
    return {
        "reports": list(_REPORT_REGISTRY),
        "count": len(_REPORT_REGISTRY),
    }


def _get_executor(report_key: str) -> ReportExecutor:
    executor = _REPORT_EXECUTORS.get(report_key)
    if executor is None:
        raise ValueError(f"Unknown report_key: {report_key}")
    return executor


def execute_tally_report(params: Dict[str, Any]) -> Dict[str, Any]:
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


def export_tally_report(params: Dict[str, Any]) -> Dict[str, Any]:
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
