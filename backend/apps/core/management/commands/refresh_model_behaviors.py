"""Bring every stored definition's behaviors up to what the code computes — additively.

A definition's config.behaviors is seeded once (seed_model_definitions) and the form reads it,
never the code. Fields added to a model since, and rules the code learned since (terms as a
lookup, an integer pointer as a lookup), reach no form until the stored copy is refreshed —
the gap 0061, 0063 closed one field at a time (Bill, 2026-11-05: "the vast majority of user
input fields should have a selectlist").

Rules: a computed field the stored set lacks is added; a stored 'number' the code now computes
as a 'lookup' becomes that lookup (its label kept); a stored lookup takes the keys the computed
lookup has and it lacks (pick, value, display); every other stored entry is left alone — a staff
member's edit to a behavior is theirs.

Usage:
    python manage.py refresh_model_behaviors            # the stored definitions
    python manage.py refresh_model_behaviors --dry-run
    python manage.py refresh_model_behaviors --bundles  # settings/init/demo bundles too
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.core.models.setting import Setting
from apps.core.services.field_behaviors import get_field_behaviors

BUNDLES = ('settings-bundle.json', 'init-bundle.json', 'demo-bundle.json')
ROOT = Path(__file__).resolve().parents[4]


def refreshed(model_key: str, config: dict) -> tuple:
    """``(config, changes)`` — the definition's config with its behaviors refreshed, and the
    field names that changed (empty when nothing did)."""
    try:
        computed = get_field_behaviors(model_key)
    except Exception:
        return config, []
    behaviors = dict(config.get('behaviors') or {})
    changes = []
    for name, comp in computed.items():
        stored = behaviors.get(name)
        if stored is None:
            behaviors[name] = dict(comp)
            changes.append(name)
        elif stored.get('type') == 'number' and comp.get('type') == 'lookup':
            behaviors[name] = {**stored, **comp, 'label': stored.get('label') or comp.get('label')}
            changes.append(name)
        elif stored.get('type') == 'lookup' and comp.get('type') == 'lookup' and set(comp) - set(stored) - {'label'}:
            behaviors[name] = {**{k: v for k, v in comp.items() if k != 'label'}, **stored}
            changes.append(name)
    if not changes:
        return config, []
    return {**config, 'behaviors': behaviors}, changes


class Command(BaseCommand):
    help = "Add the behaviors the code computes to every stored definition that lacks them"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--bundles', action='store_true', help='Refresh the three shipped bundles too')

    def handle(self, *args, **opts):
        total = 0
        for s in Setting.objects.filter(purpose='wc:model').iterator():
            if not isinstance(s.config, dict):
                continue
            config, changes = refreshed(s.parent_model, s.config)
            if changes:
                total += len(changes)
                self.stdout.write(f'{s.parent_model}: {", ".join(changes)}')
                if not opts['dry_run']:
                    Setting.objects.filter(pk=s.pk).update(config=config)
        self.stdout.write(f'{total} behaviors {"would be " if opts["dry_run"] else ""}added or upgraded')
        if opts['bundles']:
            for name in BUNDLES:
                path = ROOT / name
                data = json.loads(path.read_text())
                n = 0
                for item in data['settings']:
                    if item.get('purpose') != 'wc:model' or not isinstance(item.get('config'), dict):
                        continue
                    config, changes = refreshed(item['parent_model'], item['config'])
                    if changes:
                        item['config'] = config
                        n += len(changes)
                if not opts['dry_run']:
                    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
                self.stdout.write(f'{name}: {n} behaviors')
