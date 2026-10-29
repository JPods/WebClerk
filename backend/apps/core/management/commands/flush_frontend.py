"""
flush_frontend — Tell all open browser tabs to reload their cached Settings.

Bumps the wc-flush Setting's dt_changed timestamp. The frontend polls
every 15 seconds and reloads when it detects a change. BroadcastChannel
ensures all tabs in the same browser flush simultaneously.

Usage:
    ./bin/python manage.py flush_frontend

When to use:
    - After seed_panel_columns or any seed_* command
    - After bulk Setting updates
    - During initial setup when pages loaded before Settings existed
    - Alice calls this after detecting missing panel definitions
"""
from django.core.management.base import BaseCommand

from apps.core.services.frontend_flush import flush_frontend


class Command(BaseCommand):
    help = 'Signal frontend tabs to reload cached Settings and panel definitions'

    def handle(self, *args, **options):
        result = flush_frontend()
        verb = 'Created' if result['created'] else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f"{verb} wc-flush signal (dt_changed={result['dt_changed']}). "
            f'Frontend will reload within 15 seconds.'
        ))
