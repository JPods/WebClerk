"""
Ensure all database records have required default structures for JSONB fields.

This command loops through all models inheriting from BaseModel and ensures
that JSON envelope fields (metadata, refs, prefs, comments, actions) have
their required structure. It also handles app-specific JSONB fields like
OrgBase aspects.

IMPORTANT: This command only ADDS missing keys - it never overwrites existing data.

Usage:
    python manage.py ensure_model_defaults
    python manage.py ensure_model_defaults --dry-run
    python manage.py ensure_model_defaults --model=orgbase
    python manage.py ensure_model_defaults --verbose
"""
import json
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction
from django.utils import timezone

from common.models import (
    default_metadata,
    default_refs,
    default_prefs,
    default_comments,
    BaseModel,
)


def deep_merge_defaults(existing: dict | list | None, defaults: dict | list) -> tuple[dict | list, bool]:
    """
    Recursively merge defaults into existing data, only adding missing keys.
    Returns (merged_data, was_modified).
    
    - If existing is None or wrong type, return defaults (modified=True)
    - If existing is a dict, add missing keys from defaults recursively
    - If existing is a list, return as-is (don't modify lists)
    - Never overwrite existing values
    """
    if existing is None:
        return defaults, True
    
    # If defaults is a list, existing should be a list - don't modify lists
    if isinstance(defaults, list):
        if not isinstance(existing, list):
            return defaults, True
        return existing, False
    
    # If defaults is a dict
    if isinstance(defaults, dict):
        if not isinstance(existing, dict):
            return defaults, True
        
        modified = False
        result = dict(existing)  # shallow copy
        
        for key, default_value in defaults.items():
            if key not in result:
                # Key missing entirely - add it
                result[key] = default_value
                modified = True
            elif isinstance(default_value, dict):
                # Recursively merge nested dicts
                merged, was_mod = deep_merge_defaults(result[key], default_value)
                if was_mod:
                    result[key] = merged
                    modified = True
            # If key exists and default is not a dict, leave existing value alone
        
        return result, modified
    
    # For other types, return existing unchanged
    return existing, False


# App-specific default factories
# OrgBase aspects
ORG_ASPECT_DEFAULTS = {
    "contacts": lambda: [],
    "locations": lambda: [],
    "domains": lambda: [],
    "phones": lambda: [],
    "emails": lambda: [],
    "relations": lambda: {"parents": [], "children": [], "linked_ids": []},
    "financial": lambda: {"credit": {}, "balances": {}, "due_buckets": [], "metrics": {}},
    "docs": lambda: [],
    "connections": lambda: {},
    "data": lambda: {},
    "metrics": lambda: {"counts": {}, "periods": {}},
    "gl_accounts": lambda: {},
}


class Command(BaseCommand):
    help = "Ensure all database records have required default structures for JSONB fields"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )
        parser.add_argument(
            '--model',
            type=str,
            help='Only process a specific model (e.g., orgbase, salesorder)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about each record',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limit number of records to process per model (0 = no limit)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        target_model = options.get('model', '').lower() if options.get('model') else None
        verbose = options['verbose']
        limit = options['limit']

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))

        # Get all models
        all_models = apps.get_models()
        
        # Filter to models that inherit from BaseModel (have the JSON fields)
        basemodel_models = []
        for model in all_models:
            # Check if model has BaseModel JSON fields
            has_metadata = hasattr(model, 'metadata')
            has_refs = hasattr(model, 'refs')
            if has_metadata or has_refs:
                basemodel_models.append(model)

        self.stdout.write(f"Found {len(basemodel_models)} models with JSON envelope fields")

        total_updated = 0
        total_skipped = 0

        for model in basemodel_models:
            model_name = model.__name__.lower()
            
            # Filter by target model if specified
            if target_model and model_name != target_model:
                continue

            self.stdout.write(f"\nProcessing {model._meta.label}...")
            
            # Get field names for this model
            field_names = {f.name for f in model._meta.fields}
            
            # Determine which JSON fields exist on this model
            json_fields_to_check = {}
            
            # BaseModel fields
            if 'metadata' in field_names:
                json_fields_to_check['metadata'] = default_metadata
            if 'refs' in field_names:
                json_fields_to_check['refs'] = default_refs
            if 'prefs' in field_names:
                json_fields_to_check['prefs'] = default_prefs
            if 'comments' in field_names:
                json_fields_to_check['comments'] = default_comments
            if 'actions' in field_names:
                json_fields_to_check['actions'] = lambda: {}
            
            # OrgBase specific aspects
            for aspect_name, default_fn in ORG_ASPECT_DEFAULTS.items():
                if aspect_name in field_names:
                    json_fields_to_check[aspect_name] = default_fn

            if not json_fields_to_check:
                self.stdout.write(f"  No JSON fields found, skipping")
                continue

            # Process records
            queryset = model.objects.all()
            if limit > 0:
                queryset = queryset[:limit]
            
            model_updated = 0
            model_skipped = 0

            for obj in queryset.iterator():
                record_modified = False
                changes = []

                for field_name, default_fn in json_fields_to_check.items():
                    current_value = getattr(obj, field_name, None)
                    defaults = default_fn()
                    
                    merged, was_modified = deep_merge_defaults(current_value, defaults)
                    
                    if was_modified:
                        if not dry_run:
                            setattr(obj, field_name, merged)
                        record_modified = True
                        changes.append(field_name)

                if record_modified:
                    if not dry_run:
                        # Save without triggering version bump or other side effects
                        # Use update() to avoid model save() hooks
                        update_fields = {f: getattr(obj, f) for f in changes}
                        model.objects.filter(pk=obj.pk).update(**update_fields)
                    
                    model_updated += 1
                    if verbose:
                        self.stdout.write(f"  Updated {model_name}#{obj.pk}: {', '.join(changes)}")
                else:
                    model_skipped += 1

            total_updated += model_updated
            total_skipped += model_skipped
            
            if model_updated > 0:
                self.stdout.write(self.style.SUCCESS(f"  Updated: {model_updated}, Skipped: {model_skipped}"))
            else:
                self.stdout.write(f"  Updated: {model_updated}, Skipped: {model_skipped}")

        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN COMPLETE - Would update {total_updated} records, {total_skipped} already OK"))
        else:
            self.stdout.write(self.style.SUCCESS(f"COMPLETE - Updated {total_updated} records, {total_skipped} already OK"))
