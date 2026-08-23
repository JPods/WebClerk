from __future__ import annotations

from django.db import models
from typing import Iterable


def default_relationship_stats() -> dict:
    """Default structure for relationship statistics.

    Keys:
      counts: mapping of relation_type -> count (e.g., customers, vendors, manufacturers)
      dt_last: last updated timestamp per relation_type
    """
    return {"counts": {}, "dt_last": {}}


class RelationshipStatsMixin(models.Model):
    """Per-organization relationship statistics cache.

    Intended for OrgBase to quickly surface how many related orgs of each type are
    linked (e.g., how many customers a vendor services). Actual relationship edges
    live elsewhere (e.g., a relations JSON or join tables). This is a denormalized
    helper updated by service layer tasks or signals.
    """

    feature_flags = {"relationship_stats"}
    relationship_stats = models.JSONField(default=default_relationship_stats, blank=True)

    class Meta:
        abstract = True

    # ---- Update helpers -------------------------------------------------
    def set_relation_count(self, relation_type: str, count: int, dt_ms: int | None = None):
        stats = self.relationship_stats
        stats.setdefault("counts", {})[relation_type] = int(count)
        if dt_ms is not None:
            stats.setdefault("dt_last", {})[relation_type] = dt_ms
        self.relationship_stats = stats
        return count

    def bulk_set_relation_counts(self, mapping: dict[str, int], dt_ms: int | None = None):
        for k, v in mapping.items():
            self.set_relation_count(k, v, dt_ms=dt_ms)
        return self.relationship_stats.get("counts", {})

    def inc_relation(self, relation_type: str, delta: int = 1, dt_ms: int | None = None):
        stats = self.relationship_stats
        counts = stats.setdefault("counts", {})
        counts[relation_type] = int(counts.get(relation_type, 0)) + delta
        if dt_ms is not None:
            stats.setdefault("dt_last", {})[relation_type] = dt_ms
        self.relationship_stats = stats
        return counts[relation_type]

    # ---- Accessors ------------------------------------------------------
    def get_relation_count(self, relation_type: str) -> int:
        return int(self.relationship_stats.get("counts", {}).get(relation_type, 0)) if isinstance(self.relationship_stats, dict) else 0

    def top_relations(self, limit: int = 5) -> list[tuple[str, int]]:
        counts = self.relationship_stats.get("counts", {}) if isinstance(self.relationship_stats, dict) else {}
        return sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
