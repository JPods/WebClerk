"""Reset one part of a model's layout to the code's default (Bill, 2026-10-29).

A model's layout (config.layout on its wc:model Setting: list, column, detail, form, panel, card,
tabs, active) is the company's own; seeding never overwrites it. When one part is broken, a
staff login puts that part — and only that part — back to what seed_model_definitions builds
from the model's fields; lists, help, access and every other part stay. The change is a Log
audit row holding the old part, so it can be put back; Alice's nightly backup holds it too.
"""
from __future__ import annotations

from django.db import transaction

PARTS = ('active', 'list', 'column', 'detail', 'form', 'panel', 'card', 'tabs')


def reset(name: str, part: str, *, actor):
    """config.layout.<part> of model `name` becomes the code default; returns the new part."""
    from apps.core.management.commands.seed_model_definitions import build_model_config
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
    default = build_model_config(key)['layout'].get(part)
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
        user = as_actor(actor).user
        Log.write('audit', 'layout_reset', model_name='setting', record_id=model_def.pk,
                  name=f'{key}.layout.{part}', changes={part: {'old': before, 'new': default}},
                  user=user)
    return default
