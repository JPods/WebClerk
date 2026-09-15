"""
Mark specific contacts as superusers.
"""
from django.core.management.base import BaseCommand
from apps.core.models.contact import Contact


class Command(BaseCommand):
    help = "Mark contacts with id=1 and id=2 as superusers"

    def handle(self, *args, **options):
        contacts = Contact.objects.filter(id__in=[1, 2])
        for contact in contacts:
            contact.is_superuser = True
            contact.is_staff = True
            contact.role = 'admin'
            contact.set_password('1111pass')
            contact.save()
            self.stdout.write(f"Marked contact {contact.id} ({contact.email}) as superuser")
        self.stdout.write(self.style.SUCCESS("Superuser marking completed"))