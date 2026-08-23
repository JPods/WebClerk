"""
Parade of Reports — Alice-driven onboarding tool.

Alice walks new users through their reports, rendering each with polished
sample data and collecting feedback. The parade is itself a Report record
(category='onboarding', model_name='report').

Usage:
    From Alice (via manage endpoint):
        POST /wcapi/manage/
        {"action": "start_parade", "params": {"report_ids": [1,2,3]}}

    The parade:
    1. Queries selected Report records (or all active if none specified)
    2. Groups them by business flow (Selling → Getting Paid → Buying → Catalog)
    3. For each report, builds the render URL with sample=true
    4. Returns the parade manifest — Alice drives Chrome DevTools through it

The parade does NOT drive Chrome itself — it produces the manifest.
Alice uses Chrome DevTools MCP tools (navigate_page, take_screenshot,
evaluate_script) to walk through the manifest and collect feedback.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.apps import apps as django_apps

logger = logging.getLogger(__name__)

SAMPLE_DATA_DIR = Path(__file__).resolve().parent.parent / "sample_data"

# Business flow grouping — reports parade in this order
PARADE_GROUPS = [
    {
        "name": "Selling",
        "description": "Documents you send to customers",
        "models": ["invoice", "order", "proposal", "workorder"],
        "report_patterns": [
            "invoice", "credit memo", "order confirmation",
            "packing slip", "pick", "bill of lading", "work order",
            "proposal", "quote", "estimate", "proforma",
        ],
    },
    {
        "name": "Getting Paid",
        "description": "Tracking money in",
        "models": ["payment", "statement"],
        "report_patterns": [
            "payment", "receipt", "remittance", "statement",
            "aging", "past due",
        ],
    },
    {
        "name": "Buying",
        "description": "Documents you send to vendors",
        "models": ["purchase", "requisition"],
        "report_patterns": [
            "purchase order", "receiving", "vendor", "requisition",
        ],
    },
    {
        "name": "Catalog & Contacts",
        "description": "Your products and people",
        "models": ["item", "contact"],
        "report_patterns": [
            "item", "price list", "inventory", "customer",
            "contact", "label", "mailing",
        ],
    },
    {
        "name": "Analysis",
        "description": "Reports that summarize activity",
        "models": [],
        "report_patterns": [
            "commission", "sales", "summary", "analysis",
            "margin", "activity", "history",
        ],
    },
]


def _has_sample_data(model_name: str, report_name: str = "") -> bool:
    """Check if polished sample data exists for this model or report."""
    if (SAMPLE_DATA_DIR / f"{model_name}.json").exists():
        return True
    # Check by report name slug (e.g., "aging" for "Aging Report")
    if report_name:
        slug = report_name.lower().replace(" ", "_")
        if (SAMPLE_DATA_DIR / f"{slug}.json").exists():
            return True
        # Partial match — "aging" in "aging_report"
        for f in SAMPLE_DATA_DIR.glob("*.json"):
            if not f.name.startswith("_") and f.stem in slug:
                return True
    return False


def _classify_report(report) -> str:
    """Assign a report to a parade group based on name and model."""
    name_lower = (report.name or "").lower()
    model_lower = (report.model_name or "").lower()

    for group in PARADE_GROUPS:
        # Match by model
        if model_lower in group["models"]:
            return group["name"]
        # Match by name pattern
        for pattern in group["report_patterns"]:
            if pattern in name_lower:
                return group["name"]

    return "Other"


def build_parade_manifest(
    report_ids: Optional[List[int]] = None,
    base_url: str = "http://localhost:8000",
) -> Dict[str, Any]:
    """
    Build the parade manifest — a structured list of reports grouped
    by business flow, each with a render URL using sample data.

    Parameters
    ----------
    report_ids : list of int, optional
        Specific Report record IDs to include. If None, includes all
        active print reports that have sample data available.
    base_url : str
        The server base URL for building render URLs.

    Returns
    -------
    dict with:
        groups : list of group dicts, each with:
            name, description, reports (list of report entries)
        total_reports : int
        sample_models : list of models with sample data
        feedback_options : list of feedback choices
    """
    Report = django_apps.get_model("core", "Report")

    qs = Report.objects.filter(
        is_active=True,
        is_deleted=False,
        output_type="print",
    ).order_by("model_name", "sort_order", "name")

    if report_ids:
        qs = qs.filter(id__in=report_ids)

    # Build grouped manifest
    groups: Dict[str, List[Dict]] = {}
    for report in qs:
        model = report.model_name or ""
        config = report.config or {}
        has_sample = bool(config.get("sample_data")) or _has_sample_data(model, report.name or "")

        group_name = _classify_report(report)

        entry = {
            "id": report.id,
            "name": report.name,
            "model_name": model,
            "category": report.category or "",
            "description": report.description or "",
            "has_sample_data": has_sample,
            "render_url": (
                f"{base_url}/wcapi/parade-preview/"
                f"?report_id={report.id}"
            ) if has_sample else None,
            "feedback": None,  # Alice fills this during parade
        }

        groups.setdefault(group_name, []).append(entry)

    # Order groups by PARADE_GROUPS sequence
    group_order = [g["name"] for g in PARADE_GROUPS] + ["Other"]
    ordered_groups = []
    for gname in group_order:
        if gname in groups:
            group_def = next(
                (g for g in PARADE_GROUPS if g["name"] == gname),
                {"name": gname, "description": ""},
            )
            ordered_groups.append({
                "name": gname,
                "description": group_def.get("description", ""),
                "reports": groups[gname],
                "count": len(groups[gname]),
            })

    # Available sample data models
    sample_models = [
        f.stem for f in SAMPLE_DATA_DIR.glob("*.json")
        if not f.name.startswith("_")
    ]

    return {
        "groups": ordered_groups,
        "total_reports": sum(g["count"] for g in ordered_groups),
        "sample_models": sample_models,
        "feedback_options": ["Keep", "Modify", "Don't Need"],
        "instructions": (
            "Alice navigates Chrome to each render_url. At each stop, "
            "the user chooses Keep / Modify / Don't Need and optionally "
            "adds notes. Feedback is saved to the Report record via wcapi."
        ),
    }


def save_parade_feedback(
    report_id: int,
    feedback: str,
    notes: str = "",
    user_id: Optional[int] = None,
) -> bool:
    """
    Save user feedback from the parade to the Report record.

    Stored in config.parade_feedback:
        decision: Keep | Modify | Don't Need
        notes: user's free-text notes
        user_id: who gave the feedback
        dt_feedback: when (UTC ISO)
    """
    from datetime import datetime, timezone

    Report = django_apps.get_model("core", "Report")
    report = Report.objects.filter(id=report_id).first()
    if not report:
        return False

    config = report.config or {}
    config["parade_feedback"] = {
        "decision": feedback,
        "notes": notes,
        "user_id": user_id,
        "dt_feedback": datetime.now(timezone.utc).isoformat(),
    }
    report.config = config
    report.save(update_fields=["config", "dt_modified"])
    return True
