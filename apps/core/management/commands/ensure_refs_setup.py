"""
Management command to ensure refs_setup settings exist for all models.
"""

from django.core.management.base import BaseCommand
from django.apps import apps
from apps.core.models.setting import Setting
from apps.core.constants.model_registry import MODEL_REGISTRY


class Command(BaseCommand):
    help = 'Ensure refs_setup settings exist for all models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Suppress verbose output',
        )

    def handle(self, *args, **options):
        verbose = not options['quiet']

        if verbose:
            self.stdout.write('Ensuring refs_setup settings exist for all models...')

        created_count = 0
        existing_count = 0

        for model_key, meta in MODEL_REGISTRY.items():
            # Check if refs_setup setting already exists
            existing = Setting.objects.filter(
                model_name=model_key,
                purpose='refs_setup'
            ).first()

            if existing:
                existing_count += 1
                if verbose:
                    self.stdout.write(f'  - {model_key}: already exists')
                continue

            # Get the model class
            try:
                model_class = meta.import_model()
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'  - {model_key}: failed to import model - {e}')
                )
                continue

            # Get character fields
            char_fields = []
            for field in model_class._meta.get_fields():
                if hasattr(field, 'get_internal_type'):
                    field_type = field.get_internal_type()
                    if field_type in ['CharField', 'TextField', 'EmailField', 'URLField']:
                        char_fields.append(field.name)

            # Create priority order based on common naming patterns
            priority_order = []
            priority_patterns = [
                ('name_first', 10),
                ('name_last', 9),
                ('company', 8),
                ('name', 7),
                ('title', 6),
                ('description', 5),
                ('email', 4),
                ('phone', 3),
                ('address', 2),
            ]

            for field_name in char_fields:
                for pattern, priority in priority_patterns:
                    if pattern in field_name.lower():
                        priority_order.append({
                            'model_name': model_key,
                            'field_name': field_name,
                            'priority': priority
                        })
                        break
            # Sort by priority descending
            priority_order.sort(key=lambda x: x['priority'], reverse=True)

            # Create default data structure
            data = {
                'fields': char_fields,
                'priority_order': []  # Will be populated based on common patterns
            }

            # Create the setting
            setting = Setting(
                name=f'{model_key} refs setup',
                purpose='refs_setup',
                model_name=model_key,
                data=data
            )

            try:
                setting.save()
                created_count += 1
                if verbose:
                    self.stdout.write(f'  - {model_key}: created with {len(char_fields)} fields')
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  - {model_key}: failed to create setting - {e}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Completed: {created_count} created, {existing_count} already existed'
            )
        )

        return 0