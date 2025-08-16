from django.core.management.base import BaseCommand
from contacts.models import Contact
from actions.models import Action
from communications.models import Communication

def extract_keywords(obj):
    # Dummy implementation: replace with your actual keyword extraction logic
    if hasattr(obj, 'description'):
        return obj.description.split()[:5]
    return []

def check_and_save_keywords(obj):
    keywords = extract_keywords(obj)
    obj.keywords = keywords
    obj.save()

class Command(BaseCommand):
    help = "Loop through contacts, actions, communications and save/check keywords"

    def handle(self, *args, **options):
        for contact in Contact.objects.all():
            check_and_save_keywords(contact)
        for action in Action.objects.all():
            check_and_save_keywords(action)
        for comm in Communication.objects.all():
            check_and_save_keywords(comm)
        self.stdout.write(self.style.SUCCESS("Keywords checked and saved for all records."))