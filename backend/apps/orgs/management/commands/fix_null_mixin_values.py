"""
Replace null numerical values with zero in org JSONB mixin fields.

Walks the financial, stats, relationship_stats, metrics, and metadata
JSONB fields on every OrgBase record.  For each leaf whose default is a
number (int or float), if the stored value is None/null it is set to 0.

Usage:
    python manage.py fix_null_mixin_values
    python manage.py fix_null_mixin_values --dry-run
    python manage.py fix_null_mixin_values --org-id 42
    python manage.py fix_null_mixin_values --field financial
"""
from __future__ import annotations

import copy
from django.core.management.base import BaseCommand
from apps.orgs.models import OrgBase
from apps.orgs.models.constants import (
    default_financial,
    default_metrics,
)
from common.stats_mixin import default_stats
from common.relationship_stats_mixin import default_relationship_stats
from common.models import default_metadata


# ── helpers ──────────────────────────────────────────────────────────────

def nulls_to_zero(data: dict | list | None, defaults: dict | list | None) -> tuple[dict | list, int]:
    """Recursively replace None values with 0 where the default is numeric.

    Returns (cleaned_data, fix_count).

    Strategy:
      • If *defaults* is a dict we walk each key.
        – If the default value for a key is int/float and the stored value is
          None, replace with 0.
        – If the default value is a dict/list, recurse.
      • If *defaults* is a list we skip (list items are dynamic records like
        contacts/addresses — no fixed numeric leaf schema).
      • Keys that exist in data but NOT in defaults are left untouched —
        this handles dynamic sub-keys in stats.counts, metrics.periods, etc.
    """
    if data is None:
        data = copy.deepcopy(defaults) if defaults is not None else {}
        # Count every numeric leaf that was implicitly null and is now 0
        count = _count_numeric_leaves(data)
        return data, count

    if not isinstance(defaults, dict) or not isinstance(data, dict):
        return data, 0

    fixes = 0
    for key, default_val in defaults.items():
        if key not in data:
            # Key missing entirely — backfill from defaults if numeric or nested
            if isinstance(default_val, (int, float)):
                data[key] = 0
                fixes += 1
            elif isinstance(default_val, dict):
                data[key] = copy.deepcopy(default_val)
                fixes += _count_numeric_leaves(default_val)
            continue

        stored = data[key]

        if isinstance(default_val, (int, float)):
            if stored is None:
                data[key] = 0
                fixes += 1
        elif isinstance(default_val, dict):
            sub, sub_fixes = nulls_to_zero(stored, default_val)
            data[key] = sub
            fixes += sub_fixes
        # lists / strings / bools → leave as-is

    # Also walk data keys not in defaults for nested dicts whose leaves are
    # null numerics.  This covers dynamic buckets like stats.counts where
    # the defaults dict is empty but runtime keys carry int values.
    for key in data:
        if key in defaults:
            continue
        val = data[key]
        if val is None:
            # Dynamic key with null — could be numeric.  Default to 0.
            data[key] = 0
            fixes += 1
        elif isinstance(val, dict):
            sub, sub_fixes = _fix_dynamic_nulls(val)
            data[key] = sub
            fixes += sub_fixes

    return data, fixes


def _fix_dynamic_nulls(data: dict) -> tuple[dict, int]:
    """Fix nulls in dict subtrees that have no schema defaults (dynamic keys)."""
    fixes = 0
    for key, val in list(data.items()):
        if val is None:
            data[key] = 0
            fixes += 1
        elif isinstance(val, dict):
            sub, sub_fixes = _fix_dynamic_nulls(val)
            data[key] = sub
            fixes += sub_fixes
    return data, fixes


def _count_numeric_leaves(d) -> int:
    """Count numeric leaf values in a nested dict."""
    if isinstance(d, (int, float)):
        return 1
    if isinstance(d, dict):
        return sum(_count_numeric_leaves(v) for v in d.values())
    if isinstance(d, list):
        return sum(_count_numeric_leaves(v) for v in d)
    return 0


# The JSONB fields we clean and their respective default factories.
FIELD_DEFAULTS = {
    "financial": default_financial,
    "stats": default_stats,
    "relationship_stats": default_relationship_stats,
    "metrics": default_metrics,
    "metadata": default_metadata,
}


class Command(BaseCommand):
    help = "Replace null numerical values with zero in org JSONB mixin fields"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without saving",
        )
        parser.add_argument(
            "--org-id",
            type=int,
            help="Fix a single org by ID",
        )
        parser.add_argument(
            "--field",
            choices=list(FIELD_DEFAULTS.keys()),
            help="Limit to a single JSONB field (default: all)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        org_id = options.get("org_id")
        field_filter = options.get("field")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be saved"))

        qs = OrgBase.objects.all()
        if org_id:
            qs = qs.filter(id=org_id)

        total = qs.count()
        updated = 0
        skipped = 0
        errors = 0
        total_fixes = 0
        per_field_fixes: dict[str, int] = {f: 0 for f in FIELD_DEFAULTS}

        fields_to_check = {field_filter: FIELD_DEFAULTS[field_filter]} if field_filter else FIELD_DEFAULTS

        self.stdout.write(f"Processing {total} org(s) across field(s): {', '.join(fields_to_check)}...")

        for org in qs.iterator():
            try:
                org_fixes = 0
                dirty_fields: list[str] = []

                for field_name, default_fn in fields_to_check.items():
                    raw = getattr(org, field_name)
                    defaults = default_fn()
                    cleaned, fixes = nulls_to_zero(
                        copy.deepcopy(raw) if raw is not None else None,
                        defaults,
                    )
                    if fixes:
                        setattr(org, field_name, cleaned)
                        dirty_fields.append(field_name)
                        org_fixes += fixes
                        per_field_fixes[field_name] += fixes

                if org_fixes:
                    if dry_run:
                        self.stdout.write(
                            f"  Org {org.id} ({org.display_name}): "
                            f"{org_fixes} null(s) → 0 in {', '.join(dirty_fields)}"
                        )
                    else:
                        org.save(update_fields=dirty_fields + ["dt_modified"])
                    updated += 1
                    total_fixes += org_fixes
                else:
                    skipped += 1

            except Exception as exc:
                errors += 1
                self.stderr.write(self.style.ERROR(f"Error on org {org.id}: {exc}"))

        # ── Summary ──────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Done."))
        self.stdout.write(f"  Total orgs:    {total}")
        self.stdout.write(f"  Updated:       {updated}")
        self.stdout.write(f"  Skipped:       {skipped} (no nulls found)")
        self.stdout.write(f"  Errors:        {errors}")
        self.stdout.write(f"  Nulls fixed:   {total_fixes}")
        for fname, count in per_field_fixes.items():
            if count:
                self.stdout.write(f"    {fname}: {count}")

        if dry_run:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Run without --dry-run to apply changes"))
