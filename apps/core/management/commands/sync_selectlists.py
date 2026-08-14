"""
Sync r25 select lists ↔ wc3 Setting records (purpose='wc:selectlist').

Thin wrapper around common.sync_wcreact.selectlists — all data and logic lives there.

Usage:
    python manage.py sync_selectlists --direction to-wc3
    python manage.py sync_selectlists --direction to-wc3 --dry-run
    python manage.py sync_selectlists --direction to-r25
    python manage.py sync_selectlists --direction list
    python manage.py sync_selectlists --direction to-wc3 --key terms --key priority
"""

from django.core.management.base import BaseCommand
from common.sync_wcreact.selectlists import (
    push_selectlists_to_wc3,
    show_selectlists_for_r25,
    list_selectlist_settings,
)


class Command(BaseCommand):
    help = "Sync r25 select lists ↔ wc3 Setting records (purpose='wc:selectlist')"

    def add_arguments(self, parser):
        parser.add_argument(
            "--direction",
            choices=["to-wc3", "to-r25", "list"],
            default="list",
            help="to-wc3: push r25 lists → wc3 settings.  "
                 "to-r25: show wc3 settings as r25 format.  "
                 "list: show current wc3 selectlist settings.",
        )
        parser.add_argument(
            "--key",
            action="append",
            dest="keys",
            help="Limit to specific list key(s). Can be repeated.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without saving.",
        )

    def handle(self, *args, **options):
        direction = options["direction"]
        keys = options.get("keys")
        dry_run = options["dry_run"]

        if direction == "to-wc3":
            push_selectlists_to_wc3(self.stdout, self.style, keys=keys, dry_run=dry_run)
        elif direction == "to-r25":
            show_selectlists_for_r25(self.stdout, keys=keys)
        else:
            list_selectlist_settings(self.stdout, keys=keys)
