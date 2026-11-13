"""Defaults — each model's own, seen together; one moment (readme 106; Bill, 2026-11-07).

Where: every model's defaults live in its own ``wc:model`` Setting, ``config.defaults`` =
``{"fields": {<field>: <value>}, "formatting": {currency, locale, date_format, number_precision}}``
(Bill: "put them in each model.setting", config.defaults not prefs.defaults, formatting folded in
and nested so a field named like a formatting key cannot collide). The defaults console
(a ``wc:console`` Setting; the front end's DefaultsConsole) shows every model's blocks in one
grid, marks where models disagree on a shared field, and edits each cell through the door into
that model's Setting. The company profile keeps no defaults.

When: the save that first gives a record its ida fills its blank fields from its model's
``fields`` block. The server writes them with no role filter — a default is the company's
write, not the person's; a value the same payload carries is the person's and wins, blank
included. A later ida change does not fire them again, and no later save refills a blank:
existing records are repaired by the sweep (106 step 4), not on every save.

``model_defaults`` is the one reader. ``checked_defaults`` is the one gate: a block naming a
field the model lacks, a value off the field's list, or a formatting key that is not one of the
four is refused where it is written (Setting.save). ``shipped_defaults`` is what a fresh
installation starts with (seed_model_definitions); the migration that gave wc_demo its blocks
(core 0072) carries its own frozen copy.

A ``<field>_days`` default is that many days from now, written as the dt_ field's UTC epoch ms.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from apps.core.services.door import Refused

DAY_MS = 86_400_000
SELL = ('quote', 'order', 'invoice')
BUY = ('purchase', 'receipt')
FORMATTING_KEYS = ('currency', 'locale', 'date_format', 'number_precision')
#: The fields the console compares across models.
SHARED_FIELDS = ('terms', 'price_level', 'dt_needed_days', 'priority', 'source_name')

SHIPPED_FORMATTING: Dict[str, Any] = {'currency': 'USD', 'locale': 'en-US', 'date_format': 'short',
                                      'number_precision': 2}
#: A fresh installation's field defaults, per model. A model not named starts with none.
SHIPPED_FIELDS: Dict[str, Dict[str, Any]] = {
    **{m: {'terms': 'N30', 'price_level': 'retail', 'dt_needed_days': 14, 'priority': 'medium'} for m in SELL + BUY},
    'workorder': {'dt_needed_days': 14, 'priority': 'medium'},
    'customer': {'terms': 'N30', 'price_level': 'retail'},
    'vendor': {'terms': 'N30'},
    'manufacturer': {'terms': 'N30'},
}


#: Switches a model's definition carries beside its field defaults: ``config.defaults.features``
#: = ``{<name>: true|false}`` (Bill, 2026-11-12: "a default to turn this line/serial contact on
#: and off"). name → the models that have the switch and what a fresh installation starts with.
#: ``line_contacts``: the people a line names by role and the serial it issues carries
#: (readme 110; transactions/services/line_contacts.py).
FEATURES: Dict[str, Dict[str, Any]] = {
    'line_contacts': {'models': SELL, 'shipped': False},
}


def shipped_features(model_key: str) -> Dict[str, bool]:
    """The switches this model has, each as a fresh installation starts with it."""
    return {name: bool(f['shipped']) for name, f in FEATURES.items() if model_key in f['models']}


def shipped_defaults(model_key: str) -> Dict[str, Any]:
    """The block a model's definition is seeded with."""
    block = {'fields': dict(SHIPPED_FIELDS.get(model_key, {})), 'formatting': dict(SHIPPED_FORMATTING)}
    if shipped_features(model_key):
        block['features'] = shipped_features(model_key)
    return block


def model_features(model_key: str) -> Dict[str, bool]:
    """The model's switches from its definition, the shipped value where it names none."""
    from apps.core.services import definition
    shipped = shipped_features(model_key)
    return definition.part(model_key, ('defaults', 'features'),
                           lambda raw: {**shipped, **{k: bool(v) for k, v in raw.items() if k in shipped}}
                           if isinstance(raw, dict) else dict(shipped))


def feature_on(model_key: str, name: str) -> bool:
    """Whether this model's switch ``name`` is on. A model without the switch has it off."""
    return bool(model_features(model_key).get(name))


def model_defaults(model_key: str) -> Dict[str, Any]:
    """The model's field defaults from its definition: ``{field: value}``, blanks left out.
    Read through the definition cache (a change is seen within a second, any process)."""
    from apps.core.services import definition
    return definition.part(model_key, ('defaults', 'fields'),
                           lambda raw: _present(raw) if isinstance(raw, dict) else {})


def model_formatting(model_key: str) -> Dict[str, Any]:
    """The model's formatting block, the shipped one where the definition has none."""
    from apps.core.services import definition
    return definition.part(model_key, ('defaults', 'formatting'),
                           lambda raw: {**SHIPPED_FORMATTING, **raw} if isinstance(raw, dict) else dict(SHIPPED_FORMATTING))


