"""
fix_party_layouts — Repoint transaction header cards from scalar/config.ship_to
to party-keyed addresses/phones/emails JSON fields.

Before: customer card reads company, phone, attention, address_full, email (scalars)
        ship_to card reads config.ship_to.* (old path)

After:  bill_to card reads addresses.bill_to.*, phones.bill_to.*, emails.bill_to.*
        ship_to card reads addresses.ship_to.*, phones.ship_to.*, emails.ship_to.*

Usage:
    python manage.py fix_party_layouts --dry-run
    python manage.py fix_party_layouts
"""
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting


BILL_TO_FIELDS = [
    {"type": "readonly", "field": "addresses.bill_to.company", "label": "company"},
    {"type": "readonly", "field": "addresses.bill_to.attention", "label": "attention"},
    {"type": "readonly", "field": "addresses.bill_to.full_address", "label": "address"},
    {"type": "readonly", "field": "phones.bill_to.number", "label": "phone"},
    {"type": "readonly", "field": "emails.bill_to.email", "label": "email"},
]

SHIP_TO_FIELDS = [
    {"field": "addresses.ship_to.company", "label": "company"},
    {"field": "addresses.ship_to.attention", "label": "attention"},
    {"field": "addresses.ship_to.full_address", "label": "address"},
    {"field": "phones.ship_to.number", "label": "phone"},
    {"field": "emails.ship_to.email", "label": "email"},
    {"field": "ship_via", "label": "ship_via"},
]

MODELS = [
    'wc-model-order',
    'wc-model-invoice',
    'wc-model-quote',
    'wc-model-purchase',
    'wc-model-work_order',
]


class Command(BaseCommand):
    help = 'Repoint transaction header cards to party-keyed JSON fields'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        tag = '[DRY RUN] ' if dry_run else ''
        updated = 0

        for ida in MODELS:
            try:
                s = Setting.objects.get(ida=ida, is_active=True)
            except Setting.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  {tag}Not found: {ida}'))
                continue

            cfg = s.config or {}
            layout = cfg.get('layout', {})
            form_default = layout.get('form', {}).get('default', {})
            sections = form_default.get('sections', [])

            changed = False
            for sec in sections:
                if sec.get('type') != 'header':
                    continue
                columns = sec.get('columns', [])
                for col in columns:
                    title = col.get('title', '')

                    # First column: customer/vendor → bill_to
                    if title in ('customer', 'vendor'):
                        old_fields = [f.get('field') for f in col.get('fields', [])]
                        col['title'] = 'bill_to'
                        col['fields'] = list(BILL_TO_FIELDS)
                        self.stdout.write(
                            f'  {tag}{ida}: {title} → bill_to  '
                            f'(was {old_fields})'
                        )
                        changed = True

                    # Second column: ship_to
                    elif title == 'ship_to':
                        old_fields = [f.get('field') for f in col.get('fields', [])]
                        col['fields'] = list(SHIP_TO_FIELDS)
                        self.stdout.write(
                            f'  {tag}{ida}: ship_to updated  '
                            f'(was {old_fields})'
                        )
                        changed = True

            if changed and not dry_run:
                s.config = cfg
                s._setting_update_authorized = True
                s.save(update_fields=['config'])
                updated += 1
            elif changed:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n{tag}Done: {updated} layouts updated'
        ))
