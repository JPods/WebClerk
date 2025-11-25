from django.core.management.base import BaseCommand
from apps.core.models import Action
import datetime

class Command(BaseCommand):
    help = 'Update action dates to 2025-11-25 start, 2025-11-30 due/end/expected, duration 4'

    def handle(self, *args, **options):
        dt_start_ts = int(datetime.datetime(2025, 11, 25).timestamp() * 1000)
        dt_due_ts = int(datetime.datetime(2025, 11, 30).timestamp() * 1000)
        dt_end_ts = int(datetime.datetime(2025, 11, 30).timestamp() * 1000)
        dt_expected_ts = int(datetime.datetime(2025, 11, 30).timestamp() * 1000)
        duration = 4

        actions = Action.objects.all()
        self.stdout.write(f'Updating {actions.count()} actions...')
        for action in actions:
            action.dt_start = dt_start_ts
            action.dt_due = dt_due_ts
            action.dt_end = dt_end_ts
            action.dt_expected = dt_expected_ts
            action.duration = duration
            action.save()
        self.stdout.write('Done.')