def _present(block: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in block.items() if v not in (None, '')}


def resolve(key: str, value: Any) -> tuple:
    """A default's field and value: ``dt_needed_days: 14`` is ``dt_needed`` two weeks out."""
    if key.endswith('_days'):
        return key[:-len('_days')], int(time.time() * 1000) + int(float(value) * DAY_MS)
    return key, value


def named_term(value: Any) -> str:
    """A terms default as the Term's own ida; a definition naming no term is a configuration
    fault, refused where it bites with the valid idas (fail fast, never silent)."""
    from apps.accounts.services.terms_ledger import named_term_ida
    try:
        return named_term_ida(value)
    except ValueError as e:
        raise Refused(400, 'invalid_terms', f'The definition\'s defaults.fields.terms is wrong: {e}',
                      [f'terms: {e}'])


def fill_defaults(obj, model_key: str, data: Dict[str, Any], named: bool) -> List[str]:
    """Fill the blank fields of a record this save first gives an ida; the fields filled.
    Called by the save door after the payload is assigned (save._write). ``named`` is whether
    the record had an ida before this save: one whose payload carries its ida (an import, a
    bundle) is still being named now, and its blanks are filled like any newborn's."""
    names = {f.name for f in obj._meta.concrete_fields}
    if 'ida' not in names or named:                           # already named: the moment has passed
        return []
    filled: List[str] = []
    for key, value in model_defaults(model_key).items():
        field, value = resolve(key, value)
        if field not in names or field in data or getattr(obj, field, None) not in (None, ''):
            continue
        setattr(obj, field, named_term(value) if field == 'terms' else value)
        filled.append(field)
    return filled


# ── the gate: Setting.save on a wc:model definition ─────────────────────────

def checked_defaults(model_key: str, defaults: Any) -> Dict[str, Any]:
    """``config.defaults`` as it may be stored, or ValueError with coaching: the two blocks and
    nothing else; ``fields`` names only fields the model has (its <Model>SettingDefaults
    schema, extra forbidden, then the model's own columns), a value with a list in the
    definition is stored in the list's spelling, terms as a Term's ida; ``formatting`` holds
    only the four keys."""
    switches = shipped_features(model_key)
    if defaults in (None, {}):
        return {'fields': {}, 'formatting': dict(SHIPPED_FORMATTING), **({'features': switches} if switches else {})}
    if not isinstance(defaults, dict) or set(defaults) - {'fields', 'formatting', 'features'}:
        raise ValueError(f'{model_key} config.defaults holds "fields", "formatting" and "features", nothing '
                         f'else: {sorted(defaults) if isinstance(defaults, dict) else type(defaults).__name__}.')
    features = defaults.get('features') or {}
    if not isinstance(features, dict):
        raise ValueError(f'{model_key} config.defaults.features is an object of switches.')
    unknown = sorted(set(features) - set(switches))
    if unknown:
        has = ', '.join(sorted(switches)) or 'none'
        raise ValueError(f'{model_key} has no switch {", ".join(unknown)}; its switches: {has}.')
    not_bool = sorted(k for k, v in features.items() if not isinstance(v, bool))
    if not_bool:
        raise ValueError(f'{model_key} switch {", ".join(not_bool)} is true or false.')
    fields = defaults.get('fields') or {}
    formatting = defaults.get('formatting') or {}
    if not isinstance(fields, dict) or not isinstance(formatting, dict):
        raise ValueError(f'{model_key} config.defaults.fields and .formatting are objects.')
    unknown = sorted(set(formatting) - set(FORMATTING_KEYS))
    if unknown:
        raise ValueError(f'{model_key} config.defaults.formatting takes {", ".join(FORMATTING_KEYS)}; '
                         f'not {", ".join(unknown)}.')
    fields = _checked_fields(model_key, fields)
    out = {'fields': fields, 'formatting': {**SHIPPED_FORMATTING, **formatting}}
    if switches:
        out['features'] = {**switches, **features}
    return out


