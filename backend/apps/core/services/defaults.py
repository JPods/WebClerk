"""Defaults — one home, one moment (readme 106; Bill, 2026-11-07).

One home: the company profile's ``config.defaults`` holds every model's defaults. One moment:
the save that first gives a record its ida fills its blank fields from its model's block. The
server writes them with no role filter — a default is the company's write, not the person's;
a value the same payload carries is the person's and wins, blank included. A later ida change
does not fire them again, and no later save refills a blank: existing records are repaired
by the sweep (106 step 4), not on every save.

``model_defaults`` is the one reader of the profile's shape. Until Bill rules on the per-model
blocks (106, open A) the stored shape is still ``{terms, order_new: {days, priority}}`` and
this function derives each model's block from it; step 1 replaces its body with a direct read
of ``defaults[model_key]`` and nothing else changes.

A ``<field>_days`` default is that many days from now, written as the dt_ field's UTC epoch ms.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List

from apps.core.services.door import Refused

DAY_MS = 86_400_000
DOCUMENTS = ('quote', 'order', 'invoice', 'purchase', 'receipt', 'workorder', 'requisition')


def model_defaults(model_key: str) -> Dict[str, Any]:
    """The company's defaults for one model: ``{field: value}``, blanks left out."""
    from apps.core.services.company_profile import company_config
    stored = company_config('defaults')
    block = stored.get(model_key)
    if isinstance(block, dict):
        return _present(block)
    # Derived from the pre-106 shape until the per-model blocks land (open A).
    terms = stored.get('terms')
    order_new = stored.get('order_new') if isinstance(stored.get('order_new'), dict) else {}
    if model_key in DOCUMENTS:
        return _present({'terms': terms, 'price_level': 'retail',
                         'dt_needed_days': order_new.get('days'), 'priority': order_new.get('priority')})
    if model_key == 'customer':
        return _present({'terms': terms, 'price_level': 'retail'})
    if model_key == 'vendor':
        return _present({'terms': terms})
    return {}


def _present(block: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in block.items() if v not in (None, '')}


def resolve(key: str, value: Any) -> tuple:
    """A default's field and value: ``dt_needed_days: 14`` is ``dt_needed`` two weeks out."""
    if key.endswith('_days'):
        return key[:-len('_days')], int(time.time() * 1000) + int(float(value) * DAY_MS)
    return key, value


def named_term(value: Any) -> str:
    """A company terms default as the Term's own ida; a profile naming no term is a
    configuration fault, refused where it bites with the valid idas (fail fast, never silent)."""
    from apps.accounts.services.terms_ledger import named_term_ida
    try:
        return named_term_ida(value)
    except ValueError as e:
        raise Refused(400, 'invalid_terms', f'The company profile defaults.terms is wrong: {e}',
                      [f'terms: {e}'])


def fill_defaults(obj, model_key: str, data: Dict[str, Any]) -> List[str]:
    """Fill the blank fields of a record this save first gives an ida; the fields filled.
    Called by the save door after the payload is assigned (save._write)."""
    names = {f.name for f in obj._meta.concrete_fields}
    if 'ida' not in names or getattr(obj, 'ida', None):      # already named: the moment has passed
        return []
    filled: List[str] = []
    for key, value in model_defaults(model_key).items():
        field, value = resolve(key, value)
        if field not in names or field in data or getattr(obj, field, None) not in (None, ''):
            continue
        setattr(obj, field, named_term(value) if field == 'terms' else value)
        filled.append(field)
    return filled
