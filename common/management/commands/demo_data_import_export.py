# python manage.py demo_data_import_export export
# python manage.py demo_data_import_export import

import os      # Standard library for file and path operations
import json    # Standard library for working with JSON data
from django.core.management.base import BaseCommand  # Base class for Django management commands
from django.apps import apps  # Utility to access all registered Django models

class Command(BaseCommand):
    # Help text shown when you run 'python manage.py help demo_data_import_export'
    help = "Export or import all data from all tables as JSON. Usage: python manage.py demo_data_import_export [import|export]"

    def add_arguments(self, parser):
        """Register CLI arguments for the management command."""
        parser.add_argument(
            'action', choices=['export', 'import'], help="Choose 'export' or 'import'."
        )
        parser.add_argument(
            '--path', default=None,
            help='Optional export/import file path (defaults to sibling all_tables_export.json).'
        )
        parser.add_argument(
            '--exclude', default='',
            help='Comma list of extra model labels (app_label.ModelName) to exclude.'
        )
        parser.add_argument(
            '--exclude-lines', action='store_true',
            help='Exclude all models whose class name ends with "Line" (pragmatic skip of line-item tables).'
        )
        parser.add_argument(
            '--settings-path', default=None,
            help='Optional path to a secondary JSON (e.g., settings_data.json) merged ONLY on import after primary import.'
        )
        parser.add_argument(
            '--force-settings', action='store_true',
            help='Force re-import of settings/contacts JSON even if .imported marker exists.'
        )

    def handle(self, *args, **kwargs):
        # Main entry point for the command
        action = kwargs['action']  # 'export' or 'import'
        base_dir = os.path.dirname(__file__)
        filename = kwargs.get('path') or os.path.join(base_dir, 'all_tables_export.json')
        extra_exclude = {m.strip() for m in (kwargs.get('exclude') or '').split(',') if m.strip()}
        exclude_lines = bool(kwargs.get('exclude_lines'))
        settings_path = kwargs.get('settings_path') or os.path.join(base_dir, 'settings_data.json')
        force_settings = bool(kwargs.get('force_settings'))

        if action == 'export':
            self.export_all_data(filename, extra_exclude, exclude_lines)
        elif action == 'import':
            self.delete_all_data(extra_exclude, exclude_lines)
            self.import_all_data(filename, extra_exclude, exclude_lines)
            # Optional auto/explicit second-phase import (settings & contacts etc.)
            if settings_path and os.path.isfile(settings_path):
                marker_path = settings_path + '.imported'
                if os.path.isfile(marker_path) and not force_settings:
                    self.stdout.write("Settings data already imported earlier (marker present). Skipping (use --force-settings to override).")
                else:
                    if force_settings and os.path.isfile(marker_path):
                        self.stdout.write(self.style.WARNING("Forcing re-import of settings data (marker ignored)."))
                    self.stdout.write(getattr(self.style, 'NOTICE', lambda x: x)(f"Merging secondary data from: {settings_path}"))
                    # merge=True for upsert semantics on contacts/settings
                    self.import_all_data(settings_path, extra_exclude, exclude_lines, delete_first=False, merge=True)
                    try:
                        with open(marker_path, 'w') as mf:
                            mf.write('imported')
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Could not write marker file {marker_path}: {e}"))
            else:
                self.stdout.write("No settings_data.json found to merge.")

    def _base_skip_models(self):  # central list for consistency
        return [
            'core.Pending',
            'auth.Permission',
            'contenttypes.ContentType',
            'admin.LogEntry',
            'sessions.Session',  # ephemeral session data not needed in snapshots
            # celery beat scheduling tables
            'django_celery_beat.PeriodicTask',
            'django_celery_beat.CrontabSchedule',
            'django_celery_beat.IntervalSchedule',
            'django_celery_beat.ClockedSchedule',
            'django_celery_beat.SolarSchedule',
            'django_celery_beat.PeriodicTasks',
            # celery results tables
            'django_celery_results.TaskResult',
            'django_celery_results.ChordCounter',
            'django_celery_results.GroupResult',
        ]

    def _augment_with_line_models(self, skip_models, include_line_skip):
        """If include_line_skip is True, add all models whose class name ends with 'Line' plus certain association tables to skip list."""
        if not include_line_skip:
            return skip_models
        added = []
        for model in apps.get_models():
            if model.__name__.endswith('Line'):
                label = f"{model._meta.app_label}.{model.__name__}"
                if label not in skip_models:
                    skip_models.add(label)
                    added.append(label)
        # Also skip ProjectAssociation because regenerated Project PKs break references; can be reseeded later
        for model in apps.get_models():
            if model.__name__ == 'ProjectAssociation':
                label = f"{model._meta.app_label}.{model.__name__}"
                if label not in skip_models:
                    skip_models.add(label)
                    added.append(label)
        if added:
            self.stdout.write(self.style.WARNING(f"Skipping line models (--exclude-lines): {', '.join(sorted(added))}"))
        return skip_models

    def export_all_data(self, filename, extra_exclude, exclude_lines=False):
        """Export all fields from all tables to a JSON file."""
        skip_models = set(self._base_skip_models()) | set(extra_exclude)
        skip_models = self._augment_with_line_models(skip_models, exclude_lines)
        all_data = {}  # Dictionary to hold all exported data
        for model in apps.get_models():  # Loop through all Django models
            model_name = f"{model._meta.app_label}.{model.__name__}"
            if model_name in skip_models:
                continue
            self.stdout.write(f"Exporting table: {model_name}")
            rows = []
            rel_fields = []
            for f in model._meta.fields:
                if f.is_relation and f.many_to_one:
                    rel_fields.append(f)
            for obj in model.objects.all():
                row = {}
                for f in model._meta.fields:
                    if f.is_relation and f.many_to_one:
                        # Use underlying *_id (attname) raw value to ensure import consistency
                        row[f.name] = getattr(obj, f.attname)
                    else:
                        row[f.name] = getattr(obj, f.name)
                rows.append(row)
            all_data[model_name] = rows
        # Write the all_data dictionary to the JSON file
        with open(filename, 'w') as f:
            json.dump(all_data, f, default=str, indent=4)
        self.stdout.write(f"Export completed: {filename}")  # Print completion message

    def delete_all_data(self, extra_exclude, exclude_lines=False):
        """Delete all data from all tables (except skip list)."""
        skip_models = set(self._base_skip_models()) | set(extra_exclude)
        skip_models = self._augment_with_line_models(skip_models, exclude_lines)
        for model in apps.get_models():
            model_name = f"{model._meta.app_label}.{model.__name__}"
            if model_name in skip_models:
                continue
            model.objects.all().delete()

    def import_all_data(self, filename, extra_exclude, exclude_lines=False, delete_first=True, merge=False):
        """Import all fields into all tables from a JSON file.

        Pragmatic mode: primary keys and uuids in the source snapshot are ignored; new ones are generated.
        This avoids complexities around ordering and related object availability. Line-item models can be
        excluded with --exclude-lines to sidestep parent dependency save logic.
        """
        skip_models = set(self._base_skip_models()) | set(extra_exclude)
        skip_models = self._augment_with_line_models(skip_models, exclude_lines)
        with open(filename, 'r') as f:
            all_data = json.load(f)
        # If this phase requested a pre-delete, perform targeted deletes (not full) for models included in file
        if delete_first:
            for model in apps.get_models():
                model_name = f"{model._meta.app_label}.{model.__name__}"
                if model_name in skip_models:
                    continue
                if model_name in all_data:
                    model.objects.all().delete()
        merge_config = {
            'core.Contact': ['email'],
            'core.Setting': ['name', 'purpose', 'table_name'],  # logical composite key
        }
        for model in apps.get_models():
            model_name = f"{model._meta.app_label}.{model.__name__}"
            if model_name in skip_models:
                continue
            self.stdout.write(f"Importing table: {model_name}")
            objects = all_data.get(model_name, [])
            for obj_data in objects:
                # Resolve FK relations (best effort). If target not yet imported, leave as None.
                for field in model._meta.fields:
                    if field.is_relation and field.many_to_one and field.name in obj_data:
                        rel_model = field.related_model
                        rel_value = obj_data[field.name]
                        if rel_value is not None:
                            resolved = None
                            try:
                                resolved = rel_model.objects.get(pk=rel_value)
                            except Exception:
                                if isinstance(rel_value, str) and hasattr(rel_model, 'uuid'):
                                    try:
                                        resolved = rel_model.objects.get(uuid=rel_value)
                                    except Exception:
                                        resolved = None
                            obj_data[field.name] = resolved
                # Drop original PK so a new one is assigned
                pk_field = model._meta.pk
                if pk_field is not None:
                    obj_data.pop(pk_field.name, None)
                # Remove common uuid field if present (will regenerate if auto or default)
                if 'uuid' in obj_data:
                    obj_data.pop('uuid')
                # Prune any keys not actual model fields (secondary snapshots may carry extra convenience fields)
                allowed_fields = {f.name for f in model._meta.fields}
                drop_keys = [k for k in list(obj_data.keys()) if k not in allowed_fields]
                if drop_keys:
                    for k in drop_keys:
                        obj_data.pop(k, None)
                if merge and model_name in merge_config:
                    key_fields = merge_config[model_name]
                    lookup = {k: obj_data.get(k) for k in key_fields if obj_data.get(k) is not None}
                    instance = None
                    if lookup and len(lookup) == len(key_fields):
                        try:
                            instance = model.objects.get(**lookup)
                        except model.DoesNotExist:
                            instance = None
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f"Lookup error for {model_name}: {e}"))
                    if instance:
                        for k, v in obj_data.items():
                            if k in key_fields:
                                continue
                            try:
                                setattr(instance, k, v)
                            except Exception:
                                pass
                        try:
                            instance.save()
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"Failed updating {model_name}: {e}"))
                        continue
                try:
                    model.objects.create(**obj_data)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed creating {model_name}: {e}"))
        self.stdout.write(f"Import completed (PKs regenerated): {filename}")