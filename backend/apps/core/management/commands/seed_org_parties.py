"""
seed_org_parties — Assign contact records as bill_to and ship_to on customers/vendors,
then propagate to their transaction records.

Uses existing contacts linked to each org. Picks two different contacts for bill_to
and ship_to when enough contacts exist; uses the same contact for both when only one
is available. Primary contact becomes the prime party.

Usage:
    python manage.py seed_org_parties --dry-run    # preview
    python manage.py seed_org_parties              # apply
"""
import random
from django.core.management.base import BaseCommand
from apps.orgs.models.base import OrgBase
from apps.core.models import Contact
from apps.communications.models import Phone, Email, Address
from apps.transactions.models import Order, Invoice, Purchase, Proposal


def _contact_party(contact, org):
    """Build a party dict from a contact and its communication records."""
    phone = Phone.objects.filter(contact_id=contact.pk, is_active=True).first()
    email = Email.objects.filter(contact_id=contact.pk, is_active=True).first()
    addr = Address.objects.filter(contact_id=contact.pk, is_active=True).first()

    return {
        'address': {
            'contact_id': contact.pk,
            'company': org.display_name,
            'attention': contact.attention or '',
            'full_address': addr.full if addr else '',
            'instructions': '',
        },
        'phone': {
            'phone_id': phone.pk if phone else None,
            'number': phone.number if phone else '',
        },
        'email': {
            'email_id': email.pk if email else None,
            'email': email.email if email else '',
        },
    }


class Command(BaseCommand):
    help = 'Assign contact records as bill_to/ship_to on orgs, then propagate to transactions'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        tag = '[DRY RUN] ' if dry_run else ''
        random.seed(42)

        org_updated = txn_updated = 0

        orgs = OrgBase.objects.filter(
            is_active=True,
            org_type__in=['customer', 'vendor'],
        ).order_by('display_name')

        for org in orgs:
            # Find contacts linked to this org
            linked = list(
                Contact.objects.filter(is_active=True)
                .filter(
                    **{f'{org.org_type}_id': org.pk}
                )
                .order_by('id')
            )

            if not linked:
                self.stdout.write(f'  {tag}Skip {org.display_name} — no linked contacts')
                continue

            # Primary contact
            primary = None
            if org.contact_id:
                primary = next((c for c in linked if c.pk == org.contact_id), None)
            if not primary:
                primary = linked[0]

            # Pick bill_to and ship_to from the pool (excluding primary)
            others = [c for c in linked if c.pk != primary.pk]

            if len(others) >= 2:
                bill_to_contact, ship_to_contact = random.sample(others, 2)
            elif len(others) == 1:
                # Sometimes same, sometimes different
                bill_to_contact = others[0]
                ship_to_contact = others[0] if random.random() < 0.4 else primary
            else:
                # Only one contact — use for all three roles
                bill_to_contact = primary
                ship_to_contact = primary

            prime = _contact_party(primary, org)
            bill_to = _contact_party(bill_to_contact, org)
            ship_to = _contact_party(ship_to_contact, org)

            org.addresses = {
                'prime': prime['address'],
                'bill_to': bill_to['address'],
                'ship_to': ship_to['address'],
            }
            org.phones = {
                'prime': prime['phone'],
                'bill_to': bill_to['phone'],
                'ship_to': ship_to['phone'],
            }
            org.emails = {
                'prime': prime['email'],
                'bill_to': bill_to['email'],
                'ship_to': ship_to['email'],
            }

            same = '(same)' if bill_to_contact.pk == ship_to_contact.pk else ''
            self.stdout.write(
                f'  {tag}{org.org_type} {org.display_name}: '
                f'prime={primary.attention}, '
                f'bill_to={bill_to_contact.attention}, '
                f'ship_to={ship_to_contact.attention} {same}'
            )

            if not dry_run:
                org.save(update_fields=['addresses', 'phones', 'emails'])
            org_updated += 1

            # Propagate to transactions
            for Model in [Order, Invoice, Purchase, Proposal]:
                txns = Model.objects.filter(is_active=True).filter(
                    **{'customer_id' if org.org_type == 'customer' else 'vendor_id': org.pk}
                )
                for txn in txns:
                    txn.addresses = {
                        'bill_to': bill_to['address'],
                        'ship_to': ship_to['address'],
                    }
                    txn.phones = {
                        'bill_to': bill_to['phone'],
                        'ship_to': ship_to['phone'],
                    }
                    txn.emails = {
                        'bill_to': bill_to['email'],
                        'ship_to': ship_to['email'],
                    }
                    if not dry_run:
                        txn.save(update_fields=['addresses', 'phones', 'emails'])
                    txn_updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n{tag}Done: {org_updated} orgs, {txn_updated} transactions updated'
        ))
