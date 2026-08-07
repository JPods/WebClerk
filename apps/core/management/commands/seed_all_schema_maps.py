"""Seed schema_map Setting records for all registered models.

Creates a simple schema_map Setting for every model in MODEL_REGISTRY
that doesn't already have one. Complex models (contact, item, serial,
payment) already have custom schemas -- this seeds the simple ones.

Also creates template Pydantic schema files in common/schemas/ for
models that don't have one yet.

Usage:
    python manage.py seed_all_schema_maps
    python manage.py seed_all_schema_maps --force  # overwrite existing
    python manage.py seed_all_schema_maps --dry-run  # report only
"""
import os
from pathlib import Path
from django.core.management.base import BaseCommand
from apps.core.models import Setting
from apps.core.constants.model_registry import MODEL_REGISTRY


# Models that already have custom Pydantic schemas -- don't overwrite
CUSTOM_SCHEMA_MODELS = {
    'contact', 'customer', 'item', 'serial', 'payment', 'transaction',
}

SCHEMA_TEMPLATE = '''"""
Pydantic schemas for {title} JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# -- .config ----------------------------------------------------------------

class {class_name}Config(BaseModel):
    class Config:
        extra = "allow"


# -- .metadata (inherits MetadataBase) --------------------------------------

class {class_name}Metadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class {class_name}Prefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class {class_name}Refs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None
'''


def to_class_name(key: str) -> str:
    """Convert model key to PascalCase class name."""
    return ''.join(word.capitalize() for word in key.split('_'))


class Command(BaseCommand):
    help = "Seed schema_map Setting records for all registered models"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Overwrite existing Settings")
        parser.add_argument("--dry-run", action="store_true", help="Report only, don't create")

    def handle(self, *args, **options):
        force = options["force"]
        dry_run = options["dry_run"]

        existing = set(
            Setting.objects.filter(purpose="schema_map", is_active=True)
            .values_list("parent_model", flat=True)
        )

        schemas_dir = Path(__file__).resolve().parents[4] / "common" / "schemas"
        created_settings = 0
        created_schemas = 0
        skipped = 0

        for key, meta in sorted(MODEL_REGISTRY.items()):
            # Skip if Setting already exists (unless force)
            if key in existing and not force:
                skipped += 1
                continue

            class_name = to_class_name(key)
            schema_module = f"common.schemas.{key}"
            schema_file = schemas_dir / f"{key}.py"

            # Create Pydantic schema file if it doesn't exist
            if not schema_file.exists() and key not in CUSTOM_SCHEMA_MODELS:
                if dry_run:
                    self.stdout.write(f"  Would create schema: {schema_file.name}")
                else:
                    schema_file.write_text(
                        SCHEMA_TEMPLATE.format(
                            title=meta.singular,
                            class_name=class_name,
                        )
                    )
                    created_schemas += 1

            # Determine schema module -- use existing if custom, else generated
            if key in CUSTOM_SCHEMA_MODELS:
                schema_module = f"common.schemas.{key}"

            config = {
                "pydantic_schema": schema_module,
                "config_schema": f"{class_name}Config",
                "metadata_schema": f"{class_name}Metadata",
                "prefs_schema": f"{class_name}Prefs",
                "refs_schema": f"{class_name}Refs",
            }

            if dry_run:
                self.stdout.write(f"  Would seed Setting: {key}")
                created_settings += 1
                continue

            if key in existing and force:
                Setting.objects.filter(
                    parent_model=key, purpose="schema_map", is_active=True
                ).update(config=config, name=f"{meta.singular} schema")
            else:
                Setting.objects.create(
                    name=f"{meta.singular} schema",
                    parent_model=key,
                    purpose="schema_map",
                    scope="system",
                    config=config,
                )
            created_settings += 1

        action = "Would create" if dry_run else "Created"
        self.stdout.write(
            f"{action} {created_settings} Setting(s), "
            f"{created_schemas} schema file(s). "
            f"Skipped {skipped} (already exist)."
        )
