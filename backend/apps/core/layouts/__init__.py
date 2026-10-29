"""A model's layout: the one backend source of its list, detail, form, panel and card (Bill, 2026-10-29).

layouts.json holds every model's layout as designed — the code's default, captured from the
layouts in use (seed_layouts --capture) and committed. A model it does not hold gets the best
guess from its fields (guess.py). A company's own layout lives on its wc:model Setting
(config.layout) and is never overwritten: fill() adds only the parts it lacks, and reset() puts
back one part a staff login asks for, keeping the old part in the Log.

    layout.active                 which named layouts are in use
    layout.list.default.columns   db.list
    layout.column.default         the columns view
    layout.detail.default.fields  db.detail
    layout.form.default.sections  db.form: header, lines, comments, tabs
    layout.panel                  the model shown inside another record's page
    layout.card                   named cards {identity, details, schedule, …}
    layout.tabs                   the linked panels a record shows
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Optional

from django.db import transaction

from . import guess

PARTS = ('active', 'list', 'column', 'detail', 'form', 'panel', 'card', 'tabs')
DESIGNED = Path(__file__).with_name('layouts.json')
_designed: Optional[dict] = None


def designed() -> dict:
    """{model: layout} from layouts.json."""
    global _designed
    if _designed is None:
        _designed = json.loads(DESIGNED.read_text()) if DESIGNED.exists() else {}
    return _designed


def guessed(key: str) -> dict:
    """Every part, guessed from the model's fields."""
    columns = guess.list_columns(key)
    panel = guess.panel(key)
    card = guess.cards(key)
    pair = {'detail': 'default', 'form': 'default'}
    return {
        'active': {'list': 'default', 'column': 'default', 'detail': 'default', 'form': 'default'},
        'list': {'default': {**pair, 'columns': columns}},
        'column': {'default': {**pair, 'columns': panel}},
        'detail': {'default': {'list': 'default', 'form': 'default', 'fields': guess.detail_fields(key)}},
        'form': {'default': guess.form(key, card)},
        'panel': panel,
        'card': card,
        'tabs': list(guess.TABS),
    }


def build(key: str) -> dict:
    """The code's default layout for a model: as designed, any part it lacks guessed."""
    return _filled(key, copy.deepcopy(designed().get(key) or {}), lambda: guessed(key))[0]


def _has(layout: dict, part: str) -> bool:
    value = layout.get(part)
    default = value.get('default') if isinstance(value, dict) else None
    if part == 'list':
        return bool(isinstance(default, dict) and default.get('columns'))
    if part == 'column':
        return isinstance(default, dict)
    if part == 'detail':
        return bool(isinstance(default, dict) and (default.get('fields') or default.get('sections')))
    if part == 'form':
        sections = default.get('sections') if isinstance(default, dict) else None
        return (bool(sections) and 'edit_rules' in default
                and any(s.get('type') == 'header' for s in sections if isinstance(s, dict)))
    if part in ('panel', 'tabs'):
        return isinstance(value, list) and bool(value)
    return isinstance(value, dict) and bool(value)                     # active, card


def _filled(key: str, layout: dict, source) -> tuple[dict, list]:
    """Each part `layout` lacks, from source() (called once, only if needed)."""
    missing = [p for p in PARTS if not _has(layout, p)]
    if not missing:
        return layout, []
    src = source()
    form = layout.get('form') if isinstance(layout.get('form'), dict) else {}
    for part in missing:
        if part == 'form' and isinstance(form.get('default'), dict) and form['default'].get('sections'):
            # A form with sections but no fields gains a header in front; the rest stays, and
            # what the form page reads (model, family, edit_rules) is added where absent.
            mine, theirs = form['default'], src['form']['default']
            if not any(isinstance(s, dict) and s.get('type') == 'header' for s in mine['sections']):
                mine['sections'] = [s for s in theirs['sections'] if s.get('type') == 'header'] + mine['sections']
            mine.setdefault('model', key)
            mine.setdefault('family', guess.family_of(key))
            mine.setdefault('edit_rules', copy.deepcopy(theirs.get('edit_rules') or guess.EDIT_RULES))
        elif part in ('list', 'column', 'detail', 'form'):
            layout[part] = {**(layout.get(part) if isinstance(layout.get(part), dict) else {}),
                            'default': copy.deepcopy(src[part]['default'])}
        else:
            layout[part] = copy.deepcopy(src[part])
    return layout, missing


def fill(key: str, layout: Optional[dict]) -> tuple[dict, list]:
    """`layout` with each part it lacks taken from build(key); returns (layout, parts filled)."""
    return _filled(key, copy.deepcopy(layout or {}), lambda: build(key))


def reset(name: str, part: str, *, actor):
    """config.layout.<part> of model `name` becomes the code default; returns the new part."""
    from apps.core.models import Setting
    from apps.core.models.log import Log
    from apps.core.services import definition
    from apps.core.services.access import model_key
    from apps.core.services.door import Refused, as_actor
    key = model_key(name) or name
    if part not in PARTS:
        raise Refused(400, 'layout_part_unknown', f"A layout part is one of: {', '.join(PARTS)}.",
                      {'part': part})
    if not definition.may_change(actor):
        raise Refused(403, 'layout_edit_forbidden', 'Only staff reset a layout.', {'model_name': key})
    default = build(key).get(part)
    with transaction.atomic():
        model_def = (Setting.objects.select_for_update()
                     .filter(purpose='wc:model', parent_model=key).order_by('id').first())
        if model_def is None:
            raise Refused(404, 'no_definition', f'{key} has no model definition.', {'model_name': key})
        config = dict(model_def.config or {})
        layout = dict(config.get('layout') or {})
        before = layout.get(part)
        if before == default:
            return default
        layout[part] = default
        config['layout'] = layout
        Setting.objects.filter(pk=model_def.pk).update(config=config)
        definition.clear(key)
        Log.write('audit', 'layout_reset', model_name='setting', record_id=model_def.pk,
                  name=f'{key}.layout.{part}', changes={part: {'old': before, 'new': default}},
                  user=as_actor(actor).user)
    return default


def capture(layouts: dict) -> None:
    """Write {model: layout} into layouts.json (seed_layouts --capture): design work becomes code."""
    global _designed
    merged = {**designed(), **layouts}
    DESIGNED.write_text(json.dumps(dict(sorted(merged.items())), indent=1, ensure_ascii=False) + '\n')
    _designed = None
