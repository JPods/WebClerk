# python manage.py populate_related_data
from django.core.management.base import BaseCommand
import random
import uuid
from apps.core.models import Contact
from apps.communications.models import Email, Phone, Location, Domain

def set_contact_ref(metadata, contact_id):
    # Ensure the structure exists
    if 'refs' not in metadata:
        metadata['refs'] = {}
    if 'links' not in metadata['refs']:
        metadata['refs']['links'] = {}
    if 'contacts' not in metadata['refs']['links']:
        metadata['refs']['links']['contacts'] = []
    if contact_id not in metadata['refs']['links']['contacts']:
        metadata['refs']['links']['contacts'].append(contact_id)
    return metadata

class Command(BaseCommand):
    help = "Populate related tables with 1-5 records per contact"

    def handle(self, *args, **kwargs):
        for contact in Contact.objects.all():
            # Create 1-5 emails
            for _ in range(random.randint(1, 5)):
                Email.objects.create(
                    metadata=set_contact_ref({}, contact.id),
                    email=f"user{uuid.uuid4().hex[:6]}@example.com",
                    name=f"Email for {contact.id}",
                    uuid=uuid.uuid4()
                )
            # Create 1-5 phones
            for _ in range(random.randint(1, 5)):
                Phone.objects.create(
                    metadata=set_contact_ref({}, contact.id),
                    number=f"+1{random.randint(1000000000, 9999999999)}",
                    name=f"Phone for {contact.id}",
                    uuid=uuid.uuid4()
                )
            # Create 1-5 locations
            for _ in range(random.randint(1, 5)):
                Location.objects.create(
                    metadata=set_contact_ref({}, contact.id),
                    address1=f"{random.randint(1,9999)} Main St",
                    city="Sample City",
                    country="Sample Country",
                    uuid=uuid.uuid4()
                )
            # Create 1-5 domains
            for _ in range(random.randint(1, 5)):
                Domain.objects.create(
                    metadata=set_contact_ref({}, contact.id),
                    path=f"www{random.randint(1,999)}.example.com",
                    uuid=uuid.uuid4()
                )
            self.stdout.write(f"Populated related records for Contact id={contact.id}")