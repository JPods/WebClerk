"""
5A. Database Sync Conflict Advisor.

Deterministic sync engine compares row versions between wc3 (PostgreSQL)
and wc2 (4D). Ollama is advisory-only: evaluates ambiguous merge conflicts
and proposes resolutions. Human approval required.

Usage:
    from apps.ai_assistant.services.sync_advisor import SyncConflictAdvisor

    advisor = SyncConflictAdvisor()
    conflicts = advisor.detect_conflicts(model_name='contact', limit=100)
    resolution = advisor.resolve_conflict(conflict)
"""
from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone

logger = logging.getLogger(__name__)


class SyncConflict:
    """Represents a data conflict between wc3 and wc2 versions of a record."""

    def __init__(
        self,
        model_name: str,
        record_id: int,
        wc3_data: dict[str, Any],
        wc2_data: dict[str, Any],
        conflict_fields: list[str],
    ):
        self.model_name = model_name
        self.record_id = record_id
        self.wc3_data = wc3_data
        self.wc2_data = wc2_data
        self.conflict_fields = conflict_fields
        self.resolution: dict[str, Any] | None = None
        self.resolved_by: str = ""  # "auto", "llm", "human"

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model_name,
            "record_id": self.record_id,
            "conflict_fields": self.conflict_fields,
            "wc3_values": {f: self.wc3_data.get(f) for f in self.conflict_fields},
            "wc2_values": {f: self.wc2_data.get(f) for f in self.conflict_fields},
            "resolution": self.resolution,
            "resolved_by": self.resolved_by,
        }


