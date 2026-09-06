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
import time

from django.core.management.base import BaseCommand

from apps.core.models.setting import Setting


class Command(BaseCommand):
    help = 'Signal frontend tabs to reload cached Settings and panel definitions'

    def handle(self, *args, **options):
        now_ms = int(time.time() * 1000)
        _, created = Setting.objects.update_or_create(
            ida='wc-flush',
            defaults={
                'name': 'Frontend Flush Signal',
                'purpose': 'wc:system',
                'explanation': 'Timestamp bumped to trigger frontend cache reload',
                'config': {'dt_changed': now_ms},
                'dt_modified': now_ms,
            },
        )
        verb = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'{verb} wc-flush signal (dt_changed={now_ms}). '
            f'Frontend will reload within 15 seconds.'
        ))
