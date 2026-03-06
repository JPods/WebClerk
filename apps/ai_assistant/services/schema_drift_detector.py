"""
5D. Schema ↔ TypeScript Drift Detection.

Compares Django model field definitions against TypeScript interfaces and
Zod schemas in React2025 to detect mismatches (missing fields, wrong types,
required/optional disagreements).

Usage:
    from apps.ai_assistant.services.schema_drift_detector import SchemaDriftDetector

    detector = SchemaDriftDetector()
    report = detector.detect_all()           # full scan
    report = detector.detect_model('order')  # single model
    print(detector.format_report(report))
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

from django.apps import apps
from django.conf import settings

logger = logging.getLogger(__name__)


# ── Django field → expected TS type mapping ─────────────────────────────────
DJANGO_TO_TS: dict[str, str] = {
    "AutoField": "number",
    "BigAutoField": "number",
    "SmallAutoField": "number",
    "IntegerField": "number",
    "SmallIntegerField": "number",
    "BigIntegerField": "number",
    "PositiveIntegerField": "number",
    "PositiveSmallIntegerField": "number",
    "PositiveBigIntegerField": "number",
    "FloatField": "number",
    "DecimalField": "number",       # could be string in some TS patterns
    "BooleanField": "boolean",
    "NullBooleanField": "boolean",
    "CharField": "string",
    "TextField": "string",
    "SlugField": "string",
    "EmailField": "string",
    "URLField": "string",
    "UUIDField": "string",
    "FilePathField": "string",
    "IPAddressField": "string",
    "GenericIPAddressField": "string",
    "DateField": "string",         # ISO string in JSON
    "DateTimeField": "string",
    "TimeField": "string",
    "DurationField": "string",
    "JSONField": "Record<string, any>",
    "ArrayField": "any[]",
    "ForeignKey": "number",        # FK → id is number
    "OneToOneField": "number",
    "FileField": "string",
    "ImageField": "string",
    "BinaryField": "string",
}


# ── R25 project root (sibling of webClerk3) ────────────────────────────────
R25_ROOT = Path(settings.BASE_DIR).parent / "React2025"


class SchemaDriftDetector:
    """Compare Django model fields against TypeScript interfaces."""

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
        """Get all fields for a Django model as {name: {type, required, default, ...}}."""
        from common.models import BaseModel

        model_cls = None
        for m in apps.get_models():
            if m.__name__.lower() == model_name.lower() and issubclass(m, BaseModel):
                model_cls = m
                break

        if model_cls is None:
            return None

        fields = {}
        for f in model_cls._meta.get_fields():
            # Skip reverse relations (ManyToOneRel, ManyToManyRel, etc.)
            if not hasattr(f, "get_internal_type") or not hasattr(f, "has_default"):
                continue
            internal_type = f.get_internal_type()
            ts_type = DJANGO_TO_TS.get(internal_type, "unknown")

            # FK fields: the actual DB column is field_name + "_id"
            is_fk = internal_type in ("ForeignKey", "OneToOneField")
            db_name = f"{f.name}_id" if is_fk else f.name

            required = not getattr(f, "blank", True)
            nullable = getattr(f, "null", False)
            has_default = f.has_default()

            fields[db_name] = {
                "django_type": internal_type,
                "expected_ts": ts_type,
                "required": required and not has_default,
                "nullable": nullable,
                "has_default": has_default,
            }

        return fields

    # ── Parse TypeScript interfaces ────────────────────────────────────

    def _find_ts_files(self, model_name: str) -> list[Path]:
        """Find TypeScript type/interface files for a model in R25."""
        results = []
        if not self.r25_root.exists():
            return results

        # Search patterns
        patterns = [
            f"src/apps/**/models/{model_name}/types/*.ts",
            f"src/apps/**/models/{model_name}/types/*.tsx",
            f"src/model/**/{model_name.title()}*.ts",
            f"src/type/**/{model_name.title()}*.ts",
            f"src/generated/**/{model_name.title()}*.ts",
        ]

        for pattern in patterns:
            results.extend(self.r25_root.glob(pattern))

        return results

    def _parse_ts_interface(self, file_path: Path) -> dict[str, dict[str, Any]]:
        """Extract field names and types from a TypeScript interface/type."""
        fields: dict[str, dict[str, Any]] = {}

        try:
            content = file_path.read_text()
        except Exception:
            return fields

        # Match interface/type blocks: interface Foo { ... } or type Foo = { ... }
        interface_re = re.compile(
            r'(?:export\s+)?(?:interface|type)\s+\w+\s*(?:=\s*)?\{([^}]+)\}',
            re.DOTALL
        )

        for match in interface_re.finditer(content):
            body = match.group(1)
            # Parse field lines: name?: type; or name: type;
            field_re = re.compile(r'(\w+)(\?)?:\s*([^;,\n]+)')
            for fm in field_re.finditer(body):
                name = fm.group(1)
                optional = fm.group(2) == "?"
                ts_type = fm.group(3).strip()
                fields[name] = {
                    "ts_type": ts_type,
                    "optional": optional,
                    "source": str(file_path.relative_to(self.r25_root)),
                }

        return fields

    # ── Find Zod schemas ──────────────────────────────────────────────

    def _find_zod_files(self, model_name: str) -> list[Path]:
        """Find Zod validation schema files for a model."""
        results = []
        if not self.r25_root.exists():
            return results

        patterns = [
            f"src/validations/**/*{model_name}*.ts",
            f"src/apps/**/models/{model_name}/**/*schema*.ts",
            f"src/apps/**/models/{model_name}/**/*validation*.ts",
        ]

        for pattern in patterns:
            results.extend(self.r25_root.glob(pattern))

        return results

    # ── Drift comparison ──────────────────────────────────────────────

    def detect_model(self, model_name: str) -> dict[str, Any]:
        """Detect drift for a single model.

        Returns:
            {
                'model': str,
                'django_fields': int,
                'ts_fields': int,
                'ts_files': [str],
                'issues': [
                    {'field': str, 'type': str, 'detail': str, 'severity': str},
                ],
            }
        """
        django_fields = self._get_django_fields(model_name)
        if django_fields is None:
            return {"model": model_name, "error": f"Django model '{model_name}' not found"}

        # Gather all TS fields across interface files
        ts_files = self._find_ts_files(model_name)
        all_ts_fields: dict[str, dict[str, Any]] = {}
        ts_file_names = []

        for tf in ts_files:
            ts_file_names.append(str(tf.relative_to(self.r25_root)))
            parsed = self._parse_ts_interface(tf)
            all_ts_fields.update(parsed)

        if not all_ts_fields:
            return {
                "model": model_name,
                "django_fields": len(django_fields),
                "ts_fields": 0,
                "ts_files": ts_file_names,
                "issues": [{"field": "*", "type": "missing_ts", "detail": "No TypeScript interface found", "severity": "high"}],
            }

        issues = []

        # 1. Fields in Django but not in TS
        skip_fields = {"id", "is_active", "is_deleted", "created_by_id", "modified_by_id",
                       "metadata", "refs", "prefs", "comments", "actions", "health_rating",
                       "keywords_pending", "row_version"}
        for dj_name, dj_info in django_fields.items():
            if dj_name in skip_fields:
                continue
            if dj_name not in all_ts_fields:
                severity = "high" if dj_info["required"] else "medium"
                issues.append({
                    "field": dj_name,
                    "type": "missing_in_ts",
                    "detail": f"Django has '{dj_name}' ({dj_info['django_type']}) but TS interface does not",
                    "severity": severity,
                })

        # 2. Fields in TS but not in Django
        for ts_name, ts_info in all_ts_fields.items():
            if ts_name in skip_fields or ts_name in ("id",):
                continue
            if ts_name not in django_fields:
                # Could be a computed/virtual field — lower severity
                issues.append({
                    "field": ts_name,
                    "type": "missing_in_django",
                    "detail": f"TS has '{ts_name}' ({ts_info['ts_type']}) but Django model does not",
                    "severity": "low",
                })

        # 3. Type mismatches
        for name in set(django_fields) & set(all_ts_fields):
            dj_type = django_fields[name]["expected_ts"]
            ts_type = all_ts_fields[name]["ts_type"]

            if not self._types_compatible(dj_type, ts_type):
                issues.append({
                    "field": name,
                    "type": "type_mismatch",
                    "detail": f"Django expects '{dj_type}' but TS has '{ts_type}'",
                    "severity": "high",
                })

        # 4. Required/optional mismatches
        for name in set(django_fields) & set(all_ts_fields):
            dj_required = django_fields[name]["required"]
            ts_optional = all_ts_fields[name].get("optional", False)
            if dj_required and ts_optional:
                issues.append({
                    "field": name,
                    "type": "required_mismatch",
                    "detail": f"Django requires '{name}' but TS marks it optional",
                    "severity": "medium",
                })

        return {
            "model": model_name,
            "django_fields": len(django_fields),
            "ts_fields": len(all_ts_fields),
            "ts_files": ts_file_names,
            "issues": sorted(issues, key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["severity"]]),
        }

    def _types_compatible(self, django_ts: str, actual_ts: str) -> bool:
        """Check if Django's expected TS type is compatible with the actual TS type."""
        actual = actual_ts.strip().rstrip(";").strip()

        # Direct match
        if django_ts == actual:
            return True

        # number compatible types
        if django_ts == "number" and actual in ("number", "number | null", "number | undefined", "number | string", "int", "float"):
            return True

        # string compatible types
        if django_ts == "string" and actual in ("string", "string | null", "string | undefined"):
            return True

        # boolean compatible
        if django_ts == "boolean" and actual in ("boolean", "boolean | null", "boolean | undefined", "bool"):
            return True

        # JSON fields are flexible
        if django_ts == "Record<string, any>":
            if any(k in actual for k in ("Record", "object", "{", "any", "unknown", "JSON")):
                return True

        # Array fields
        if django_ts == "any[]" and ("[]" in actual or "Array" in actual):
            return True

        # Nullable suffixes
        if " | null" in actual or " | undefined" in actual:
            base = re.sub(r'\s*\|\s*(null|undefined)', '', actual).strip()
            return self._types_compatible(django_ts, base)

        return False

    # ── Bulk detection ────────────────────────────────────────────────

    def detect_all(self) -> dict[str, Any]:
        """Detect drift across all registered models."""
        from common.models import BaseModel

        results = {}
        total_issues = 0

        for model_cls in apps.get_models():
            if not issubclass(model_cls, BaseModel) or model_cls is BaseModel:
                continue
            name = model_cls.__name__.lower()
            result = self.detect_model(name)
            if result.get("ts_fields", 0) > 0 or result.get("error"):
                results[name] = result
                total_issues += len(result.get("issues", []))

        return {
            "models_checked": len(results),
            "total_issues": total_issues,
            "severity_counts": {
                "high": sum(1 for r in results.values() for i in r.get("issues", []) if i.get("severity") == "high"),
                "medium": sum(1 for r in results.values() for i in r.get("issues", []) if i.get("severity") == "medium"),
                "low": sum(1 for r in results.values() for i in r.get("issues", []) if i.get("severity") == "low"),
            },
            "per_model": results,
        }

    # ── LLM-enhanced analysis ─────────────────────────────────────────

    def llm_analyze_drift(self, report: dict[str, Any]) -> str:
        """Use Ollama to generate a narrative analysis of drift issues."""
        client = self._get_client()
        if not client:
            return "LLM not available — enable with use_llm=True"

        issues_summary = []
        for model_name, data in report.get("per_model", {}).items():
            for issue in data.get("issues", []):
                issues_summary.append(
                    f"[{issue['severity'].upper()}] {model_name}.{issue['field']}: {issue['detail']}"
                )

        if not issues_summary:
            return "No schema drift detected."

        prompt = (
            "Analyze these schema drift issues between Django backend and React TypeScript frontend.\n"
            "Group by severity, suggest fixes, and identify patterns.\n\n"
            + "\n".join(issues_summary[:50])  # Cap to avoid context overflow
        )

        try:
            return client.generate(prompt, mode="developer")
        except Exception as e:
            return f"LLM analysis failed: {e}"

    # ── Report formatting ─────────────────────────────────────────────

    def format_report(self, report: dict[str, Any]) -> str:
        """Format drift report as markdown."""
        lines = [
            "# Schema Drift Report",
            f"Generated: {__import__('django').utils.timezone.now():%Y-%m-%d %H:%M}",
            "",
            f"**Models checked:** {report.get('models_checked', 0)}",
            f"**Total issues:** {report.get('total_issues', 0)}",
        ]

        severity = report.get("severity_counts", {})
        lines.append(
            f"**Severity:** 🔴 High: {severity.get('high', 0)} | "
            f"🟡 Medium: {severity.get('medium', 0)} | "
            f"🔵 Low: {severity.get('low', 0)}"
        )
        lines.append("")

        for model_name, data in report.get("per_model", {}).items():
            if "error" in data:
                lines.append(f"## {model_name.title()}\n⚠️ {data['error']}\n")
                continue

            issues = data.get("issues", [])
            lines.append(f"## {model_name.title()}")
            lines.append(f"Django fields: {data.get('django_fields', 0)} | TS fields: {data.get('ts_fields', 0)}")
            if data.get("ts_files"):
                lines.append(f"TS files: {', '.join(data['ts_files'])}")

            if not issues:
                lines.append("✅ No issues detected\n")
                continue

            lines.append("")
            for issue in issues:
                icon = {"high": "🔴", "medium": "🟡", "low": "🔵"}[issue["severity"]]
                lines.append(f"- {icon} **{issue['field']}** ({issue['type']}): {issue['detail']}")
            lines.append("")

        return "\n".join(lines)
