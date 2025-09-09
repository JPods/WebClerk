"""Deprecated stub command retained only as a no-op placeholder after naming migration."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Deprecated stub; no longer needed."
    def handle(self, *args, **opts):  # pragma: no cover
        self.stdout.write('Deprecated no-op command; safe to remove when convenient.')
