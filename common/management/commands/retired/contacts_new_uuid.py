from django.core.management.base import BaseCommand
from apps.core.models import Contact
import uuid

class Command(BaseCommand):
    help = "Assign a new UUID to contacts missing one"

    def handle(self, *args, **kwargs):
        for contact in Contact.objects.all():
            if not contact.uuid:
                contact.uuid = uuid.uuid4()
                contact.save()
                self.stdout.write(f"Set uuid for contact id={contact.id}")

    #psql -d commerce_expert -c "SELECT id, uuid, email, name_first, name_last FROM contacts;"

    #psql -d commerce_expert -c "ALTER TABLE contacts ADD COLUMN uuid UUID;"

    #psql -d commerce_expert -c "UPDATE contacts SET uuid = gen_random_uuid() WHERE uuid IS NULL;"

    #psql -d commerce_expert -c "DROP TABLE contacts;"