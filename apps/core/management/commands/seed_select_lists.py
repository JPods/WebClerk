"""
seed_select_lists — Add select_lists to field_access Settings.

Usage:
    python manage.py seed_select_lists
    python manage.py seed_select_lists --force   # overwrite existing select_lists

Merges a `select_lists` key into each model's field_access Setting config.
This replaces WC2's popup/popupchoices tables with inline JSON — no new
tables, no FK lookups, already cached, already synced.

Each select list defines:
  - choices: list of allowed values
  - label: human-readable name for the dropdown
  - allow_custom: true = user can type a value not on the list (WC2 "Alternates")
"""
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting


# ─── Select lists by model ───────────────────────────────────────────────
# Only universal lists that every WC3 installation needs.
# Company-specific lists (product categories, custom profiles) are added
# by the company after setup.

SELECT_LISTS = {
    'order': {
        'status': {
            'label': 'Order Status',
            'choices': [
                'draft', 'open', 'approved', 'hold',
                'shipped', 'partial_ship', 'invoiced',
                'closed', 'cancelled',
            ],
            'allow_custom': True,
        },
        'priority': {
            'label': 'Priority',
            'choices': ['low', 'medium', 'high', 'urgent'],
            'allow_custom': False,
        },
    },

    'proposal': {
        'status': {
            'label': 'Proposal Status',
            'choices': [
                'draft', 'sent', 'reviewed',
                'accepted', 'declined', 'expired', 'revised',
            ],
            'allow_custom': True,
        },
    },

    'purchase': {
        'status': {
            'label': 'PO Status',
            'choices': [
                'draft', 'open', 'ordered', 'confirmed',
                'partial', 'received', 'closed', 'cancelled',
            ],
            'allow_custom': True,
        },
    },

    'invoice': {
        'status': {
            'label': 'Invoice Status',
            'choices': [
                'draft', 'open', 'sent',
                'partial', 'paid', 'void', 'cancelled',
            ],
            'allow_custom': True,
        },
    },

    'work_order': {
        'status': {
            'label': 'Work Order Status',
            'choices': [
                'draft', 'open', 'in_progress', 'on_hold',
                'completed', 'closed', 'cancelled',
            ],
            'allow_custom': True,
        },
    },

    'requisition': {
        'status': {
            'label': 'Requisition Status',
            'choices': [
                'request', 'requisition', 'approved',
                'ordered', 'received', 'closed',
            ],
            'allow_custom': True,
        },
    },

    'contact': {
        'salutation': {
            'label': 'Salutation',
            'choices': ['Mr.', 'Mrs.', 'Ms.', 'Dr.', 'Prof.'],
            'allow_custom': True,
        },
    },

    'customer': {
        'prospect': {
            'label': 'Prospect Level',
            'choices': ['lead', 'qualified', 'customer', 'key_account', 'inactive'],
            'allow_custom': True,
        },
        'price_level': {
            'label': 'Price Level',
            'choices': ['A', 'B', 'C', 'D'],
            'allow_custom': True,
        },
    },

    'item': {
        'type_id': {
            'label': 'Item Type',
            'choices': ['sale', 'service', 'build', 'internal', 'hold', 'dead'],
            'allow_custom': True,
        },
    },

    'action': {
        'status': {
            'label': 'Action Status',
            'choices': [
                'created', 'assigned', 'in_progress',
                'review', 'approved', 'closed', 'rejected',
            ],
            'allow_custom': True,
        },
        'priority': {
            'label': 'Priority',
            'choices': ['low', 'medium', 'high', 'urgent'],
            'allow_custom': False,
        },
    },

    'payment': {
        'type': {
            'label': 'Payment Type',
            'choices': ['received', 'expense'],
            'allow_custom': False,
        },
        'status': {
            'label': 'Payment Status',
            'choices': [
                'pending', 'authorized', 'captured',
                'settled', 'declined', 'voided', 'refunded',
            ],
            'allow_custom': False,
        },
        'category': {
            'label': 'Expense Category',
            'choices': [
                'Office Supplies',
                'Travel',
                'Utilities',
                'Rent',
                'Insurance',
                'Professional Services',
                'Shipping',
                'Equipment',
                'Materials',
                'Payroll',
                'Taxes',
                'Advertising',
                'Repairs & Maintenance',
                'Miscellaneous',
            ],
            'allow_custom': True,
            'default_gl': 'EXP-MISC-000',
            'gl_map': {
                'Office Supplies': 'EXP-OFFICE-000',
                'Travel': 'EXP-TRAVEL-000',
                'Utilities': 'EXP-UTIL-000',
                'Rent': 'EXP-RENT-000',
                'Insurance': 'EXP-INSUR-000',
                'Professional Services': 'EXP-PROFSVC-000',
                'Shipping': 'EXP-SHIPPING-000',
                'Equipment': 'EXP-EQUIP-000',
                'Materials': 'EXP-MATERIALS-000',
                'Payroll': 'EXP-PAYROLL-000',
                'Taxes': 'EXP-TAX-000',
                'Advertising': 'EXP-ADVERT-000',
                'Repairs & Maintenance': 'EXP-REPAIR-000',
                'Miscellaneous': 'EXP-MISC-000',
            },
        },
    },

    'gl_account': {
        'type': {
            'label': 'Account Type',
            'choices': ['asset', 'liability', 'equity', 'revenue', 'expense', 'contra'],
            'allow_custom': False,
        },
        'category': {
            'label': 'Account Category',
            'choices': ['cash', 'receivables', 'payables', 'inventory', 'sales', 'cogs', 'expense'],
            'allow_custom': True,
        },
    },

    'document': {
        'status': {
            'label': 'Document Status',
            'choices': ['draft', 'active', 'review', 'approved', 'archived', 'expired'],
            'allow_custom': True,
        },
    },
}


class Command(BaseCommand):
    help = 'Add select_lists to field_access Settings (replaces WC2 popup/popupchoices)'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Overwrite existing select_lists')

    def handle(self, *args, **options):
        force = options.get('force', False)
        updated = skipped = created_settings = 0

        for model_name, lists in SELECT_LISTS.items():
            setting = Setting.objects.filter(
                purpose='field_access',
                parent_model=model_name,
                is_active=True,
                is_deleted=False,
            ).first()

            if not setting:
                self.stdout.write(self.style.WARNING(
                    f'  No field_access Setting for {model_name} — skipping'))
                skipped += 1
                continue

            config = setting.config or {}
            existing = config.get('select_lists')

            if existing and not force:
                self.stdout.write(f'  {model_name}: select_lists exists (use --force)')
                skipped += 1
                continue

            config['select_lists'] = lists
            setting.config = config
            setting.save(update_fields=['config'])
            updated += 1
            field_count = len(lists)
            self.stdout.write(f'  {model_name}: {field_count} select lists added')

        self.stdout.write(self.style.SUCCESS(
            f'\nSelect lists: {updated} models updated, {skipped} skipped'))
