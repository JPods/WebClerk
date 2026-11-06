"""Scan every stored model definition for what a form would get wrong (definition_scan.py).

Usage:
    python manage.py scan_definitions          # exit 1 when anything is found
"""
import sys

from django.core.management.base import BaseCommand

from apps.core.services.definition_scan import scan


class Command(BaseCommand):
    help = "Form fields the door refuses, selects with no list, lookups on no model, stale behaviors"

    def handle(self, *args, **opts):
        found = scan()
        total = 0
        for key, items in found.items():
            self.stdout.write(f'{key}: {len(items)}')
            for item in items:
                self.stdout.write(f'  {item}')
            total += len(items)
        self.stdout.write('clean' if not total else f'{total} findings')
        if total:
            sys.exit(1)