class SyncConflictAdvisor:
    """Advisory layer for database sync conflicts between wc3 and wc2.

    The actual sync transport is handled by deterministic Celery tasks.
    This service only evaluates and recommends conflict resolutions.
    """

    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm
        self._client = None

    def _get_client(self):
        if self._client is None and self.use_llm:
            from apps.ai_assistant.services.ollama_client import OllamaClient
            self._client = OllamaClient()
        return self._client

    # ── Conflict detection (placeholder for actual sync engine) ────────

    def detect_conflicts(
        self,
        model_name: str,
        wc3_records: list[dict] | None = None,
        wc2_records: list[dict] | None = None,
    ) -> list[SyncConflict]:
        """Detect conflicts between two record sets.

        In production, wc2_records would come from a 4D ODBC/REST bridge.
        For now, this accepts pre-fetched record dicts for comparison.
        """
        if not wc3_records or not wc2_records:
            logger.info("No records provided for sync comparison")
            return []

        # Index wc2 by ID
        wc2_by_id = {r.get("id"): r for r in wc2_records if r.get("id")}

        conflicts = []
        for wc3_rec in wc3_records:
            rec_id = wc3_rec.get("id")
            if rec_id not in wc2_by_id:
                continue  # New record, not a conflict

            wc2_rec = wc2_by_id[rec_id]

            # Compare scalar fields (skip JSON envelopes — handled separately)
            conflict_fields = []
            skip_fields = {"id", "metadata", "refs", "prefs", "comments", "actions",
                           "created_at", "updated_at", "dt_modified", "dt_created"}

            for field in set(wc3_rec.keys()) & set(wc2_rec.keys()):
                if field in skip_fields:
                    continue
                if wc3_rec[field] != wc2_rec[field]:
                    # Both sides have different non-null values
                    if wc3_rec[field] is not None and wc2_rec[field] is not None:
                        conflict_fields.append(field)

            if conflict_fields:
                conflicts.append(SyncConflict(
                    model_name=model_name,
                    record_id=rec_id,
                    wc3_data=wc3_rec,
                    wc2_data=wc2_rec,
                    conflict_fields=conflict_fields,
                ))

        return conflicts

    # ── Deterministic resolution rules ─────────────────────────────────

    def auto_resolve(self, conflict: SyncConflict) -> SyncConflict:
        """Try deterministic resolution before falling back to LLM.

        Rules:
        1. If one side is empty/null and the other has data → take the data
        2. If wc3 version is newer (by metadata timestamp) → prefer wc3
        3. If field is a timestamp → take the more recent one
        """
        resolution = {}

        for field in conflict.conflict_fields:
            wc3_val = conflict.wc3_data.get(field)
            wc2_val = conflict.wc2_data.get(field)

            # Rule 1: One side empty
            if not wc3_val and wc2_val:
                resolution[field] = {"value": wc2_val, "source": "wc2", "reason": "wc3 empty"}
            elif wc3_val and not wc2_val:
                resolution[field] = {"value": wc3_val, "source": "wc3", "reason": "wc2 empty"}
            # Rule 2: Prefer higher row_version
            elif field == "row_version":
                winner = "wc3" if (wc3_val or 0) >= (wc2_val or 0) else "wc2"
                resolution[field] = {
                    "value": wc3_val if winner == "wc3" else wc2_val,
                    "source": winner,
                    "reason": "higher version",
                }
            else:
                # Cannot auto-resolve — needs LLM or human
                resolution[field] = {"value": None, "source": "unresolved", "reason": "ambiguous"}

        # Check if all resolved
        unresolved = [f for f, r in resolution.items() if r["source"] == "unresolved"]

        if unresolved and self.use_llm:
            llm_resolution = self._llm_resolve(conflict, unresolved)
            resolution.update(llm_resolution)

        conflict.resolution = resolution
        conflict.resolved_by = (
            "auto" if not unresolved
            else "llm" if all(resolution[f]["source"] != "unresolved" for f in unresolved)
            else "needs_human"
        )
        return conflict

    # ── LLM resolution ─────────────────────────────────────────────────

    def _llm_resolve(self, conflict: SyncConflict, unresolved_fields: list[str]) -> dict[str, Any]:
        """Ask Ollama to evaluate ambiguous merge conflicts."""
        client = self._get_client()
        if not client:
            return {}

        try:
            field_details = []
            for f in unresolved_fields:
                field_details.append(
                    f"  {f}: wc3='{conflict.wc3_data.get(f)}' vs wc2='{conflict.wc2_data.get(f)}'"
                )

            prompt = (
                f"You are evaluating a data sync conflict for a {conflict.model_name} record (ID: {conflict.record_id}).\n"
                f"Two databases have different values for these fields:\n"
                + "\n".join(field_details)
                + "\n\nFor EACH field, reply with which source to use (wc3 or wc2) and why.\n"
                f"Format: field_name: source (reason)\n"
            )
            response = client.generate(prompt, mode="general")

            # Parse LLM response
            resolution = {}
            for f in unresolved_fields:
                if f"wc3" in response.lower() and f in response:
                    resolution[f] = {
                        "value": conflict.wc3_data.get(f),
                        "source": "wc3",
                        "reason": "LLM recommended wc3",
                    }
                elif "wc2" in response.lower() and f in response:
                    resolution[f] = {
                        "value": conflict.wc2_data.get(f),
                        "source": "wc2",
                        "reason": "LLM recommended wc2",
                    }
                else:
                    resolution[f] = {
                        "value": None,
                        "source": "unresolved",
                        "reason": "LLM could not determine",
                    }

            return resolution

        except Exception as e:
            logger.debug("LLM sync resolution failed: %s", e)
            return {}

    # ── Bulk resolution ────────────────────────────────────────────────

    def resolve_all(self, conflicts: list[SyncConflict]) -> dict[str, Any]:
        """Attempt to resolve all conflicts, returning a summary."""
        auto_resolved = 0
        llm_resolved = 0
        needs_human = 0

        for conflict in conflicts:
            self.auto_resolve(conflict)
            if conflict.resolved_by == "auto":
                auto_resolved += 1
            elif conflict.resolved_by == "llm":
                llm_resolved += 1
            else:
                needs_human += 1

        return {
            "total_conflicts": len(conflicts),
            "auto_resolved": auto_resolved,
            "llm_resolved": llm_resolved,
            "needs_human": needs_human,
            "conflicts": [c.to_dict() for c in conflicts],
        }

    # ── Report ─────────────────────────────────────────────────────────

    def format_report(self, result: dict[str, Any]) -> str:
        """Format sync conflict resolution report as markdown."""
        lines = [
            "# Sync Conflict Resolution Report",
            f"Generated: {timezone.now():%Y-%m-%d %H:%M}",
            "",
            f"**Total conflicts:** {result.get('total_conflicts', 0)}",
            f"**Auto-resolved:** {result.get('auto_resolved', 0)}",
            f"**LLM-resolved:** {result.get('llm_resolved', 0)}",
            f"**Needs human review:** {result.get('needs_human', 0)}",
            "",
        ]

        for conflict in result.get("conflicts", []):
            lines.append(f"### {conflict['model'].title()} #{conflict['record_id']}")
            lines.append(f"Resolved by: **{conflict.get('resolved_by', 'unknown')}**")
            for field in conflict.get("conflict_fields", []):
                res = (conflict.get("resolution") or {}).get(field, {})
                icon = "✅" if res.get("source") != "unresolved" else "❓"
                lines.append(
                    f"- {icon} **{field}**: wc3=`{conflict['wc3_values'].get(field)}` vs "
                    f"wc2=`{conflict['wc2_values'].get(field)}` → {res.get('source', '?')} ({res.get('reason', '')})"
                )
            lines.append("")

        return "\n".join(lines)
