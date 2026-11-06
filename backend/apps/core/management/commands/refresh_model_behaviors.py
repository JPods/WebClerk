"""Bring every stored definition's behaviors up to what the code computes — additively.

A definition's config.behaviors is seeded once (seed_model_definitions) and the form reads it,
never the code. Fields added to a model since, and rules the code learned since (terms as a
lookup, an integer pointer as a lookup), reach no form until the stored copy is refreshed —
the gap 0061, 0063 closed one field at a time (Bill, 2026-11-05: "the vast majority of user
input fields should have a selectlist").

Rules (the lead's, 2026-11-05: additive means never overwriting what a person changed): a
computed field the stored set lacks is added; a stored entry that still equals what the code
computed before — a number default, or a lookup with only the keys the code gave it — takes
what the code computes now (the label kept); anything else is a person's edit, reported and
left alone. The stored behaviors do not record who set them, so "equal to the old default" is
the test.

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
    """``(config, changes, kept)`` — the definition's config with its behaviors refreshed, the
    field names that changed, and the fields the code would change but a person has edited
    (reported, never touched)."""
    try:
        computed = get_field_behaviors(model_key)
    except Exception:
        return config, [], []
    behaviors = dict(config.get('behaviors') or {})
    changes, kept = [], []
    for name, comp in computed.items():
        stored = behaviors.get(name)
        if stored is None:
            behaviors[name] = dict(comp)
            changes.append(name)
            continue
        if comp.get('type') != 'lookup' or stored.get('type') == 'lookup' and not (set(comp) - set(stored) - {'label'}):
            continue                                    # nothing the code would change
        if _is_old_default(stored, comp):
            behaviors[name] = {**comp, 'label': stored.get('label') or comp.get('label')}
            changes.append(name)
        else:
            kept.append(name)
    if not changes:
        return config, [], kept
    return {**config, 'behaviors': behaviors}, changes, kept


def _is_old_default(stored: dict, comp: dict) -> bool:
    """The stored entry is what the code computed before: a bare number, or a lookup whose
    every key the code gave it with the same value. The label is never the test — a label is
    the person's wording and is kept whichever way the type goes."""
    rest = {k: v for k, v in stored.items() if k != 'label'}
    if rest == {'type': 'number'} or (rest == {'type': 'text'} and comp.get('value') == 'ida'):
        return True                     # the code's own defaults for an _id and an _ida column
    if rest.get('type') == 'lookup':
        return all(k in comp and comp[k] == v for k, v in rest.items())
    return False


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
            config, changes, kept = refreshed(s.parent_model, s.config)
            if kept:
                self.stdout.write(f'{s.parent_model}: kept as a person set them: {", ".join(kept)}')
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
                    config, changes, kept = refreshed(item['parent_model'], item['config'])
                    if kept:
                        self.stdout.write(f'{name} {item["parent_model"]}: kept as a person set them: {", ".join(kept)}')
                    if changes:
                        item['config'] = config
                        n += len(changes)
                if not opts['dry_run']:
                    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
                self.stdout.write(f'{name}: {n} behaviors')
