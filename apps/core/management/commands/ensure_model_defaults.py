"""
Ensure all database records have required default structures for JSONB fields.

This command loops through all models inheriting from BaseModel and ensures
that JSON envelope fields have their required structure using the
JSON_DEFAULT_FACTORIES pattern defined on each model class.

The command collects factories from the entire class hierarchy (via MRO),
so transaction models get their transaction-specific defaults automatically.

IMPORTANT: This command only ADDS missing keys - it never overwrites existing data.

Usage:
    python manage.py ensure_model_defaults
    python manage.py ensure_model_defaults --dry-run
    python manage.py ensure_model_defaults --model=salesorder
    python manage.py ensure_model_defaults --verbose
    python manage.py ensure_model_defaults --batch-size=500

See: readmes/topics/models/json-default-factories.md
"""
from django.core.management.base import BaseCommand
from django.apps import apps

from common.models import BaseModel


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


def collect_json_factories_for_model(model_class):
    """
    Collect JSON_DEFAULT_FACTORIES from the model's MRO.
    Returns dict mapping field_name -> factory_function.
    
    Works like BaseModel._collect_json_default_factories() but at class level.
    """
    factories = {}
    # Walk MRO in reverse so child classes override parent factories
    for cls in reversed(model_class.__mro__):
        class_factories = getattr(cls, 'JSON_DEFAULT_FACTORIES', None)
        if class_factories and isinstance(class_factories, dict):
            factories.update(class_factories)
    return factories


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
            help='Only process a specific model (e.g., salesorder, invoice)',
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
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of records to process before committing (default: 1000)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        target_model = options.get('model', '').lower() if options.get('model') else None
        verbose = options['verbose']
        limit = options['limit']
        batch_size = options['batch_size']

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))

        # Get all models that inherit from BaseModel
        all_models = apps.get_models()
        basemodel_models = [m for m in all_models if issubclass(m, BaseModel) and not m._meta.abstract]

        self.stdout.write(f"Found {len(basemodel_models)} concrete models inheriting from BaseModel")

        total_updated = 0
        total_skipped = 0

        for model in basemodel_models:
            model_name = model.__name__.lower()
            
            # Filter by target model if specified
            if target_model and model_name != target_model:
                continue

            # Collect JSON_DEFAULT_FACTORIES from MRO
            json_factories = collect_json_factories_for_model(model)
            
            # Filter to only fields that exist on this model
            field_names = {f.name for f in model._meta.fields}
            json_factories = {k: v for k, v in json_factories.items() if k in field_names}

            if not json_factories:
                if verbose:
                    self.stdout.write(f"Skipping {model._meta.label} - no JSON factories")
                continue

            self.stdout.write(f"\nProcessing {model._meta.label}...")
            self.stdout.write(f"  Fields: {', '.join(sorted(json_factories.keys()))}")

            # Process records
            queryset = model.objects.all()
            if limit > 0:
                queryset = queryset[:limit]
            
            model_updated = 0
            model_skipped = 0
            batch_updates = []

            for obj in queryset.iterator():
                record_modified = False
                changes = []
                update_data = {}

                for field_name, factory in json_factories.items():
                    current_value = getattr(obj, field_name, None)
                    defaults = factory()
                    
                    merged, was_modified = deep_merge_defaults(current_value, defaults)
                    
                    if was_modified:
                        update_data[field_name] = merged
                        record_modified = True
                        changes.append(field_name)

                if record_modified:
                    model_updated += 1
                    if verbose:
                        self.stdout.write(f"  Will update {model_name}#{obj.pk}: {', '.join(changes)}")
                    
                    if not dry_run:
                        # Batch the updates for efficiency
                        batch_updates.append((obj.pk, update_data))
                        
                        # Commit batch
                        if len(batch_updates) >= batch_size:
                            self._apply_batch(model, batch_updates)
                            batch_updates = []
                else:
                    model_skipped += 1

            # Apply remaining batch
            if batch_updates and not dry_run:
                self._apply_batch(model, batch_updates)

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

    def _apply_batch(self, model, batch_updates):
        """Apply a batch of updates using individual update() calls to avoid save() hooks."""
        for pk, update_data in batch_updates:
            model.objects.filter(pk=pk).update(**update_data)