def _checked_fields(model_key: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    schema = defaults_schema(model_key)
    if schema is not None:
        try:
            schema(**fields)
        except Exception as e:                       # pydantic's ValidationError, extra forbidden
            raise ValueError(f'{model_key} config.defaults.fields: {_pydantic_sentence(e)}')
    names = _concrete_names(model_key)
    if names:
        bad = sorted(k for k in fields if (k[:-len('_days')] if k.endswith('_days') else k) not in names)
        if bad:
            raise ValueError(f'{model_key} has no field {", ".join(bad)}: a default names a field the '
                             f'model has (a dt_ field as <field>_days).')
    from apps.core.services import select_lists
    lists = select_lists.lists(model_key)
    out: Dict[str, Any] = {}
    for key, value in fields.items():
        if value in (None, ''):
            continue
        listed = lists.get(key)
        if listed:
            match = next((str(v) for v in listed if str(v).lower() == str(value).lower()), None)
            if match is None:
                raise ValueError(f"{model_key} default {key} '{value}' is not on its list: "
                                 f"{', '.join(sorted(str(v) for v in listed))}.")
            value = match
        if key == 'terms':
            from apps.accounts.services.terms_ledger import named_term_ida
            try:
                value = named_term_ida(value)
            except ValueError as e:
                raise ValueError(f'{model_key} default terms: {e}')
        if key.endswith('_days'):
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise ValueError(f'{model_key} default {key} is a number of days, not {value!r}.')
        out[key] = value
    return out


def _pydantic_sentence(e: Exception) -> str:
    errors = getattr(e, 'errors', None)
    if callable(errors):
        parts = []
        for err in errors():
            loc = '.'.join(str(p) for p in err.get('loc', ())) or '?'
            parts.append(f"{loc}: {err.get('msg', '')}")
        return '; '.join(parts)
    return str(e)


def _concrete_names(model_key: str) -> set:
    from apps.core.utils import registry
    resolved = registry.resolve(model_key)
    if resolved is None:
        return set()
    model = resolved if hasattr(resolved, '_meta') else resolved.import_model()
    return {f.name for f in model._meta.concrete_fields} if model is not None else set()


def defaults_schema(model_key: str):
    """The model's <Model>SettingDefaults pydantic class (its ``<model>_pydantic`` module), or
    None when the model has none."""
    import importlib
    from apps.core.utils import registry
    resolved = registry.resolve(model_key)
    if resolved is None:
        return None
    model = resolved if hasattr(resolved, '_meta') else resolved.import_model()
    if model is None:
        return None
    try:
        module = importlib.import_module(f'{model.__module__}_pydantic')
    except ImportError:
        return None
    for name in dir(module):
        if name.endswith('SettingDefaults'):
            return getattr(module, name)
    return None


# ── an org's own defaults for its documents ─────────────────────────────────
#: What an org's config.defaults.fields may hold: the document fields a party fill may set
#: that are not columns on the org (a column describes the org — terms, price_level,
#: source_name — and party_fill copies it; never a value in both). The chain is the model's
#: Setting, then the org, then the payload (the lead, readme 106 "Orgs carry their own defaults").
ORG_DEFAULT_FIELDS = ('ship_via', 'priority', 'dt_needed_days', 'rep_id')


def checked_org_defaults(defaults: Any) -> Dict[str, Any]:
    """An org's ``config.defaults`` as it may be stored, or ValueError with coaching: the two
    blocks; fields among ORG_DEFAULT_FIELDS, a listed value in a document list's spelling
    (ship_via and priority are checked against every sell document's list); formatting the
    four keys."""
    if defaults in (None, {}):
        return {'fields': {}, 'formatting': {}}
    if not isinstance(defaults, dict) or set(defaults) - {'fields', 'formatting'}:
        raise ValueError('An org\'s config.defaults holds "fields" and "formatting", nothing else.')
    fields = defaults.get('fields') or {}
    formatting = defaults.get('formatting') or {}
    if not isinstance(fields, dict) or not isinstance(formatting, dict):
        raise ValueError('config.defaults.fields and .formatting are objects.')
    unknown = sorted(set(formatting) - set(FORMATTING_KEYS))
    if unknown:
        raise ValueError(f'config.defaults.formatting takes {", ".join(FORMATTING_KEYS)}; not {", ".join(unknown)}.')
    bad = sorted(set(fields) - set(ORG_DEFAULT_FIELDS))
    if bad:
        raise ValueError(f'An org\'s config.defaults.fields takes {", ".join(ORG_DEFAULT_FIELDS)} — what its '
                         f'documents start with and the org has no column for; not {", ".join(bad)}. Terms, '
                         f'price level and source are the org\'s own columns.')
    from apps.core.services import select_lists
    out: Dict[str, Any] = {}
    for key, value in fields.items():
        if value in (None, ''):
            continue
        if key in ('ship_via', 'priority'):
            listed = {str(v) for model_key in SELL + BUY for v in (select_lists.lists(model_key).get(key) or ())}
            match = next((v for v in sorted(listed) if v.lower() == str(value).lower()), None)
            if listed and match is None:
                raise ValueError(f"default {key} '{value}' is on no document's list: {', '.join(sorted(listed))}.")
            value = match or str(value)
        if key == 'dt_needed_days':
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise ValueError(f'default dt_needed_days is a number of days, not {value!r}.')
        out[key] = value
    return {'fields': out, 'formatting': {k: v for k, v in formatting.items() if k in FORMATTING_KEYS}}


def org_defaults(org) -> Dict[str, Any]:
    """The org's ``config.defaults.fields``, blanks left out."""
    config = org.config if isinstance(getattr(org, 'config', None), dict) else {}
    block = config.get('defaults') if isinstance(config.get('defaults'), dict) else {}
    fields = block.get('fields') if isinstance(block.get('fields'), dict) else {}
    return _present(fields)
