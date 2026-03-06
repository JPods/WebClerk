"""
5H. Layout ↔ Schema Drift Detection.

Compares Django model field definitions against actual field references
in React2025 page components (Detail forms, List columns, Display views)
to detect UI-level mismatches — fields referenced in layouts that don't
exist in the model, or model fields missing from all layouts.

This complements SchemaDriftDetector (5D) which checks TypeScript
*type definitions*. This checks the *rendered UI components*.

Usage:
    from apps.ai_assistant.services.layout_drift_detector import LayoutDriftDetector

    detector = LayoutDriftDetector()
    report = detector.detect_all()              # full scan
    report = detector.detect_model('item')      # single model
    print(detector.format_report(report))
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from django.apps import apps
from django.conf import settings

logger = logging.getLogger(__name__)


# ── R25 project root (sibling of webClerk3) ────────────────────────────────
R25_ROOT = Path(settings.BASE_DIR).parent / "React2025"


# ── Regex patterns for extracting field references from page components ────
# Each tuple: (compiled regex, group index for field name, pattern label)
FIELD_PATTERNS: list[tuple[re.Pattern, int, str]] = [
    # react-hook-form register("field_name")
    (re.compile(r'register\(\s*"([^"]+)"'), 1, "register"),
    # react-hook-form Controller name="field_name"
    (re.compile(r'<Controller\s+name="([^"]+)"'), 1, "Controller"),
    (re.compile(r'Controller\s*\n?\s*name="([^"]+)"'), 1, "Controller"),
    # useWatch name="field_name"
    (re.compile(r'useWatch\([^)]*name:\s*"([^"]+)"'), 1, "useWatch"),
    # ScalarCard label entries: { label: "field_name", value: ... }
    (re.compile(r'\{\s*label:\s*"([^"]+)"'), 1, "ScalarCard"),
    # JsonCard fieldName="field_name"
    (re.compile(r'fieldName="([^"]+)"'), 1, "JsonCard"),
    # handleFieldChange("field_name", ...) — Display pages
    (re.compile(r'handleFieldChange\(\s*"([^"]+)"'), 1, "handleFieldChange"),
    # OrgLinkPanel / CommLinkPanel fieldName: "field_id"
    (re.compile(r'fieldName:\s*"([^"]+)"'), 1, "LinkPanel"),
    # DETAIL_FIELDS constant arrays
    (re.compile(r'"([^"]+)"'), 1, "DETAIL_FIELDS"),  # used only within FIELDS blocks
]

# Patterns specifically for list page columns
LIST_PATTERNS: list[tuple[re.Pattern, int, str]] = [
    # selector: (row) => row.field
    (re.compile(r'selector:\s*\([^)]*\)\s*=>\s*\(?(?:row)\.(\w+)'), 1, "selector"),
    # cell: (row) => row.field
    (re.compile(r'cell:\s*\([^)]*\)\s*=>\s*\(?(?:row)\.(\w+)'), 1, "cell"),
    # valueFrom(row, ["field1", "field2", ...]) — extract all candidates
    (re.compile(r'valueFrom\(\s*row\s*,\s*\[(.*?)\]'), 1, "valueFrom"),
    # row?.field?.subfield dot-chain access
    (re.compile(r'row\?\.(\w+)'), 1, "optional_chain"),
]

# Fields rendered by BaseModelCards (always present — skip checking these)
BASE_MODEL_CARD_FIELDS = frozenset({
    "id", "uuid", "ida", "dt_created", "dt_modified", "version",
    "is_active", "security_level", "is_deleted", "is_archived",
    "health_rating", "metadata", "refs", "prefs", "comments",
})

# Fields that exist in Django models but are internal / not expected in layouts
INTERNAL_FIELDS = frozenset({
    "created_by_id", "modified_by_id", "keywords_pending", "row_version",
    "password", "last_login", "is_superuser", "groups", "user_permissions",
    "actions",  # rendered via dedicated panel, not form fields
})

# Known JSON sub-field prefixes that map to parent JSONField names
# e.g., register("price_base") maps to the "price" JSONField
JSON_FIELD_PREFIXES: dict[str, list[str]] = {
    "price": ["price_base", "price_retail", "price_distributor", "price_wholesale",
              "price_dealer", "price_list", "price_sale", "price_level"],
    "cost": ["cost_standard", "cost_average", "cost_last", "cost_lowest",
             "cost_highest", "cost_replacement"],
    "tax_code": ["tax_code_purchase", "tax_code_sales", "tax_code_exempt",
                 "tax_code_shipping", "tax_code_duty"],
    "catalog": ["catalog_sku", "catalog_barcode", "catalog_upc",
                "catalog_isbn", "catalog_mpn", "catalog_ean"],
    "financial": ["financial_credit_limit", "financial_balance",
                  "financial_terms", "financial_discount"],
    "quantity": ["quantity_on_hand", "quantity_committed", "quantity_available",
                 "quantity_on_order", "quantity_reorder_point",
                 "quantity_reorder_qty", "quantity_min", "quantity_max"],
    "flags": ["flags_taxable", "flags_discountable", "flags_serialized",
              "flags_lotted", "flags_perishable", "flags_hazardous"],
    "connections": ["connections_website", "connections_portal"],
    "data": ["data_notes", "data_internal_notes"],
    "gl_accounts": ["gl_accounts_revenue", "gl_accounts_expense",
                    "gl_accounts_asset", "gl_accounts_cogs"],
    "metrics": ["metrics_ytd_sales", "metrics_ytd_purchases",
                "metrics_lifetime_sales"],
    "relations": ["relations_parent_id", "relations_default_warehouse"],
}


class LayoutDriftDetector:
    """Compare Django model fields against R25 layout page field references."""

    def __init__(self, r25_root: Path | None = None, use_llm: bool = False):
        self.r25_root = r25_root or R25_ROOT
        self.use_llm = use_llm
        self._client = None

    def _get_client(self):
        if self._client is None and self.use_llm:
            from apps.ai_assistant.services.ollama_client import OllamaClient
            self._client = OllamaClient()
        return self._client

    # ── Introspect Django models ───────────────────────────────────────

    def _get_django_fields(self, model_name: str) -> dict[str, dict[str, Any]] | None:
        """Get all fields for a Django model as {name: {type, required, ...}}.

        Returns field names using the DB column convention (FK → field_id).
        """
        from common.models import BaseModel

        model_cls = None
        for m in apps.get_models():
            if m.__name__.lower() == model_name.lower() and issubclass(m, BaseModel):
                model_cls = m
                break

        if model_cls is None:
            return None

        fields: dict[str, dict[str, Any]] = {}
        json_fields: set[str] = set()

        for f in model_cls._meta.get_fields():
            if not hasattr(f, "get_internal_type"):
                continue
            internal_type = f.get_internal_type()
            is_fk = internal_type in ("ForeignKey", "OneToOneField")
            db_name = f"{f.name}_id" if is_fk else f.name
            is_json = internal_type == "JSONField"

            if is_json:
                json_fields.add(f.name)

            fields[db_name] = {
                "django_type": internal_type,
                "required": not getattr(f, "blank", True) and not f.has_default(),
                "is_json": is_json,
                "is_fk": is_fk,
            }

        return fields

    def _get_json_field_names(self, model_name: str) -> set[str]:
        """Return the set of JSONField names for a model."""
        fields = self._get_django_fields(model_name)
        if not fields:
            return set()
        return {name for name, info in fields.items() if info.get("is_json")}

    # ── Discover R25 page files ────────────────────────────────────────

    def _find_page_files(self, model_name: str) -> dict[str, list[Path]]:
        """Find Detail, List, Display page files for a model.

        Returns dict with keys 'detail', 'list', 'display' mapping to file paths.
        Excludes files prefixed with 'qqq_' (legacy/deprecated).
        """
        pages: dict[str, list[Path]] = {"detail": [], "list": [], "display": []}
        if not self.r25_root.exists():
            return pages

        # Search for page files under models/{model_name}/pages/
        patterns = [
            f"src/apps/**/models/{model_name}/pages/*Detail*.tsx",
            f"src/apps/**/models/{model_name}/pages/*List*.tsx",
            f"src/apps/**/models/{model_name}/pages/*Display*.tsx",
        ]

        for pattern in patterns:
            for path in self.r25_root.glob(pattern):
                # Skip legacy files prefixed with qqq_
                if path.name.startswith("qqq_"):
                    continue
                # Skip backup copies (e.g., ContactDetail2.tsx)
                if re.search(r'\d+\s*\d*\.tsx$', path.name):
                    continue

                name_lower = path.name.lower()
                if "detail" in name_lower:
                    pages["detail"].append(path)
                elif "list" in name_lower:
                    pages["list"].append(path)
                elif "display" in name_lower:
                    pages["display"].append(path)

        return pages

    # ── Extract field references from page files ──────────────────────

    def _extract_detail_fields(self, file_path: Path) -> dict[str, set[str]]:
        """Extract field references from a Detail page (form page).

        Returns {pattern_label: {field_names}} for traceability.
        """
        fields_by_pattern: dict[str, set[str]] = {}

        try:
            content = file_path.read_text()
        except Exception:
            return fields_by_pattern

        # Core form field patterns (register, Controller, useWatch)
        for pattern, group, label in FIELD_PATTERNS:
            if label == "DETAIL_FIELDS":
                # Only apply inside explicit FIELDS array declarations
                fields_match = re.search(
                    r'const\s+\w*FIELDS\s*=\s*\[([\s\S]*?)\]\s*(?:as\s+const)?',
                    content,
                )
                if fields_match:
                    for m in pattern.finditer(fields_match.group(1)):
                        fields_by_pattern.setdefault(label, set()).add(m.group(1))
                continue

            for m in pattern.finditer(content):
                field_name = m.group(1)
                # Filter out non-field strings (e.g., CSS classes, component names)
                if self._is_valid_field_name(field_name):
                    fields_by_pattern.setdefault(label, set()).add(field_name)

        return fields_by_pattern

    def _extract_list_fields(self, file_path: Path) -> dict[str, set[str]]:
        """Extract field references from a List page (data table)."""
        fields_by_pattern: dict[str, set[str]] = {}

        try:
            content = file_path.read_text()
        except Exception:
            return fields_by_pattern

        for pattern, group, label in LIST_PATTERNS:
            for m in pattern.finditer(content):
                if label == "valueFrom":
                    # Extract all quoted strings from the array
                    candidates = re.findall(r'"([^"]+)"', m.group(1))
                    for c in candidates:
                        if self._is_valid_field_name(c):
                            fields_by_pattern.setdefault(label, set()).add(c)
                else:
                    field_name = m.group(1)
                    if self._is_valid_field_name(field_name):
                        fields_by_pattern.setdefault(label, set()).add(field_name)

        return fields_by_pattern

    def _extract_display_fields(self, file_path: Path) -> dict[str, set[str]]:
        """Extract field references from a Display page (read-only view).

        Display pages may use ScalarCard, JsonCard, handleFieldChange, or
        direct data.field access.
        """
        fields_by_pattern: dict[str, set[str]] = {}

        try:
            content = file_path.read_text()
        except Exception:
            return fields_by_pattern

        # Use the same core patterns (ScalarCard labels, JsonCard fieldName, etc.)
        for pattern, group, label in FIELD_PATTERNS:
            if label == "DETAIL_FIELDS":
                continue
            for m in pattern.finditer(content):
                field_name = m.group(1)
                if self._is_valid_field_name(field_name):
                    fields_by_pattern.setdefault(label, set()).add(field_name)

        # Also look for data.field_name access patterns
        data_access = re.compile(r'data\.(\w+)')
        for m in data_access.finditer(content):
            field_name = m.group(1)
            if self._is_valid_field_name(field_name):
                fields_by_pattern.setdefault("data_access", set()).add(field_name)

        return fields_by_pattern

    @staticmethod
    def _is_valid_field_name(name: str) -> bool:
        """Filter out strings that are clearly not Django field names."""
        if not name or len(name) > 80:
            return False
        # Must be snake_case or simple lowercase
        if not re.match(r'^[a-z][a-z0-9_]*$', name):
            return False
        # Exclude common non-field strings
        non_fields = {
            "true", "false", "null", "undefined", "none", "default",
            "submit", "reset", "cancel", "save", "delete", "edit",
            "loading", "error", "success", "pending", "required",
            "type", "key", "value", "index", "item", "row", "col",
            "display", "visible", "hidden", "disabled", "readonly",
            "left", "right", "center", "top", "bottom",
            "sm", "md", "lg", "xl", "xxl",
            "primary", "secondary", "warning", "danger", "info",
        }
        if name in non_fields:
            return False
        return True

    # ── Map JSON sub-fields to parent JSONField ───────────────────────

    def _resolve_json_subfields(
        self, layout_fields: set[str], json_field_names: set[str]
    ) -> tuple[set[str], dict[str, str]]:
        """Separate layout fields into direct model fields and JSON sub-fields.

        Returns:
            (remaining_fields, json_mappings)
            - remaining_fields: layout fields that aren't JSON sub-fields
            - json_mappings: {sub_field: parent_json_field} for recognized sub-fields
        """
        remaining = set()
        json_mappings: dict[str, str] = {}

        for field in layout_fields:
            mapped = False
            # Check against known prefixes
            for json_parent, sub_fields in JSON_FIELD_PREFIXES.items():
                if json_parent in json_field_names and field in sub_fields:
                    json_mappings[field] = json_parent
                    mapped = True
                    break
            # Also check prefix heuristic: if field starts with a JSON field name
            if not mapped:
                for jf in json_field_names:
                    if field.startswith(f"{jf}_") and jf != field:
                        json_mappings[field] = jf
                        mapped = True
                        break
            if not mapped:
                remaining.add(field)

        return remaining, json_mappings

    # ── Drift detection for a single model ────────────────────────────

    def detect_model(self, model_name: str) -> dict[str, Any]:
        """Detect layout drift for a single model.

        Returns:
            {
                'model': str,
                'django_fields': int,
                'pages_found': {'detail': [str], 'list': [str], 'display': [str]},
                'layout_fields': {'detail': [str], 'list': [str], 'display': [str]},
                'issues': [
                    {'field': str, 'type': str, 'page_type': str, 'detail': str, 'severity': str},
                ],
            }
        """
        django_fields = self._get_django_fields(model_name)
        if django_fields is None:
            return {"model": model_name, "error": f"Django model '{model_name}' not found"}

        # Find page files
        page_files = self._find_page_files(model_name)
        pages_found = {
            k: [str(p.relative_to(self.r25_root)) for p in v]
            for k, v in page_files.items()
        }

        if not any(page_files.values()):
            return {
                "model": model_name,
                "django_fields": len(django_fields),
                "pages_found": pages_found,
                "layout_fields": {"detail": [], "list": [], "display": []},
                "issues": [{
                    "field": "*",
                    "type": "no_pages",
                    "page_type": "all",
                    "detail": "No React page files found for this model",
                    "severity": "info",
                }],
            }

        # Extract fields from each page type
        all_detail_fields: set[str] = set()
        all_list_fields: set[str] = set()
        all_display_fields: set[str] = set()
        all_layout_fields: set[str] = set()

        for fp in page_files["detail"]:
            by_pattern = self._extract_detail_fields(fp)
            for fields in by_pattern.values():
                all_detail_fields |= fields

        for fp in page_files["list"]:
            by_pattern = self._extract_list_fields(fp)
            for fields in by_pattern.values():
                all_list_fields |= fields

        for fp in page_files["display"]:
            by_pattern = self._extract_display_fields(fp)
            for fields in by_pattern.values():
                all_display_fields |= fields

        all_layout_fields = all_detail_fields | all_list_fields | all_display_fields

        # Resolve JSON sub-fields
        json_field_names = {n for n, info in django_fields.items() if info.get("is_json")}
        layout_direct, json_mappings = self._resolve_json_subfields(
            all_layout_fields, json_field_names
        )

        # Build comparable sets
        django_field_names = set(django_fields.keys())
        skip_fields = BASE_MODEL_CARD_FIELDS | INTERNAL_FIELDS

        issues = []

        # 1. Layout references a field that doesn't exist in Django
        for field in sorted(layout_direct - django_field_names - skip_fields):
            # Determine which page type(s) reference this field
            page_types = []
            if field in all_detail_fields:
                page_types.append("detail")
            if field in all_list_fields:
                page_types.append("list")
            if field in all_display_fields:
                page_types.append("display")

            issues.append({
                "field": field,
                "type": "phantom_field",
                "page_type": ", ".join(page_types),
                "detail": (
                    f"Layout references '{field}' but Django model has no such field. "
                    f"Found in: {', '.join(page_types)}"
                ),
                "severity": "high",
            })

        # 2. Django fields not referenced in any layout
        rendered_fields = layout_direct | set(json_mappings.values()) | skip_fields
        for field in sorted(django_field_names - rendered_fields):
            info = django_fields[field]
            # Skip reverse relations and auto-generated fields
            if info["django_type"] in ("ManyToManyField", "ManyToManyRel",
                                        "ManyToOneRel", "ForeignKey"):
                continue

            severity = "medium" if info["required"] else "low"
            issues.append({
                "field": field,
                "type": "unrendered_field",
                "page_type": "none",
                "detail": (
                    f"Django has '{field}' ({info['django_type']}) but no layout references it. "
                    f"{'Required field — likely needs a form input.' if info['required'] else 'Optional field — may be intentionally hidden.'}"
                ),
                "severity": severity,
            })

        # 3. Detail page has the field but List page doesn't (and vice versa)
        #    — informational, not always an issue
        detail_only = all_detail_fields - all_list_fields - all_display_fields - skip_fields
        # Filter to direct django fields only (not JSON sub-fields)
        detail_only_direct = detail_only & django_field_names
        if detail_only_direct and page_files["list"]:
            for field in sorted(detail_only_direct):
                # Skip FK fields from list-only check (common to omit from lists)
                if django_fields.get(field, {}).get("is_fk"):
                    continue
                issues.append({
                    "field": field,
                    "type": "detail_only",
                    "page_type": "detail",
                    "detail": f"'{field}' appears in Detail page but not in List columns",
                    "severity": "info",
                })

        # 4. JSON sub-field coverage check
        for json_parent in json_field_names - skip_fields:
            sub_fields = [sf for sf, parent in json_mappings.items() if parent == json_parent]
            if not sub_fields and json_parent not in all_layout_fields:
                issues.append({
                    "field": json_parent,
                    "type": "unrendered_json",
                    "page_type": "none",
                    "detail": (
                        f"JSONField '{json_parent}' has no sub-field references "
                        f"and no JsonCard in any layout"
                    ),
                    "severity": "low",
                })

        return {
            "model": model_name,
            "django_fields": len(django_fields),
            "pages_found": pages_found,
            "layout_fields": {
                "detail": sorted(all_detail_fields),
                "list": sorted(all_list_fields),
                "display": sorted(all_display_fields),
            },
            "json_mappings": json_mappings,
            "issues": sorted(
                issues,
                key=lambda x: {"high": 0, "medium": 1, "low": 2, "info": 3}[x["severity"]],
            ),
        }

    # ── Bulk detection ────────────────────────────────────────────────

    def detect_all(self) -> dict[str, Any]:
        """Detect layout drift across all registered models."""
        from common.models import BaseModel

        results: dict[str, Any] = {}
        total_issues = 0

        for model_cls in apps.get_models():
            if not issubclass(model_cls, BaseModel) or model_cls is BaseModel:
                continue
            name = model_cls.__name__.lower()
            result = self.detect_model(name)

            # Only include models that have pages or errors
            if any(result.get("pages_found", {}).values()) or result.get("error"):
                results[name] = result
                total_issues += len(
                    [i for i in result.get("issues", []) if i.get("severity") != "info"]
                )

        return {
            "models_checked": len(results),
            "total_issues": total_issues,
            "severity_counts": {
                "high": sum(
                    1 for r in results.values()
                    for i in r.get("issues", []) if i.get("severity") == "high"
                ),
                "medium": sum(
                    1 for r in results.values()
                    for i in r.get("issues", []) if i.get("severity") == "medium"
                ),
                "low": sum(
                    1 for r in results.values()
                    for i in r.get("issues", []) if i.get("severity") == "low"
                ),
                "info": sum(
                    1 for r in results.values()
                    for i in r.get("issues", []) if i.get("severity") == "info"
                ),
            },
            "per_model": results,
        }

    # ── LLM-enhanced analysis ─────────────────────────────────────────

    def llm_analyze_drift(self, report: dict[str, Any]) -> str:
        """Use Ollama to generate a narrative analysis of layout drift."""
        client = self._get_client()
        if not client:
            return "LLM not available — enable with use_llm=True"

        issues_summary = []
        for model_name, data in report.get("per_model", {}).items():
            for issue in data.get("issues", []):
                if issue["severity"] == "info":
                    continue
                issues_summary.append(
                    f"[{issue['severity'].upper()}] {model_name}.{issue['field']} "
                    f"({issue['type']}): {issue['detail']}"
                )

        if not issues_summary:
            return "No layout drift detected."

        prompt = (
            "Analyze these layout drift issues between Django model fields and "
            "React page components.\n"
            "For each issue, explain whether it's a real problem or expected.\n"
            "Group by severity and suggest concrete fixes.\n"
            "- 'phantom_field': layout references a field that doesn't exist in Django\n"
            "- 'unrendered_field': Django field exists but no layout references it\n"
            "- 'unrendered_json': JSONField has no sub-field form inputs or JsonCard\n\n"
            + "\n".join(issues_summary[:50])
        )

        try:
            return client.generate(prompt, mode="developer")
        except Exception as e:
            return f"LLM analysis failed: {e}"

    # ── Report formatting ─────────────────────────────────────────────

    def format_report(self, report: dict[str, Any]) -> str:
        """Format layout drift report as markdown."""
        lines = [
            "# Layout ↔ Schema Drift Report",
            f"Generated: {__import__('django').utils.timezone.now():%Y-%m-%d %H:%M}",
            "",
            f"**Models with pages:** {report.get('models_checked', 0)}",
            f"**Total issues (excl. info):** {report.get('total_issues', 0)}",
        ]

        severity = report.get("severity_counts", {})
        lines.append(
            f"**Severity:** 🔴 High: {severity.get('high', 0)} | "
            f"🟡 Medium: {severity.get('medium', 0)} | "
            f"🔵 Low: {severity.get('low', 0)} | "
            f"ℹ️  Info: {severity.get('info', 0)}"
        )
        lines.append("")

        for model_name, data in report.get("per_model", {}).items():
            if "error" in data:
                lines.append(f"## {model_name.title()}\n⚠️ {data['error']}\n")
                continue

            issues = data.get("issues", [])
            pages = data.get("pages_found", {})
            page_counts = {k: len(v) for k, v in pages.items() if v}

            lines.append(f"## {model_name.title()}")
            lines.append(
                f"Django fields: {data.get('django_fields', 0)} | "
                f"Pages: {', '.join(f'{k}({c})' for k, c in page_counts.items())}"
            )

            layout = data.get("layout_fields", {})
            for page_type in ("detail", "list", "display"):
                field_list = layout.get(page_type, [])
                if field_list:
                    lines.append(f"  {page_type.title()} fields ({len(field_list)}): "
                                 f"{', '.join(field_list[:15])}"
                                 f"{'...' if len(field_list) > 15 else ''}")

            if not issues:
                lines.append("✅ No issues detected\n")
                continue

            lines.append("")
            for issue in issues:
                icon = {
                    "high": "🔴", "medium": "🟡", "low": "🔵", "info": "ℹ️"
                }[issue["severity"]]
                lines.append(
                    f"- {icon} **{issue['field']}** ({issue['type']}): {issue['detail']}"
                )
            lines.append("")

        return "\n".join(lines)
