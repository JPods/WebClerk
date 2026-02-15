"""Generate TypeScript interfaces from Django model _meta.

Reads WCAPI_BLESSED_MODELS from settings and produces TypeScript
interfaces for each model, matching the r25 per-model type pattern:

  - {Model}Record     — full record shape (all fields)
  - Create{Model}Request  — writable fields only
  - Update{Model}Request  — writable fields + id

Usage:
  # Print to stdout
  python manage.py generate_ts_types

  # Write to file (default: React2025 generated types)
  python manage.py generate_ts_types --out ../React2025/src/generated/modelTypes.ts

  # Single model
  python manage.py generate_ts_types --model customer

  # List available models
  python manage.py generate_ts_types --list
"""
from __future__ import annotations

import os
import re
import textwrap
from collections import defaultdict
from datetime import datetime
from typing import Any

from django.apps import apps as django_apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import models


# ── Alias map for WCAPI_BLESSED_MODELS entries whose class name ──
# ── doesn't match the actual Django model class name.          ──
MODEL_ALIASES: dict[str, str] = {
    "core.Audit": "core.AuditLog",
    "transactions.SalesOrder": "transactions.Order",
    "transactions.SalesOrderLine": "transactions.OrderLine",
    "transactions.PurchaseOrder": "transactions.Purchase",
    "transactions.PurchaseOrderLine": "transactions.PurchaseLine",
    "transactions.PurchaseReceipt": "transactions.Receipt",
    "transactions.ProjectLinks": "transactions.Project",  # no separate model
    "docs.Linkage": "docs.LinkageEntry",
}


# ── Django field → TypeScript type mapping ──────────────────────────
FIELD_TYPE_MAP: dict[type, str] = {
    models.AutoField: "number",
    models.SmallAutoField: "number",
    models.BigAutoField: "number",
    models.SmallIntegerField: "number",
    models.IntegerField: "number",
    models.BigIntegerField: "number",
    models.PositiveIntegerField: "number",
    models.PositiveSmallIntegerField: "number",
    models.PositiveBigIntegerField: "number",
    models.FloatField: "number",
    models.DecimalField: "number | string",
    models.CharField: "string",
    models.TextField: "string",
    models.SlugField: "string",
    models.EmailField: "string",
    models.URLField: "string",
    models.FilePathField: "string",
    models.FileField: "string",
    models.ImageField: "string",
    models.UUIDField: "string",
    models.IPAddressField: "string",
    models.GenericIPAddressField: "string",
    models.BooleanField: "boolean",
    models.NullBooleanField: "boolean | null",
    models.DateField: "string",
    models.DateTimeField: "string",
    models.TimeField: "string",
    models.DurationField: "string",
    models.BinaryField: "string",
    models.JSONField: "Record<string, any>",
}

# Fields that are always read-only (system-managed)
READONLY_FIELDS = frozenset({
    "id", "pk", "uuid", "dt_created", "dt_modified", "dt_joined",
    "version", "last_login", "date_joined",
    "password",  # never exposed
})

# Fields to skip entirely (internal Django / BaseModel plumbing)
SKIP_FIELDS = frozenset({
    "password", "logentry", "groups", "user_permissions",
})

# Fields to exclude from Create/Update requests (system-managed JSONB envelopes
# and internal flags that should only be set by backend logic)
SYSTEM_ONLY_FIELDS = frozenset({
    "refs", "metadata", "prefs", "comments", "actions",
    "is_deleted", "is_archived",
    "dt_created", "dt_modified", "dt_joined",
    "version", "last_login", "date_joined",
    "health_rating", "security_level",
    "stats", "relationship_stats",
})


def _ts_type_for_field(field: models.Field) -> str:
    """Return the TypeScript type string for a Django model field."""
    # FK / OneToOne → number (the _id raw value)
    if isinstance(field, (models.ForeignKey, models.OneToOneField)):
        return "number | null"

    # M2M → array of numbers
    if isinstance(field, models.ManyToManyField):
        return "number[]"

    # JSONField subclass check (postgres ArrayField wraps JSONField)
    if isinstance(field, models.JSONField):
        return "Record<string, any>"

    # Walk MRO to find the closest match
    for cls in type(field).__mro__:
        if cls in FIELD_TYPE_MAP:
            ts = FIELD_TYPE_MAP[cls]
            if field.null and ts not in ("boolean",):
                return f"{ts} | null"
            return ts

    return "any"


