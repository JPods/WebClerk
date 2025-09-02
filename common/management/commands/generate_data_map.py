import os
from django.core.management.base import BaseCommand
from django.apps import apps
from django.conf import settings
from django.db import models

MARKER_START = "<!-- AUTO:MODEL_MAP:START -->"
MARKER_END = "<!-- AUTO:MODEL_MAP:END -->"


def build_model_map() -> str:
    rows = []
    for model in sorted(apps.get_models(), key=lambda m: f"{m._meta.app_label}.{m.__name__}"):
        # Skip Django contrib & migration models
        if model._meta.app_label.startswith("django_") or model._meta.app_label in {"admin", "auth", "contenttypes", "sessions"}:
            continue
        meta = model._meta
        field_names = []
        json_count = 0
        for f in meta.get_fields():
            # Skip reverse relations entirely
            if isinstance(f, (models.ManyToOneRel, models.ManyToManyRel, models.OneToOneRel)):
                continue
            # Real field
            name = getattr(f, "attname", getattr(f, "name", ""))
            if name:
                field_names.append(name)
            if isinstance(f, models.JSONField):
                json_count += 1
        display_fields = ", ".join(field_names[:12]) + (" …" if len(field_names) > 12 else "")
        rows.append(
            f"| {meta.app_label}.{model.__name__} | {meta.db_table} | {len(field_names)} | {json_count} | {display_fields} |"
        )
    header = "| Model | DB Table | Fields | JSON | Sample Field Names |\n|-------|----------|--------|------|-------------------|"
    return header + "\n" + "\n".join(rows)


class Command(BaseCommand):
    help = "Generate (and optionally write) an updated model data map section in docs/data-map.md"

    def add_arguments(self, parser):
        parser.add_argument("--stdout", action="store_true", help="Print only, do not modify file")

    def handle(self, *args, **options):
        content = build_model_map()
        if options["stdout"]:
            self.stdout.write(content)
            return
        docs_path = os.path.join(settings.BASE_DIR, "docs", "data-map.md")
        if not os.path.exists(docs_path):
            self.stderr.write(f"File not found: {docs_path}")
            return
        with open(docs_path, "r", encoding="utf-8") as fh:
            original = fh.read()
        if MARKER_START not in original or MARKER_END not in original:
            self.stderr.write("Markers not found in data-map.md; aborting to avoid destructive overwrite.")
            return
        new_body = []
        inside = False
        for line in original.splitlines():
            if MARKER_START in line:
                inside = True
                new_body.append(line)
                new_body.append("")
                new_body.append(content)
                continue
            if MARKER_END in line:
                inside = False
                new_body.append("")
                new_body.append(line)
                continue
            if inside:
                # skip old auto section lines
                continue
            new_body.append(line)
        updated = "\n".join(new_body).rstrip() + "\n"
        if updated == original:
            self.stdout.write("No changes detected.")
            return
        with open(docs_path, "w", encoding="utf-8") as fh:
            fh.write(updated)
        self.stdout.write("Updated docs/data-map.md model map section.")
