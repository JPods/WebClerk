from django.core.management.base import BaseCommand
from apps.core.models.contact import Contact

class Command(BaseCommand):
    help = 'Update attention field for all contacts based on name_first and name_last'

    def handle(self, *args, **options):
        contacts = Contact.objects.all()
        updated_count = 0
        for contact in contacts:
            old_attention = contact.attention
            new_attention = f"{contact.name_first} {contact.name_last}".strip()
            if old_attention != new_attention:
                contact.attention = new_attention
                contact.save(update_fields=['attention'])
                updated_count += 1
        self.stdout.write(self.style.SUCCESS(f'Successfully updated attention for {updated_count} contacts'))