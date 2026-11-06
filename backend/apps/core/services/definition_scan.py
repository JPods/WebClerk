"""Scan every stored model definition for what a form would get wrong (the lead's item 2,
2026-11-06: prove a fresh install). Four findings, each a list of ``model.field``:

- ``refused``  — an editable form field the save door would refuse (no concrete field, no
                 declared leaf; Bill 2026-11-05: "saving customer is not working");
- ``no_list``  — a field typed select whose definition holds no list (an empty dropdown);
- ``no_model`` — a lookup whose model is not registered (a search that can never find);
- ``stale``    — a stored behavior that lags what the code computes
                 (refresh_model_behaviors would change it).

Run on a fresh database loaded from init-bundle.json it proves the bundle; run on a live one
it audits the definitions. ``manage.py scan_definitions``; tests/test_fresh_install.py.
"""
from __future__ import annotations

from typing import Dict, List

from apps.core.constants.model_registry import get_model_meta

#: Form fields opened in a card, never typed, so the door never sees them.
CARD_FIELDS = frozenset({'email', 'phone', 'address_full', 'domain', 'attention'})


def _form_fields(layout: dict):
    for sec in ((layout or {}).get('default') or {}).get('sections', []):
        for col in sec.get('columns', []):
            for f in col.get('fields', []):
                if f.get('field'):
                    yield f


def refused_on_save(model_key: str, form: dict) -> List[str]:
    """Editable form fields the door would refuse: no concrete field, no declared leaf."""
    from apps.core.services import field_leaves as fl
    meta = get_model_meta(model_key)
    if meta is None:
        return []
    leaves = fl.model_leaves(model_key)['leaves']
    model = meta.import_model()
    concrete = {f.name for f in model._meta.concrete_fields} | {f.attname for f in model._meta.concrete_fields}
    out = []
    for f in _form_fields(form):
        name = f['field']
        if f.get('type') == 'readonly' or name in CARD_FIELDS:
            continue
        ok = (name in concrete or name in leaves or any(l.startswith(name + '.') for l in leaves)
              or ('.' in name and name.split('.')[0] in concrete))
        if not ok:
            out.append(name)
    return sorted(out)


def scan_definition(model_key: str, config: dict) -> Dict[str, List[str]]:
    """The four findings for one definition's config."""
    from apps.core.management.commands.refresh_model_behaviors import refreshed
    config = config or {}
    behaviors = config.get('behaviors') or {}
    lists = config.get('selectlists') or {}
    layout = config.get('layout') or {}
    out = {'refused': [], 'no_list': [], 'no_model': [], 'stale': []}
    out['refused'] = [f'{model_key}.{n}' for n in refused_on_save(model_key, layout.get('form') or {})]
    seen = set()
    for f in _form_fields(layout.get('form') or {}):
        name = f['field']
        beh = behaviors.get(name) or {}
        kind = f.get('type') or beh.get('type')
        if kind == 'select' and not lists.get(name) and name not in seen:
            out['no_list'].append(f'{model_key}.{name}'); seen.add(name)
    for name, beh in behaviors.items():
        if beh.get('type') == 'lookup' and get_model_meta(beh.get('model') or '') is None:
            out['no_model'].append(f'{model_key}.{name}')
    _config, changes, _kept = refreshed(model_key, config)
    out['stale'] = [f'{model_key}.{n}' for n in changes]
    return out


def scan() -> Dict[str, List[str]]:
    """Every wc:model definition in the database, the four findings merged."""
    from apps.core.models import Setting
    out = {'refused': [], 'no_list': [], 'no_model': [], 'stale': []}
    for s in Setting.objects.filter(purpose='wc:model').order_by('parent_model'):
        if not isinstance(s.config, dict) or get_model_meta(s.parent_model) is None:
            continue
        for key, found in scan_definition(s.parent_model, s.config).items():
            out[key].extend(found)
    return out
