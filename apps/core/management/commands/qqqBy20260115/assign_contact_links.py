"""
Management command to assign contact links for seeded database.

Assigns 1-3 records from domain, phone, email, address models to each contact's refs.links,
and 1 customer record. Also denormalizes by adding contact IDs to the related models' refs.links.contact.
"""
import random
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.core.models.contact import Contact
from apps.communications.models.domain import Domain
from apps.communications.models.phone import Phone
from apps.communications.models.email import Email
from apps.communications.models.address import Address
from apps.orgs.models.base_org_model import Customer


class Command(BaseCommand):
    help = "Assign contact links for seeded database records"

    def handle(self, *args, **options):
        self.stdout.write("Starting contact links assignment...")

        # Get all records
        contacts = list(Contact.objects.all())
        domains = list(Domain.objects.all())
        phones = list(Phone.objects.all())
        emails = list(Email.objects.all())
        addresses = list(Address.objects.all())
        try:
            customers = list(Customer.objects.all())
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not load customers: {e}"))
            customers = []

        self.stdout.write(f"Found {len(contacts)} contacts, {len(domains)} domains, {len(phones)} phones, "
                         f"{len(emails)} emails, {len(addresses)} addresses, {len(customers)} customers")

        if not contacts:
            self.stdout.write(self.style.WARNING("No contacts found"))
            return

        # Process each contact
        for contact in contacts:
            self.assign_links_to_contact(contact, domains, phones, emails, addresses, customers)

        self.stdout.write(self.style.SUCCESS("Contact links assignment completed"))

    def assign_links_to_contact(self, contact, domains, phones, emails, addresses, customers):
        """Assign links to a single contact and denormalize to related models."""
        with transaction.atomic():
            # Ensure refs.links exists
            if not hasattr(contact, 'refs') or not isinstance(contact.refs, dict):
                contact.refs = {}
            links = contact.refs.setdefault('links', {})

            # Assign 1-3 domains
            if domains:
                num_domains = min(random.randint(1, 3), len(domains))
                selected_domains = random.sample(domains, num_domains)
                links['domain'] = [domain.id for domain in selected_domains]
                # Denormalize: add contact to each domain's refs.links.contact
                for domain in selected_domains:
                    if not hasattr(domain, 'refs') or not isinstance(domain.refs, dict):
                        domain.refs = {}
                    domain_links = domain.refs.setdefault('links', {})
                    contact_list = domain_links.setdefault('contact', [])
                    if contact.id not in contact_list:
                        contact_list.append(contact.id)
                    domain.save(update_fields=['refs'])

            # Assign 1-3 phones
            if phones:
                num_phones = min(random.randint(1, 3), len(phones))
                selected_phones = random.sample(phones, num_phones)
                links['phone'] = [phone.id for phone in selected_phones]
                # Denormalize
                for phone in selected_phones:
                    if not hasattr(phone, 'refs') or not isinstance(phone.refs, dict):
                        phone.refs = {}
                    phone_links = phone.refs.setdefault('links', {})
                    contact_list = phone_links.setdefault('contact', [])
                    if contact.id not in contact_list:
                        contact_list.append(contact.id)
                    phone.save(update_fields=['refs'])

            # Assign 1-3 emails
            if emails:
                num_emails = min(random.randint(1, 3), len(emails))
                selected_emails = random.sample(emails, num_emails)
                links['email'] = [email.id for email in selected_emails]
                # Denormalize
                for email in selected_emails:
                    if not hasattr(email, 'refs') or not isinstance(email.refs, dict):
                        email.refs = {}
                    email_links = email.refs.setdefault('links', {})
                    contact_list = email_links.setdefault('contact', [])
                    if contact.id not in contact_list:
                        contact_list.append(contact.id)
                    email.save(update_fields=['refs'])

            # Assign 1-3 addresses
            if addresses:
                num_addresses = min(random.randint(1, 3), len(addresses))
                selected_addresses = random.sample(addresses, num_addresses)
                links['address'] = [addr.id for addr in selected_addresses]
                # Denormalize
                for addr in selected_addresses:
                    if not hasattr(addr, 'refs') or not isinstance(addr.refs, dict):
                        addr.refs = {}
                    addr_links = addr.refs.setdefault('links', {})
                    contact_list = addr_links.setdefault('contact', [])
                    if contact.id not in contact_list:
                        contact_list.append(contact.id)
                    addr.save(update_fields=['refs'])

            # Assign 1 customer
            if customers:
                selected_customer = random.choice(customers)
                links['customer'] = [selected_customer.id]
                # Denormalize
                try:
                    if not hasattr(selected_customer, 'refs') or not isinstance(selected_customer.refs, dict):
                        selected_customer.refs = {}
                    customer_links = selected_customer.refs.setdefault('links', {})
                    contact_list = customer_links.setdefault('contact', [])
                    if contact.id not in contact_list:
                        contact_list.append(contact.id)
                    selected_customer.save(update_fields=['refs'])
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Could not denormalize customer {selected_customer.id}: {e}"))

            # Save the contact
            contact.save(update_fields=['refs'])

        self.stdout.write(f"Assigned links for contact {contact.id}")