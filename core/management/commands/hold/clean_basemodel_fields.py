#2025-08-17
from django.core.management.base import BaseCommand
import random
import uuid
from core.models import Contact, Setting, Action
from communications.models import Email, Phone, Location, Domain

class Command(BaseCommand):
    help = "Clean and repopulate communications and core tables with sample data"

    def handle(self, *args, **kwargs):
        # Clean up tables
        #Contact.objects.all().delete()
        Email.objects.all().delete()
        Phone.objects.all().delete()
        Location.objects.all().delete()
        Domain.objects.all().delete()
        Action.objects.all().delete()
        Setting.objects.all().delete()

        # Create 5 sample contacts
        contacts = []
        for i in range(5):
            contact = Contact.objects.create(
                name_first=f"First{i}",
                name_last=f"Last{i}",
                email=f"user{i}@example.com",  # <-- Add this line
                uuid=uuid.uuid4()
            )
    contacts.append(contact)

    # For each contact, create sample actions, emails, domains, locations, phones
    for contact in contacts:
        # Actions
        for j in range(random.randint(1, 5)):
            Action.objects.create(
                refs={"links": {"contacts": [contact.id]}},
                action_type="sample",
                description=f"Sample action {j+1} for contact {contact.id}",
                uuid=uuid.uuid4()
            )
        # Emails
        for j in range(random.randint(1, 5)):
            Email.objects.create(
                refs={"links": {"contacts": [contact.id]}},
                email=f"user{uuid.uuid4().hex[:6]}@example.com",
                name=f"Email {j+1} for contact {contact.id}",
                uuid=uuid.uuid4()
            )
        # Domains
        for j in range(random.randint(1, 5)):
            Domain.objects.create(
                refs={"links": {"contacts": [contact.id]}},
                path=f"www{random.randint(1,999)}.example.com",
                uuid=uuid.uuid4()
            )
        # Locations
        for j in range(random.randint(1, 5)):
            Location.objects.create(
                refs={"links": {"contacts": [contact.id]}},
                address1=f"{random.randint(1,9999)} Main St",
                city="Sample City",
                country="Sample Country",
                uuid=uuid.uuid4()
            )
        # Phones
        for j in range(random.randint(1, 5)):
            Phone.objects.create(
                refs={"links": {"contacts": [contact.id]}},
                number=f"+1{random.randint(1000000000, 9999999999)}",
                name=f"Phone {j+1} for contact {contact.id}",
                uuid=uuid.uuid4()
            )

    self.stdout.write("Tables cleaned and repopulated with sample contacts and related data.")