"""
5B. JSON Envelope Optimization — Analyze and compact .refs, .prefs, .metadata.

Scans denormalized JSON fields for bloat: orphaned links, duplicate keywords,
stale flags, and unused prefs keys. Generates optimization reports and
optionally auto-compacts with AtomicJSONMixin.

Usage:
    from apps.ai_assistant.services.json_optimizer import JSONOptimizer

    optimizer = JSONOptimizer()
    report = optimizer.analyze_all(limit=500)
    print(optimizer.format_report(report))
    optimizer.compact_all(limit=500, dry_run=True)
"""
from __future__ import annotations

import logging
from collections import Counter
from typing import Any

from django.apps import apps
from django.utils import timezone

logger = logging.getLogger(__name__)


# ── Keys known to be actively used by r25 frontend ─────────────────────
ACTIVE_PREFS_KEYS = {
    "display", "notifications", "defaults", "view_mode",
    "list_columns", "sort_order", "filters",
}

ACTIVE_METADATA_FLAGS = {
    "schema_rev", "keywords_pending", "verified",
}

# Maximum age (in days) for metadata.history entries before they're stale
HISTORY_RETENTION_DAYS = 365 * 2  # 2 years


class JSONOptimizer:
    """Analyze and compact denormalized JSON fields."""

    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm
        self._client = None

    def _get_client(self):
        if self._client is None and self.use_llm:
            from apps.ai_assistant.services.ollama_client import OllamaClient
            self._client = OllamaClient()
        return self._client

    # ── Refs analysis ──────────────────────────────────────────────────

    def analyze_refs(self, obj) -> dict[str, Any]:
        """Analyze a single record's refs JSON for optimization opportunities."""
        issues = []
        refs = getattr(obj, "refs", None)
        if not isinstance(refs, dict):
            return {"issues": [], "bytes": 0}

        import json
        byte_size = len(json.dumps(refs))

        # 1. Duplicate keywords
        keywords = refs.get("keywords", [])
        if isinstance(keywords, list) and len(keywords) != len(set(k.lower() if isinstance(k, str) else k for k in keywords)):
            dupes = [k for k, cnt in Counter(
                k.lower() if isinstance(k, str) else k for k in keywords
            ).items() if cnt > 1]
            issues.append({
                "type": "duplicate_keywords",
                "detail": f"{len(dupes)} duplicate keywords: {dupes[:5]}",
                "severity": "low",
                "auto_fix": True,
            })

        # 2. Empty keywords
        empty_kw = [k for k in keywords if isinstance(k, str) and not k.strip()]
        if empty_kw:
            issues.append({
                "type": "empty_keywords",
                "detail": f"{len(empty_kw)} empty/whitespace-only keywords",
                "severity": "low",
                "auto_fix": True,
            })

        # 3. Orphaned links (reference IDs to deleted records)
        links = refs.get("links", {})
        if isinstance(links, dict):
            for model_key, ids_or_dicts in links.items():
                if isinstance(ids_or_dicts, list):
                    # Check for empty lists
                    if not ids_or_dicts:
                        issues.append({
                            "type": "empty_link_list",
                            "detail": f"refs.links.{model_key} is empty list",
                            "severity": "low",
                            "auto_fix": True,
                        })
                    # Check for None/null entries
                    nulls = [i for i, v in enumerate(ids_or_dicts) if v is None]
                    if nulls:
                        issues.append({
                            "type": "null_link_entries",
                            "detail": f"refs.links.{model_key} has {len(nulls)} null entries",
                            "severity": "medium",
                            "auto_fix": True,
                        })

        # 4. Oversized refs (> 32KB)
        if byte_size > 32768:
            issues.append({
                "type": "oversized_refs",
                "detail": f"refs is {byte_size:,} bytes (> 32KB threshold)",
                "severity": "high",
                "auto_fix": False,
            })

        return {"issues": issues, "bytes": byte_size}

    # ── Prefs analysis ─────────────────────────────────────────────────

    def analyze_prefs(self, obj) -> dict[str, Any]:
        """Analyze prefs JSON for unused or stale keys."""
        issues = []
        prefs = getattr(obj, "prefs", None)
        if not isinstance(prefs, dict):
            return {"issues": [], "bytes": 0}

        import json
        byte_size = len(json.dumps(prefs))

        # Find keys not in the active set
        unknown_keys = set(prefs.keys()) - ACTIVE_PREFS_KEYS
        if unknown_keys:
            issues.append({
                "type": "unknown_prefs_keys",
                "detail": f"Prefs keys not recognized by r25: {sorted(unknown_keys)}",
                "severity": "low",
                "auto_fix": False,  # Needs review — might be used by vue2020
            })

        # Empty prefs values
        empty_vals = [k for k, v in prefs.items() if v is None or v == {} or v == [] or v == ""]
        if empty_vals:
            issues.append({
                "type": "empty_prefs_values",
                "detail": f"Empty prefs values: {empty_vals}",
                "severity": "low",
                "auto_fix": True,
            })

        return {"issues": issues, "bytes": byte_size}

    # ── Metadata analysis ──────────────────────────────────────────────

    def analyze_metadata(self, obj) -> dict[str, Any]:
        """Analyze metadata JSON for stale flags, oversized history, etc."""
        issues = []
        metadata = getattr(obj, "metadata", None)
        if not isinstance(metadata, dict):
            return {"issues": [], "bytes": 0}

        import json
        byte_size = len(json.dumps(metadata))

        # 1. Stale flags
        flags = metadata.get("flags", {})
        if isinstance(flags, dict):
            unknown_flags = set(flags.keys()) - ACTIVE_METADATA_FLAGS
            if unknown_flags:
                issues.append({
                    "type": "stale_flags",
                    "detail": f"Metadata flags not in active set: {sorted(unknown_flags)}",
                    "severity": "low",
                    "auto_fix": False,
                })

        # 2. Missing required structure
        for required in ("history", "flags", "versioning"):
            if required not in metadata:
                issues.append({
                    "type": "missing_metadata_key",
                    "detail": f"metadata.{required} is missing",
                    "severity": "medium",
                    "auto_fix": True,
                })

        # 3. Oversized metadata
        if byte_size > 65536:
            issues.append({
                "type": "oversized_metadata",
                "detail": f"metadata is {byte_size:,} bytes (> 64KB threshold)",
                "severity": "high",
                "auto_fix": False,
            })

        return {"issues": issues, "bytes": byte_size}

    # ── Auto-fix / compact ─────────────────────────────────────────────

    def compact_record(self, obj, dry_run: bool = True) -> dict[str, Any]:
        """Apply auto-fixable optimizations to a single record.

        Returns dict of changes made (or that would be made if dry_run).
        """
        changes = {}

        # Compact refs
        if hasattr(obj, "refs") and isinstance(obj.refs, dict):
            refs = obj.refs

            # Deduplicate keywords
            kw = refs.get("keywords", [])
            if isinstance(kw, list):
                seen = set()
                deduped = []
                for k in kw:
                    lower = k.lower() if isinstance(k, str) else k
                    if lower and lower not in seen:
                        seen.add(lower)
                        deduped.append(lower)
                if deduped != kw:
                    changes["refs.keywords"] = {"from": len(kw), "to": len(deduped)}
                    if not dry_run:
                        refs["keywords"] = deduped

            # Remove empty link lists and null entries
            links = refs.get("links", {})
            if isinstance(links, dict):
                cleaned_links = {}
                for model_key, entries in links.items():
                    if isinstance(entries, list):
                        filtered = [e for e in entries if e is not None]
                        if filtered:  # Only keep non-empty
                            cleaned_links[model_key] = filtered
                        else:
                            changes[f"refs.links.{model_key}"] = "removed_empty"
                    else:
                        cleaned_links[model_key] = entries
                if cleaned_links != links:
                    if not dry_run:
                        refs["links"] = cleaned_links

        # Compact prefs — remove empty values
        if hasattr(obj, "prefs") and isinstance(obj.prefs, dict):
            prefs = obj.prefs
            empty_keys = [k for k, v in prefs.items() if v is None or v == {} or v == [] or v == ""]
            if empty_keys:
                changes["prefs.removed_empty"] = empty_keys
                if not dry_run:
                    for k in empty_keys:
                        del prefs[k]

        # Ensure metadata structure
        if hasattr(obj, "metadata") and isinstance(obj.metadata, dict):
            metadata = obj.metadata
            for required in ("history", "flags", "versioning"):
                if required not in metadata:
                    changes[f"metadata.{required}"] = "added_empty"
                    if not dry_run:
                        metadata[required] = {}

        if changes and not dry_run:
            # Save only the JSON fields to avoid side effects
            update_fields = {}
            if hasattr(obj, "refs"):
                update_fields["refs"] = obj.refs
            if hasattr(obj, "prefs"):
                update_fields["prefs"] = obj.prefs
            if hasattr(obj, "metadata"):
                update_fields["metadata"] = obj.metadata
            if update_fields:
                obj.__class__.objects.filter(pk=obj.pk).update(**update_fields)

        return {"pk": obj.pk, "changes": changes, "compacted": bool(changes)}

    # ── Bulk operations ────────────────────────────────────────────────

    def analyze_model(self, model_name: str, limit: int = 500) -> dict[str, Any]:
        """Analyze all records of a model for JSON optimization opportunities."""
        from common.models import BaseModel

        model_cls = None
        for m in apps.get_models():
            if m.__name__.lower() == model_name.lower() and issubclass(m, BaseModel):
                model_cls = m
                break

        if model_cls is None:
            return {"model": model_name, "error": f"Model '{model_name}' not found"}

        total_issues = Counter()
        total_bytes = {"refs": 0, "prefs": 0, "metadata": 0}
        records_with_issues = 0
        processed = 0

        qs = model_cls.objects.filter(is_active=True).order_by("pk")[:limit]
        for obj in qs.iterator(chunk_size=200):
            processed += 1
            has_issue = False

            if hasattr(obj, "refs"):
                r = self.analyze_refs(obj)
                total_bytes["refs"] += r["bytes"]
                for issue in r["issues"]:
                    total_issues[issue["type"]] += 1
                    has_issue = True

            if hasattr(obj, "prefs"):
                p = self.analyze_prefs(obj)
                total_bytes["prefs"] += p["bytes"]
                for issue in p["issues"]:
                    total_issues[issue["type"]] += 1
                    has_issue = True

            if hasattr(obj, "metadata"):
                m = self.analyze_metadata(obj)
                total_bytes["metadata"] += m["bytes"]
                for issue in m["issues"]:
                    total_issues[issue["type"]] += 1
                    has_issue = True

            if has_issue:
                records_with_issues += 1

        return {
            "model": model_name,
            "processed": processed,
            "records_with_issues": records_with_issues,
            "issue_counts": dict(total_issues),
            "total_bytes": total_bytes,
            "avg_bytes": {
                k: round(v / processed) if processed else 0
                for k, v in total_bytes.items()
            },
        }

    def analyze_all(self, limit: int = 500) -> dict[str, Any]:
        """Analyze all BaseModel subclasses for JSON optimization."""
        from common.models import BaseModel

        results = {}
        for model_cls in apps.get_models():
            if not issubclass(model_cls, BaseModel) or model_cls is BaseModel:
                continue
            name = model_cls.__name__.lower()
            results[name] = self.analyze_model(name, limit=limit)

        total_issues = sum(
            r.get("records_with_issues", 0) for r in results.values()
        )
        return {
            "models_analyzed": len(results),
            "total_records_with_issues": total_issues,
            "per_model": results,
        }

    def compact_all(self, limit: int = 500, dry_run: bool = True) -> dict[str, Any]:
        """Compact all BaseModel records, fixing auto-fixable issues."""
        from common.models import BaseModel

        total_compacted = 0
        total_processed = 0

        for model_cls in apps.get_models():
            if not issubclass(model_cls, BaseModel) or model_cls is BaseModel:
                continue
            qs = model_cls.objects.filter(is_active=True).order_by("pk")[:limit]
            for obj in qs.iterator(chunk_size=200):
                total_processed += 1
                result = self.compact_record(obj, dry_run=dry_run)
                if result.get("compacted"):
                    total_compacted += 1

        return {
            "processed": total_processed,
            "compacted": total_compacted,
            "dry_run": dry_run,
        }

    # ── Report ─────────────────────────────────────────────────────────

    def format_report(self, report: dict[str, Any]) -> str:
        """Format analysis report as markdown."""
        lines = [
            "# JSON Envelope Optimization Report",
            f"Generated: {timezone.now():%Y-%m-%d %H:%M}",
            "",
            f"**Models analyzed:** {report.get('models_analyzed', 0)}",
            f"**Records with issues:** {report.get('total_records_with_issues', 0)}",
            "",
        ]

        for model_name, data in report.get("per_model", {}).items():
            if "error" in data:
                lines.append(f"## {model_name.title()}\n⚠️ {data['error']}\n")
                continue

            issues = data.get("issue_counts", {})
            if not issues:
                continue

            avg = data.get("avg_bytes", {})
            lines.extend([
                f"## {model_name.title()}",
                f"- Processed: {data.get('processed', 0)}",
                f"- Records with issues: {data.get('records_with_issues', 0)}",
                f"- Avg bytes: refs={avg.get('refs', 0)}, prefs={avg.get('prefs', 0)}, metadata={avg.get('metadata', 0)}",
                f"- Issues:",
            ])
            for issue_type, count in sorted(issues.items()):
                lines.append(f"  - {issue_type}: {count}")
            lines.append("")

        return "\n".join(lines)
