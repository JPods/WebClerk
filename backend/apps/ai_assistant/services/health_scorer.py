"""
5E. Record Data Health Scoring — Populate HealthMixin.health_rating (0-100).

Deterministic rules handle 80% of the score (field completeness, recency,
link integrity). Ollama evaluates subjective quality for a sample of records.

Usage:
    from apps.ai_assistant.services.health_scorer import HealthScorer

    scorer = HealthScorer()
    result = scorer.score_all(limit=500)       # nightly bulk run
    result = scorer.score_record(obj)           # single record
    result = scorer.score_model('contact', limit=200)
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.apps import apps
from django.utils import timezone

logger = logging.getLogger(__name__)


# ── Per-model scoring rules ────────────────────────────────────────────
# Each rule: (field_or_check, points, description)
# Checks can be:
#   - "field:name"          → field is truthy
#   - "json_key:field.path" → dotted path into a JSONField is truthy
#   - "related:accessor"    → related manager has ≥1 row
#   - "recency:days"        → modified within N days
#   - callable(obj) → bool

SCORING_RULES: dict[str, list[tuple[str, int, str]]] = {
    "contact": [
        ("field:name",                     10, "Has name"),
        ("related:emails",                 10, "Has email"),
        ("related:phones",                 10, "Has phone"),
        ("related:addresses",              15, "Has address"),
        ("json_key:refs.keywords",          5, "Keywords populated"),
        ("json_key:refs.links",             5, "Has linked records"),
        ("json_key:metadata.history.verified.dt", 15, "Has been verified"),
        ("recency:180",                    20, "Active in last 6 months"),
        ("field:description",              10, "Has description"),
    ],
    "customer": [
        ("field:name",                     10, "Has name"),
        ("field:contact_id",               10, "Linked to contact"),
        ("json_key:refs.keywords",          5, "Keywords populated"),
        ("json_key:refs.links",             5, "Has linked records"),
        ("json_key:metadata.history.verified.dt", 10, "Has been verified"),
        ("related:orders",                 15, "Has orders"),
        ("recency:365",                    15, "Active in last year"),
        ("field:description",              10, "Has description"),
        ("json_key:prefs",                  5, "Preferences set"),
        ("field:terms_id",                 15, "Terms assigned"),
    ],
    "vendor": [
        ("field:name",                     10, "Has name"),
        ("field:contact_id",               10, "Linked to contact"),
        ("json_key:refs.keywords",          5, "Keywords populated"),
        ("related:purchases",              15, "Has purchases"),
        ("recency:365",                    15, "Active in last year"),
        ("field:description",              10, "Has description"),
        ("field:terms_id",                 15, "Terms assigned"),
        ("json_key:metadata.history.verified.dt", 10, "Has been verified"),
        ("json_key:refs.links",             5, "Has linked records"),
        ("json_key:prefs",                  5, "Preferences set"),
    ],
    "item": [
        ("field:name",                     10, "Has name"),
        ("field:sku",                      10, "Has SKU"),
        ("field:description",              10, "Has description"),
        ("json_key:price.base",            15, "Base price set"),
        ("json_key:cost.average",          15, "Average cost set"),
        ("json_key:quantity.on_hand",      10, "On-hand tracked"),
        ("json_key:refs.keywords",          5, "Keywords populated"),
        ("field:uom",                       5, "UOM specified"),
        ("field:specification_id",         10, "Has specification"),
        ("recency:365",                    10, "Updated in last year"),
    ],
    "order": [
        ("field:ida",                      10, "Has document ID"),
        ("field:contact_id",               10, "Has contact"),
        ("field:org_id",                   10, "Has organization"),
        ("json_key:totals.total",          15, "Totals calculated"),
        ("related:order_lines",            20, "Has line items"),
        ("json_key:refs.links",             5, "Has linked records"),
        ("field:terms_id",                 10, "Terms assigned"),
        ("field:rep_id",                   10, "Rep assigned"),
        ("field:description",               5, "Has description"),
        ("json_key:metadata.flow",          5, "Flow context set"),
    ],
    "invoice": [
        ("field:ida",                      10, "Has document ID"),
        ("field:contact_id",               10, "Has contact"),
        ("field:org_id",                   10, "Has organization"),
        ("json_key:totals.total",          15, "Totals calculated"),
        ("related:invoice_lines",          20, "Has line items"),
        ("field:parent_id",               10, "Linked to source order"),
        ("field:terms_id",                 10, "Terms assigned"),
        ("field:rep_id",                    5, "Rep assigned"),
        ("field:description",               5, "Has description"),
        ("json_key:metadata.flow",          5, "Flow context set"),
    ],
    "address": [
        ("field:address1",                 15, "Has street address"),
        ("field:city",                     15, "Has city"),
        ("field:state",                    15, "Has state"),
        ("field:zip",                      15, "Has zip code"),
        ("field:country",                  10, "Has country"),
        ("field:contact_id",              10, "Linked to contact"),
        ("field:latitude",                 10, "Geocoded"),
        ("json_key:metadata.history.verified.dt", 10, "Has been verified"),
    ],
}

# Fallback rules for models not explicitly configured
DEFAULT_RULES: list[tuple[str, int, str]] = [
    ("field:name",                     15, "Has name"),
    ("json_key:refs.keywords",         10, "Keywords populated"),
    ("json_key:refs.links",            10, "Has linked records"),
    ("json_key:metadata.history.verified.dt", 15, "Has been verified"),
    ("recency:365",                    20, "Updated in last year"),
    ("field:description",              15, "Has description"),
    ("field:is_active",                15, "Record is active"),
]


class HealthScorer:
    """Evaluate data quality for records with HealthMixin."""

    def __init__(self, use_llm: bool = False, llm_sample_rate: float = 0.05):
        """
        Args:
            use_llm: Whether to use Ollama for subjective quality scoring
            llm_sample_rate: Fraction of records to evaluate with LLM (0.0-1.0)
        """
        self.use_llm = use_llm
        self.llm_sample_rate = llm_sample_rate
        self._client = None

    def _get_client(self):
        if self._client is None and self.use_llm:
            from apps.ai_assistant.services.ollama_client import OllamaClient
            self._client = OllamaClient()
        return self._client

    # ── Single-record scoring ──────────────────────────────────────────

    def score_record(self, obj, rules: list | None = None) -> dict[str, Any]:
        """Score a single record against its rule set.

        Returns:
            {
                'score': int (0-100),
                'breakdown': [{'rule': str, 'points': int, 'earned': bool, 'desc': str}],
                'model': str,
                'pk': int,
            }
        """
        model_name = obj.__class__.__name__.lower()
        rules = rules or SCORING_RULES.get(model_name, DEFAULT_RULES)

        total_possible = sum(r[1] for r in rules)
        earned = 0
        breakdown = []

        for check, points, desc in rules:
            passed = self._evaluate_check(obj, check)
            if passed:
                earned += points
            breakdown.append({
                "rule": check,
                "points": points,
                "earned": passed,
                "desc": desc,
            })

        # Normalize to 0-100 scale
        score = round((earned / total_possible) * 100) if total_possible > 0 else 0

        return {
            "score": score,
            "breakdown": breakdown,
            "model": model_name,
            "pk": getattr(obj, "pk", None),
        }

    def _evaluate_check(self, obj, check: str) -> bool:
        """Evaluate a single check against an object."""
        try:
            if check.startswith("field:"):
                field_name = check[6:]
                val = getattr(obj, field_name, None)
                return bool(val)

            elif check.startswith("json_key:"):
                path = check[9:]
                parts = path.split(".", 1)
                field_name = parts[0]
                json_path = parts[1] if len(parts) > 1 else None

                data = getattr(obj, field_name, None)
                if not isinstance(data, dict):
                    return False
                if json_path is None:
                    return bool(data)

                # Walk dotted path
                cur = data
                for key in json_path.split("."):
                    if not isinstance(cur, dict):
                        return False
                    cur = cur.get(key)
                    if cur is None:
                        return False
                # Non-empty value
                if isinstance(cur, (list, dict)):
                    return len(cur) > 0
                return bool(cur)

            elif check.startswith("related:"):
                accessor = check[8:]
                manager = getattr(obj, accessor, None)
                if manager is None:
                    return False
                return manager.exists()

            elif check.startswith("recency:"):
                days = int(check[8:])
                cutoff = timezone.now() - timedelta(days=days)
                # Check metadata modified timestamp
                if hasattr(obj, "metadata") and isinstance(obj.metadata, dict):
                    mod_ms = (obj.metadata.get("history", {})
                              .get("modified", {})
                              .get("dt", 0))
                    if mod_ms:
                        from datetime import datetime
                        mod_dt = datetime.fromtimestamp(mod_ms / 1000, tz=timezone.utc)
                        return mod_dt >= cutoff
                # Fallback to Django auto-field
                dt_modified = getattr(obj, "dt_modified", None) or getattr(obj, "modified_at", None)
                if dt_modified:
                    return dt_modified >= cutoff
                return False

            elif callable(check):
                return bool(check(obj))

        except Exception as e:
            logger.debug("Health check %s failed for %s: %s", check, obj, e)
            return False

        return False

    # ── LLM-enhanced scoring (sampled) ──────────────────────────────────

    def _llm_quality_bonus(self, obj) -> int:
        """Ask Ollama to evaluate subjective data quality. Returns 0-15 bonus points."""
        client = self._get_client()
        if not client:
            return 0

        try:
            model_name = obj.__class__.__name__
            # Build a compact record summary for the LLM
            summary_parts = []
            for field in ("name", "description", "address1", "city", "ida"):
                val = getattr(obj, field, None)
                if val:
                    summary_parts.append(f"{field}: {val}")

            if hasattr(obj, "refs") and isinstance(obj.refs, dict):
                kw = obj.refs.get("keywords", [])
                if kw:
                    summary_parts.append(f"keywords: {', '.join(kw[:10])}")

            record_text = "\n".join(summary_parts)
            prompt = (
                f"Rate the data quality of this {model_name} record on a scale of 0-15.\n"
                f"Consider: completeness, consistency, specificity, usefulness.\n"
                f"Reply with ONLY a number 0-15.\n\n"
                f"{record_text}"
            )
            response = client.generate(prompt, mode="general")
            # Extract number from response
            import re
            match = re.search(r'\b(\d{1,2})\b', response)
            if match:
                return min(int(match.group(1)), 15)
        except Exception as e:
            logger.debug("LLM health scoring failed: %s", e)

        return 0

    # ── Bulk scoring ───────────────────────────────────────────────────

    def score_model(self, model_name: str, limit: int = 500) -> dict[str, Any]:
        """Score all records of a specific model type.

        Returns:
            {
                'model': str,
                'processed': int,
                'updated': int,
                'avg_score': float,
                'distribution': {range_label: count},
            }
        """
        from common.models import BaseModel

        model_cls = None
        for m in apps.get_models():
            if m.__name__.lower() == model_name.lower() and issubclass(m, BaseModel):
                model_cls = m
                break

        if model_cls is None:
            return {"model": model_name, "error": f"Model '{model_name}' not found or not a BaseModel"}

        if not hasattr(model_cls, "health_rating"):
            return {"model": model_name, "error": f"Model '{model_name}' does not have HealthMixin"}

        rules = SCORING_RULES.get(model_name.lower(), DEFAULT_RULES)
        qs = model_cls.objects.filter(is_active=True).order_by("pk")[:limit]

        processed = 0
        updated = 0
        total_score = 0
        distribution = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
        import random

        for obj in qs.iterator(chunk_size=200):
            result = self.score_record(obj, rules=rules)
            score = result["score"]

            # Optional LLM bonus for a sample
            if self.use_llm and random.random() < self.llm_sample_rate:
                bonus = self._llm_quality_bonus(obj)
                score = min(score + bonus, 100)

            if obj.health_rating != score:
                model_cls.objects.filter(pk=obj.pk).update(health_rating=score)
                updated += 1

            total_score += score
            processed += 1

            # Distribution
            if score <= 20:
                distribution["0-20"] += 1
            elif score <= 40:
                distribution["21-40"] += 1
            elif score <= 60:
                distribution["41-60"] += 1
            elif score <= 80:
                distribution["61-80"] += 1
            else:
                distribution["81-100"] += 1

        avg = round(total_score / processed, 1) if processed > 0 else 0

        return {
            "model": model_name,
            "processed": processed,
            "updated": updated,
            "avg_score": avg,
            "distribution": distribution,
        }

    def score_all(self, limit: int = 500) -> dict[str, Any]:
        """Score all models that have HealthMixin.

        Returns summary with per-model results.
        """
        from common.models import BaseModel

        results = {}
        models_found = []

        for model_cls in apps.get_models():
            if (issubclass(model_cls, BaseModel)
                    and model_cls is not BaseModel
                    and hasattr(model_cls, "health_rating")):
                models_found.append(model_cls.__name__.lower())

        for model_name in sorted(models_found):
            results[model_name] = self.score_model(model_name, limit=limit)

        total_processed = sum(r.get("processed", 0) for r in results.values())
        total_updated = sum(r.get("updated", 0) for r in results.values())

        return {
            "models_scored": len(results),
            "total_processed": total_processed,
            "total_updated": total_updated,
            "per_model": results,
        }

    # ── Report generation ──────────────────────────────────────────────

    def generate_report(self, results: dict[str, Any]) -> str:
        """Generate a human-readable health report from scoring results."""
        lines = [
            "# Data Health Report",
            f"Generated: {timezone.now():%Y-%m-%d %H:%M}",
            "",
            f"**Models scored:** {results.get('models_scored', 0)}",
            f"**Records processed:** {results.get('total_processed', 0)}",
            f"**Records updated:** {results.get('total_updated', 0)}",
            "",
        ]

        for model_name, data in results.get("per_model", {}).items():
            if "error" in data:
                lines.append(f"## {model_name.title()}\n⚠️ {data['error']}\n")
                continue

            dist = data.get("distribution", {})
            lines.extend([
                f"## {model_name.title()}",
                f"- Average score: **{data.get('avg_score', 0)}**/100",
                f"- Records processed: {data.get('processed', 0)}",
                f"- Records updated: {data.get('updated', 0)}",
                f"- Distribution: "
                f"0-20: {dist.get('0-20', 0)} | "
                f"21-40: {dist.get('21-40', 0)} | "
                f"41-60: {dist.get('41-60', 0)} | "
                f"61-80: {dist.get('61-80', 0)} | "
                f"81-100: {dist.get('81-100', 0)}",
                "",
            ])

        return "\n".join(lines)
