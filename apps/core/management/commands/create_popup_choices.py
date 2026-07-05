"""
Create or update the singleton Setting record for popup_choices.

Reads legacy wc2 popups and popupchoices JSON exports, normalizes them into a
clean key→choices map, and stores the result in Setting.data so R25 can call
it to populate select lists.

Source files:
    webclerk3_data/popups/popups_wc2.json      – popup list definitions
    webclerk3_data/popups/popupchoices.json     – individual choice values

Usage:
    python manage.py create_popup_choices
    python manage.py create_popup_choices --reset     # Replace existing data
    python manage.py create_popup_choices --dry-run   # Preview without saving
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone

from django.core.management.base import BaseCommand

from apps.core.models import Setting


# ── Paths ────────────────────────────────────────────────────────────────────
DATA_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '../../../../..', 'webclerk3_data', 'popups')
)
POPUPS_FILE = os.path.join(DATA_DIR, 'popups_wc2.json')
CHOICES_FILE = os.path.join(DATA_DIR, 'popupchoices.json')


# ── Helpers ──────────────────────────────────────────────────────────────────
_CAMEL_RE = re.compile(r'(?<=[a-z0-9])(?=[A-Z])')

# Placeholder choice values that should be excluded
_PLACEHOLDER_CHOICES = frozenset({'Create', 'Create entries', ''})


def _array_name_to_key(array_name: str) -> str:
    """Convert a 4D array name like '<>aStatus' to a snake_case key 'status'.

    Rules:
        1. Strip '<>' prefix
        2. Strip leading 'a' or 'at' prefix  (4D naming convention)
        3. CamelCase → snake_case
        4. Lowercase
    """
    name = array_name.lstrip('<>').lstrip('>')  # remove <> wrapper
    # Strip leading 'at' (process variable) or 'a' (interprocess array) prefix
    if name.startswith('at'):
        name = name[2:]
    elif name.startswith('a'):
        name = name[1:]
    # CamelCase → snake_case
    name = _CAMEL_RE.sub('_', name)
    return name.lower()


def _build_popup_data() -> dict:
    """Parse both JSON files and return the normalized popup_choices payload."""

    with open(POPUPS_FILE) as f:
        raw_popups: list[dict] = json.load(f)

    with open(CHOICES_FILE) as f:
        raw_choices: list[dict] = json.load(f)

    # ── De-duplicate popup definitions ───────────────────────────────────
    # Same ArrayName can appear multiple times (re-approved over the years).
    # Keep the record with the highest UniqueID (latest revision).
    best_popup: dict[str, dict] = {}
    for popup in raw_popups:
        arr = popup['ArrayName']
        if arr not in best_popup or popup['UniqueID'] > best_popup[arr]['UniqueID']:
            best_popup[arr] = popup

    # ── Group choices by ArrayName ───────────────────────────────────────
    choices_by_array: dict[str, list[dict]] = defaultdict(list)
    for ch in raw_choices:
        val = (ch.get('Choice') or '').strip()
        if val in _PLACEHOLDER_CHOICES:
            continue
        choices_by_array[ch['ArrayName']].append(ch)

    # ── Build normalized lists dict ──────────────────────────────────────
    lists: dict[str, dict] = {}
    total_choices = 0

    for arr_name, popup in sorted(best_popup.items(), key=lambda kv: kv[0]):
        key = _array_name_to_key(arr_name)
        raw_ch = choices_by_array.get(arr_name, [])

        # Sort by Sequence then UniqueID for stable ordering
        raw_ch.sort(key=lambda c: (c.get('Sequence', 0), c.get('UniqueID', 0)))

        choices = []
        seen_values = set()
        for ch in raw_ch:
            val = ch['Choice'].strip()
            if val in seen_values:
                continue  # skip exact duplicate values within same list
            seen_values.add(val)
            choices.append({
                'value': val,
                'label': val,
                'alternate': (ch.get('Alternate') or '').strip(),
                'sequence': ch.get('Sequence', 0),
            })

        total_choices += len(choices)

        entry: dict = {
            'list_name': popup.get('ListName', '').strip(),
            'wc2_array_name': arr_name,
            'where_used': (popup.get('WhereUsed') or '').strip().replace('\r', '\n'),
            'choices': choices,
        }
        lists[key] = entry

    return {
        'meta': {
            'source': 'wc2 popups/popupchoices migration',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'total_lists': len(lists),
            'total_choices': total_choices,
        },
        'lists': lists,
    }


class Command(BaseCommand):
    help = 'Create/update the popup_choices singleton setting (purpose=admin)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Replace existing data even if the record already has content',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without saving',
        )

    def handle(self, *args, **options):
        reset = options.get('reset', False)
        dry_run = options.get('dry_run', False)

        # ── Validate source files ────────────────────────────────────────
        for path, label in ((POPUPS_FILE, 'popups_wc2.json'), (CHOICES_FILE, 'popupchoices.json')):
            if not os.path.isfile(path):
                self.stderr.write(self.style.ERROR(f'{label} not found: {path}'))
                return

        # ── Build payload ────────────────────────────────────────────────
        data = _build_popup_data()
        meta = data['meta']
        lists = data['lists']

        self.stdout.write(
            f"Parsed {meta['total_lists']} popup lists with "
            f"{meta['total_choices']} total choices\n"
        )

        if dry_run:
            header = f"{'Key':<30} {'ListName':<25} {'Choices':>7}"
            self.stdout.write(header)
            self.stdout.write('-' * len(header))
            for key, entry in sorted(lists.items()):
                n = len(entry['choices'])
                self.stdout.write(f"{key:<30} {entry['list_name']:<25} {n:>7}")
                for ch in entry['choices']:
                    alt = f"  (alt: {ch['alternate']})" if ch['alternate'] else ''
                    self.stdout.write(f"    - {ch['value']}{alt}")
            return

        # ── Persist setting ──────────────────────────────────────────────
        setting, created = Setting.objects.get_or_create(
            name='popup_choices',
            purpose='admin',
            defaults={'config': data},
        )

        if created:
            self.stdout.write(self.style.SUCCESS(
                f'Created popup_choices setting (id={setting.id}) — '
                f"{meta['total_lists']} lists, {meta['total_choices']} choices"
            ))
        elif reset:
            setting.config = data
            setting.save()
            self.stdout.write(self.style.SUCCESS(
                f'Reset popup_choices setting (id={setting.id}) — '
                f"{meta['total_lists']} lists, {meta['total_choices']} choices"
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'popup_choices setting already exists (id={setting.id}). '
                f'Use --reset to replace data.'
            ))