def _ts_field_name(field: models.Field) -> str:
    """Return the TypeScript property name for a field.

    For FKs: use the attname (e.g. customer_id) so the frontend sends
    the raw integer, matching WCAPI's save payload convention.
    """
    if isinstance(field, (models.ForeignKey, models.OneToOneField)):
        return field.attname  # e.g. customer_id
    return field.name


def _pascal(snake: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in snake.split("_"))


def _gather_fields(model: type[models.Model]) -> list[dict[str, Any]]:
    """Gather field metadata for a model."""
    results = []
    for field in model._meta.get_fields():
        # Skip reverse relations and M2M through tables
        if field.is_relation and not field.concrete:
            continue
        if field.many_to_many:
            continue

        name = _ts_field_name(field)
        if name in SKIP_FIELDS:
            continue

        ts_type = _ts_type_for_field(field)
        readonly = name in READONLY_FIELDS or not getattr(field, "editable", True)
        required = not getattr(field, "blank", False) and not getattr(field, "null", False)
        has_default = getattr(field, "has_default", lambda: False)()

        # FK fields are nullable when blank/null on the FK
        if isinstance(field, (models.ForeignKey, models.OneToOneField)):
            required = not field.blank and not field.null

        comment_parts = []
        if isinstance(field, (models.ForeignKey, models.OneToOneField)):
            related_model = field.related_model
            if related_model:
                comment_parts.append(f"FK → {related_model._meta.label}")
        if getattr(field, "choices", None):
            choice_vals = [str(c[0]) for c in field.choices[:8]]
            comment_parts.append(f"choices: {', '.join(choice_vals)}")
        if readonly:
            comment_parts.append("read-only")
        if getattr(field, "max_length", None):
            comment_parts.append(f"max_length={field.max_length}")

        # Mark system-only fields (read in Record, excluded from Create/Update)
        system_only = name in SYSTEM_ONLY_FIELDS or readonly

        results.append({
            "name": name,
            "ts_type": ts_type,
            "required": required,
            "readonly": readonly,
            "system_only": system_only,
            "has_default": has_default,
            "comment": " | ".join(comment_parts) if comment_parts else "",
        })

    # Sort: id/uuid first, then alphabetical
    priority = {"id": 0, "uuid": 1, "ida": 2}
    results.sort(key=lambda f: (priority.get(f["name"], 10), f["name"]))
    return results


def _generate_interfaces(
    model_name: str,
    model: type[models.Model],
) -> str:
    """Generate TypeScript interfaces for a single model."""
    fields = _gather_fields(model)
    pascal = _pascal(model_name)
    lines: list[str] = []

    # Header comment
    lines.append(f"// ── {pascal} ──")
    lines.append(f"// Django: {model._meta.label}  table: {model._meta.db_table}")
    lines.append(f"// wcapi model_name: \"{model_name}\"")
    lines.append("")

    # ── Record interface (full shape incl. read-only) ──
    lines.append(f"export interface {pascal}Record {{")
    for f in fields:
        optional = "?" if not f["required"] else ""
        comment = f"  // {f['comment']}" if f["comment"] else ""
        lines.append(f"  {f['name']}{optional}: {f['ts_type']};{comment}")
    lines.append("}")
    lines.append("")

    # ── CreateRequest (writable fields, omit read-only and system-only) ──
    writable = [f for f in fields if not f["system_only"]]
    lines.append(f"export interface Create{pascal}Request {{")
    for f in writable:
        # For create, fields with defaults are optional
        optional = "?" if not f["required"] or f["has_default"] else ""
        comment = f"  // {f['comment']}" if f["comment"] else ""
        lines.append(f"  {f['name']}{optional}: {f['ts_type']};{comment}")
    lines.append("}")
    lines.append("")

    # ── UpdateRequest (writable + id, all optional except id) ──
    lines.append(f"export interface Update{pascal}Request {{")
    lines.append("  id: number | string;")
    for f in writable:
        if f["name"] == "id":
            continue
        comment = f"  // {f['comment']}" if f["comment"] else ""
        lines.append(f"  {f['name']}?: {f['ts_type']};{comment}")
    lines.append("}")
    lines.append("")

    return "\n".join(lines)


