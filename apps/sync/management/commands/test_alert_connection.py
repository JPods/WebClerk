from django.core.management.base import BaseCommand
from apps.sync.services.incidents import trigger_safety_alert


class Command(BaseCommand):
    help = "Smoke-test: trigger the seeded safety alert Connection by creating an Exchange."

    def add_arguments(self, parser):
        parser.add_argument('--event', default='assault_detected', help='Event type to record')
        parser.add_argument('--severity', default='warning', help='Severity level')

    def handle(self, *args, **options):  # pragma: no cover - smoke path
        event = options['event']
        severity = options['severity']
        res = trigger_safety_alert(event, {"source": "test_alert_connection"}, severity)
        if res.get('ok'):
            self.stdout.write(self.style.SUCCESS(f"Alert exchange created: id={res.get('exchange_id')}"))
        else:
            self.stdout.write(self.style.ERROR(f"Failed to create alert exchange: {res.get('error')}"))
