import json
from random import random
from django.core.management.base import BaseCommand
from django.apps import apps

class Command(BaseCommand):

    def populate_action_records(num_records=20):
    Action = apps.get_model('core', 'Action')
    actions = []
    for i in range(num_records):
        action = Action(
            type=random.choice(['CREATE', 'UPDATE', 'DELETE']),
            description=f"Simulated action {i+1}",
            user_id=random.randint(1, 10),
            created_at=None  # Set to None to use auto_now_add if defined
        )
        actions.append(action)
    Action.objects.bulk_create(actions)

class Command(BaseCommand):
    help = "Populate Action records with simulated data"

    def handle(self, *args, **options):
        self.populate_action_records()