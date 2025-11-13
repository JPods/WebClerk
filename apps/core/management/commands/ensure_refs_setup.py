"""
git
Management command to ensure refs_setup settings exist for all models.
"""

from django.core.management.base import BaseCommand
from django.apps import apps
from apps.core.models.setting import Setting
from apps.core.constants.model_registry import MODEL_REGISTRY

# Define related models that should be denormalized for each model type
RELATED_MODELS_MAP = {
    #QQQ move to setting records at some point
    # Core entities that link to communications
    'contact': ['email', 'phone', 'location', 'domain','customer', 'vendor', 'rep','manufacturer'],
    'customer': ['contact', 'email', 'phone', 'location', 'domain', 'vendor', 'rep', 'manufacturer'],
    'vendor': ['contact', 'email', 'phone', 'location', 'domain','customer', 'rep', 'manufacturer'],
    'org': ['contact', 'email', 'phone', 'location', 'domain'],

    # Transaction headers that link to parties and communications
    'invoice': ['contact', 'customer', 'email', 'phone', 'location','rep', 'manufacturer', 'vendor'],
    'sales_order': ['contact', 'customer', 'email', 'phone', 'location','rep', 'manufacturer', 'vendor'],
    'purchase_order': ['contact', 'vendor', 'email', 'phone', 'location','rep', 'manufacturer', 'vendor'],
    'proposal': ['contact', 'customer', 'email', 'phone', 'location','rep', 'manufacturer', 'vendor'],
    'requisition': ['contact', 'customer', 'email', 'phone', 'location','rep', 'manufacturer', 'vendor'],
    'work_order': ['contact', 'customer', 'vendor', 'email', 'phone', 'location','rep', 'manufacturer', 'vendor'],

    # Transaction lines that inherit from headers
    'invoice_line': ['contact', 'customer', 'email', 'phone', 'location','rep', 'manufacturer', 'vendor'],
    'sales_order_line': ['contact', 'customer', 'email', 'phone', 'location','rep', 'manufacturer', 'vendor'],
    'purchase_order_line': ['contact', 'vendor', 'email', 'phone', 'location','rep', 'manufacturer', 'vendor'],
    'proposal_line': ['contact', 'customer', 'email', 'phone', 'location','rep', 'manufacturer', 'vendor'],
    'requisition_line': ['contact', 'customer', 'email', 'phone', 'location','rep', 'manufacturer', 'vendor'],
    'work_order_line': ['contact', 'customer', 'email', 'phone', 'location','rep', 'manufacturer', 'vendor'],

    # Actions and documents
    'action': ['contact', 'customer', 'vendor', 'email', 'phone', 'location', 'domain'],
    'document': ['contact', 'customer', 'vendor', 'email', 'phone', 'location'],

    # Support entities
    'project': ['contact', 'customer', 'email', 'phone', 'location','rep', 'manufacturer', 'vendor'],
    'notification': ['contact', 'email', 'phone'],

    # Product entities
    'item': ['manufacturer', 'vendor', 'location'],

    # Docs entities
    'document': ['contact', 'customer', 'invoice', 'sales_order', 'purchase_order', 'proposal', 'requisition', 'work_order', 'product'],
    'linkage': ['contact', 'customer', 'invoice', 'sales_order', 'purchase_order', 'proposal', 'requisition', 'work_order', 'product'],
    'question_answer': ['contact', 'customer', 'invoice', 'sales_order', 'purchase_order', 'proposal', 'requisition', 'work_order', 'product'],


}


class Command(BaseCommand):
    help = 'Ensure refs_setup settings exist for all models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Suppress verbose output',
        )
        parser.add_argument(
            '--rebuild',
            action='store_true',
            help='Delete existing refs_setup settings and recreate them',
        )

    def handle(self, *args, **options):
        verbose = not options['quiet']
        rebuild = options['rebuild']

        if rebuild:
            # Delete all existing refs_setup settings
            deleted_count = Setting.objects.filter(purpose='refs_setup').delete()[0]
            if verbose:
                self.stdout.write(f'Deleted {deleted_count} existing refs_setup settings')

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

            # Get character fields for this model
            char_fields = []
            for field in model_class._meta.get_fields():
                if hasattr(field, 'get_internal_type'):
                    field_type = field.get_internal_type()
                    if field_type in ['CharField', 'TextField', 'EmailField', 'URLField']:
                        char_fields.append(field.name)

            # Create priority order for this model's fields
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

            # Add priority orders for related models that should be denormalized
            related_models = RELATED_MODELS_MAP.get(model_key, [])
            for related_model_key in related_models:
                if related_model_key in MODEL_REGISTRY:
                    try:
                        related_model_class = MODEL_REGISTRY[related_model_key].import_model()

                        # Get character fields from related model
                        related_char_fields = []
                        for field in related_model_class._meta.get_fields():
                            if hasattr(field, 'get_internal_type'):
                                field_type = field.get_internal_type()
                                if field_type in ['CharField', 'TextField', 'EmailField', 'URLField']:
                                    related_char_fields.append(field.name)

                        # Add fields from related model with lower priority (offset by 20)
                        for field_name in related_char_fields:
                            for pattern, base_priority in priority_patterns:
                                if pattern in field_name.lower():
                                    priority_order.append({
                                        'model_name': related_model_key,
                                        'field_name': field_name,
                                        'priority': base_priority - 20  # Lower priority for related models
                                    })
                                    break

                    except Exception as e:
                        if verbose:
                            self.stdout.write(
                                self.style.WARNING(f'  - {model_key}: failed to import related model {related_model_key} - {e}')
                            )
                        continue

            # Sort by priority descending
            priority_order.sort(key=lambda x: x['priority'], reverse=True)

            # Create default data structure
            data = {
                'model_name': model_key,
                'priority_order': priority_order  # Will be populated based on common patterns
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