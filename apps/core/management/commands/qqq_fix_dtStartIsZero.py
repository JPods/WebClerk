from django.core.management.base import BaseCommand
from apps.core.models import Action
from django.utils import timezone

class Command(BaseCommand):
    help = 'Update action records with dt_start=0 to current datetime for dt_start and dt_updated, set duration=2, dt_expected=dt_start + 2 days'

    def handle(self, *args, **options):
        now = timezone.now()
        dt_start_ts = int(now.timestamp() * 1000)
        dt_updated_ts = dt_start_ts
        duration = 2
        dt_expected_ts = dt_start_ts + (duration * 24 * 60 * 60 * 1000)

        actions = Action.objects.filter(dt_start=0)
        self.stdout.write(f'Updating {actions.count()} actions with dt_start=0...')
        for action in actions:
            action.dt_start = dt_start_ts
            action.dt_updated = dt_updated_ts
            action.duration = duration
            action.dt_expected = dt_expected_ts
            action.save()
        self.stdout.write('Done.')