class Command(BaseCommand):
    help = "Generate TypeScript interfaces from WCAPI_BLESSED_MODELS"

    def add_arguments(self, parser):
        parser.add_argument(
            "--out", "-o",
            type=str,
            default="",
            help="Output file path. Empty = stdout.",
        )
        parser.add_argument(
            "--model", "-m",
            type=str,
            default="",
            help="Generate for a single model_name only.",
        )
        parser.add_argument(
            "--list", "-l",
            action="store_true",
            help="List available model names and exit.",
        )
        parser.add_argument(
            "--app",
            type=str,
            default="",
            help="Generate for all models in a specific app (e.g. 'orgs').",
        )

    def handle(self, **options):
        blessed: dict[str, str] = getattr(settings, "WCAPI_BLESSED_MODELS", {})
        if not blessed:
            raise CommandError("WCAPI_BLESSED_MODELS not found in settings.")

        # ── List mode ──
        if options["list"]:
            self.stdout.write("Available model names:\n")
            by_app: dict[str, list[str]] = defaultdict(list)
            for key, path in sorted(blessed.items()):
                app = path.split(".")[0]
                by_app[app].append(key)
            for app, keys in sorted(by_app.items()):
                self.stdout.write(f"\n  {app}:")
                for k in keys:
                    self.stdout.write(f"    {k}")
            return

        # ── Resolve models ──
        targets: dict[str, type[models.Model]] = {}
        seen_models: set[str] = set()  # dedupe by model class label

        for key, path in sorted(blessed.items()):
            if options["model"] and key != options["model"]:
                continue
            if options["app"] and not path.startswith(options["app"] + "."):
                continue

            app_label, model_name = path.rsplit(".", 1)
            try:
                model_cls = django_apps.get_model(app_label, model_name)
            except LookupError:
                # Try alias map
                alias = MODEL_ALIASES.get(path)
                if alias:
                    a_app, a_model = alias.rsplit(".", 1)
                    try:
                        model_cls = django_apps.get_model(a_app, a_model)
                    except LookupError:
                        self.stderr.write(f"  ⚠ {key}: model {path} (alias {alias}) not found, skipping")
                        continue
                else:
                    self.stderr.write(f"  ⚠ {key}: model {path} not found, skipping")
                    continue

            # Dedupe: proxy models (Customer, Vendor, etc.) share the same
            # table as OrgBase — generate once under each wcapi name but
            # using the same meta.
            label = model_cls._meta.label
            if label in seen_models and model_cls._meta.proxy:
                # For proxies, still generate (different model_name) but note it
                pass
            seen_models.add(label)
            targets[key] = model_cls

        if not targets:
            raise CommandError("No matching models found.")

        # ── Generate ──
        # Group by app for output ordering
        by_app: dict[str, list[tuple[str, type[models.Model]]]] = defaultdict(list)
        for key, model_cls in targets.items():
            app = model_cls._meta.app_label
            by_app[app].append((key, model_cls))

        sections: list[str] = []

        # File header
        header = textwrap.dedent(f"""\
            /**
             * AUTO-GENERATED — DO NOT EDIT
             *
             * TypeScript interfaces generated from Django model definitions.
             * Source: webClerk3 WCAPI_BLESSED_MODELS
             * Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
             *
             * Regenerate with:
             *   cd webClerk3 && python manage.py generate_ts_types \\
             *     --out ../React2025/src/generated/modelTypes.ts
             */

            /* eslint-disable @typescript-eslint/no-explicit-any */
        """)
        sections.append(header)

        for app_label in sorted(by_app.keys()):
            sections.append(f"// {'=' * 60}")
            sections.append(f"// {app_label.upper()}")
            sections.append(f"// {'=' * 60}\n")
            for key, model_cls in sorted(by_app[app_label]):
                sections.append(_generate_interfaces(key, model_cls))

        output = "\n".join(sections)

        # ── Write ──
        out_path = options["out"]
        if out_path:
            # Resolve relative to project root
            if not os.path.isabs(out_path):
                out_path = os.path.join(settings.BASE_DIR, out_path)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w") as f:
                f.write(output)
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Generated {len(targets)} model interfaces → {out_path}"
                )
            )
        else:
            self.stdout.write(output)

        # Summary
        self.stderr.write(
            f"\n  Models: {len(targets)}  |  Apps: {len(by_app)}"
        )
