"""
Fill customer/vendor data into transaction headers and set ida = 'qq' + str(id)
on all transaction headers and lines.

- Proposals, Orders, Invoices: fill from customer org + contact
- Purchases: fill from vendor org + contact
- All headers and lines: ida = 'qq' + str(id)

Usage:
    python manage.py fill_demo_transactions
    python manage.py fill_demo_transactions --dry-run
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.transactions.models import (
    Proposal, ProposalLine,
    Order, OrderLine,
    Invoice, InvoiceLine,
    Purchase, PurchaseLine,
)
from apps.orgs.models import OrgBase


class Command(BaseCommand):
    help = 'Fill customer/vendor data into transactions and set ida=qq+id on headers and lines'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would change without saving')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Sell-side: fill from customer org
        sell_models = [
            (Proposal, ProposalLine, 'proposal'),
            (Order, OrderLine, 'order'),
            (Invoice, InvoiceLine, 'invoice'),
        ]
        for header_model, line_model, parent_field in sell_models:
            self._fill_headers(header_model, 'customer', dry_run)
            self._set_ida_lines(line_model, parent_field, dry_run)

        # Buy-side: fill from vendor org
        self._fill_headers(Purchase, 'vendor', dry_run)
        self._set_ida_lines(PurchaseLine, 'purchase', dry_run)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes saved'))
        else:
            self.stdout.write(self.style.SUCCESS('Done'))

    def _fill_headers(self, model, org_field, dry_run):
        """Fill denormalized customer/vendor fields and set ida on headers."""
        name = model.__name__
        headers = model.objects.select_related(org_field, 'contact').all()
        count = headers.count()
        self.stdout.write(f'\n{name}: {count} records')

        updated = 0
        for h in headers:
            org = getattr(h, org_field, None)
            contact = h.contact

            new_ida = f'qq{h.id}'
            changes = []

            if h.ida != new_ida:
                changes.append(f'  ida: {h.ida!r} -> {new_ida!r}')
                h.ida = new_ida

            if org:
                if h.company != org.display_name:
                    changes.append(f'  company: {h.company!r} -> {org.display_name!r}')
                    h.company = org.display_name
                if org.email and h.email != org.email:
                    changes.append(f'  email: {h.email!r} -> {org.email!r}')
                    h.email = org.email
                if org.attention and h.attention != org.attention:
                    changes.append(f'  attention: {h.attention!r} -> {org.attention!r}')
                    h.attention = org.attention
                # terms and price_level from org if available
                if hasattr(org, 'terms') and org.terms and h.terms != org.terms:
                    changes.append(f'  terms: {h.terms!r} -> {org.terms!r}')
                    h.terms = org.terms
                if hasattr(org, 'price_level') and org.price_level and h.price_level != org.price_level:
                    changes.append(f'  price_level: {h.price_level!r} -> {org.price_level!r}')
                    h.price_level = org.price_level

                # Address and phone from org JSON aspects
                addr = self._first_address(org)
                if addr and h.address_full != addr:
                    changes.append(f'  address_full: {h.address_full!r} -> {addr!r}')
                    h.address_full = addr
                phone = self._first_phone(org)
                if phone and h.phone != phone:
                    changes.append(f'  phone: {h.phone!r} -> {phone!r}')
                    h.phone = phone

            # Fallback to contact for missing fields
            if contact:
                if not h.attention and (contact.name_first or contact.name_last):
                    attn = f'{contact.name_first or ""} {contact.name_last or ""}'.strip()
                    if attn:
                        changes.append(f'  attention (from contact): -> {attn!r}')
                        h.attention = attn
                if not h.email and contact.email:
                    changes.append(f'  email (from contact): -> {contact.email!r}')
                    h.email = contact.email

            if changes:
                updated += 1
                if dry_run:
                    self.stdout.write(f'  {name} #{h.id}:')
                    for c in changes:
                        self.stdout.write(c)
                else:
                    h.save(update_fields=[
                        'ida', 'company', 'attention', 'email', 'phone',
                        'address_full', 'terms', 'price_level',
                    ])

        self.stdout.write(f'  {updated}/{count} updated')

    def _set_ida_lines(self, model, parent_field, dry_run):
        """Set ida = qq + str(id) on all lines."""
        name = model.__name__
        lines = model.objects.all()
        count = lines.count()
        updated = 0

        for line in lines:
            new_ida = f'qq{line.id}'
            if line.ida != new_ida:
                updated += 1
                if dry_run:
                    self.stdout.write(f'  {name} #{line.id}: ida {line.ida!r} -> {new_ida!r}')
                else:
                    line.ida = new_ida
                    line.save(update_fields=['ida'])

        self.stdout.write(f'  {name}: {updated}/{count} lines updated')

    def _first_address(self, org):
        """Extract first address string from org.addresses JSON aspect."""
        addresses = getattr(org, 'addresses', None)
        if not isinstance(addresses, list) or not addresses:
            return None
        addr = addresses[0]
        if isinstance(addr, dict):
            parts = []
            for key in ('address1', 'address_1', 'street', 'line1'):
                if addr.get(key):
                    parts.append(addr[key])
                    break
            for key in ('address2', 'address_2', 'line2'):
                if addr.get(key):
                    parts.append(addr[key])
                    break
            for key in ('city',):
                if addr.get(key):
                    parts.append(addr[key])
            state_zip = []
            if addr.get('state'):
                state_zip.append(addr['state'])
            if addr.get('zip') or addr.get('postal_code'):
                state_zip.append(addr.get('zip') or addr.get('postal_code'))
            if state_zip:
                parts.append(' '.join(state_zip))
            return ', '.join(parts) if parts else None
        return None

    def _first_phone(self, org):
        """Extract first phone number from org.phones JSON aspect."""
        phones = getattr(org, 'phones', None)
        if not isinstance(phones, list) or not phones:
            return None
        phone = phones[0]
        if isinstance(phone, dict):
            return phone.get('number') or phone.get('phone') or phone.get('value')
        if isinstance(phone, str):
            return phone
        return None
