#demodata_related to exiting contacts
from django.core.management.base import BaseCommand
import random
import uuid
from core.models import Contact, Action
from communications.models import Email, Phone, Location, Domain

class Command(BaseCommand):
    help = "Populate 1-4 related records for each contact, storing links in refs.links.contacts"

    def handle(self, *args, **kwargs):
        contacts = Contact.objects.all()[:7]  # Get 7 contacts
        for contact in contacts:
            # Actions
            for _ in range(random.randint(1, 4)):
                action = Action.objects.create(
                    refs={"links": {"contacts": [contact.id]}},
                    description=f"Action for contact {contact.id}",
                    uuid=uuid.uuid4()
                )
            # Emails
            for _ in range(random.randint(1, 4)):
                email = Email.objects.create(
                    refs={"links": {"contacts": [contact.id]}},
                    email=f"user{uuid.uuid4().hex[:6]}@example.com",
                    name=f"Email for contact {contact.id}",
                    uuid=uuid.uuid4()
                )
            # Domains
            for _ in range(random.randint(1, 4)):
                domain = Domain.objects.create(
                    refs={"links": {"contacts": [contact.id]}},
                    path=f"www{random.randint(1,999)}.example.com",
                    uuid=uuid.uuid4()
                )
            # Phones
            for _ in range(random.randint(1, 4)):
                phone = Phone.objects.create(
                    refs={"links": {"contacts": [contact.id]}},
                    number=f"+1{random.randint(1000000000, 9999999999)}",
                    name=f"Phone for contact {contact.id}",
                    uuid=uuid.uuid4()
                )
            # Locations
            for _ in range(random.randint(1, 4)):
                location = Location.objects.create(
                    refs={"links": {"contacts": [contact.id]}},
                    address1=f"{random.randint(1,9999)} Main St",
                    city="Sample City",
                    country="Sample Country",
                    uuid=uuid.uuid4()
                )
        self.stdout.write(self.style.SUCCESS("Related records populated for 7 contacts."))