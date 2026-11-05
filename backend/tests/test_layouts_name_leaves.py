"""A form names what the record carries (readme 105 step 1, 2026-11-05).

A dotted form field must be a declared leaf: a dotted name no envelope declares is a guess,
and the field shows empty for everyone. The pending form named changes.doc_id, changes.line_id
and changes.reason; no pending carries them (its changes differ by purpose), so it shows
changes as one JSON field. The same check over every model in layouts.json is an audit, not a
test, until the line-card and panel fields are read against their own models (plan 101).
"""
import pytest

from apps.core.constants.model_registry import get_model_meta
from apps.core.layouts import designed
from apps.core.services import field_leaves as fl

pytestmark = pytest.mark.django_db


def _fields(node, out):
    if isinstance(node, dict):
        if isinstance(node.get('field'), str) and ('type' in node or 'width' in node or 'label' in node):
            out.add(node['field'])
        for v in node.values():
            _fields(v, out)
    elif isinstance(node, list):
        for x in node:
            _fields(x, out)
    return out


def unknown_fields(model_key, layout):
    """Names in `layout` that are neither a leaf, a field nor a property of the model."""
    leaves = fl.model_leaves(model_key)['leaves']
    model = get_model_meta(model_key).import_model()
    names = {f.name for f in model._meta.get_fields()} | {a for a in dir(model) if not a.startswith('_')}
    out = []
    for f in _fields(layout, set()):
        ok = f in leaves or any(l.startswith(f + '.') for l in leaves) or ('.' not in f and f in names)
        if not ok:
            out.append(f)
    return sorted(out)


def test_the_pending_form_names_what_a_pending_carries():
    assert unknown_fields('pending', designed()['pending']['form']) == []


CARD_FIELDS = {'email', 'phone', 'address_full', 'domain', 'attention'}   # opened in a card, never typed


def refused_on_save(model_key, layout):
    """Editable form fields the door would refuse: no concrete field, no declared leaf."""
    leaves = fl.model_leaves(model_key)['leaves']
    model = get_model_meta(model_key).import_model()
    concrete = {f.name for f in model._meta.concrete_fields} | {f.attname for f in model._meta.concrete_fields}
    out = []
    for sec in (layout.get('default') or {}).get('sections', []):
        for col in sec.get('columns', []):
            for f in col.get('fields', []):
                name = f.get('field')
                if not name or f.get('type') == 'readonly' or name in CARD_FIELDS:
                    continue
                ok = (name in concrete or name in leaves or any(l.startswith(name + '.') for l in leaves)
                      or ('.' in name and name.split('.')[0] in concrete))
                if not ok:
                    out.append(name)
    return sorted(out)


@pytest.mark.parametrize('model_key', sorted(designed().keys()))
def test_every_editable_form_field_is_one_the_door_accepts(model_key):
    """Bill, 2026-11-05: "saving customer is not working" — the form edited display_name, a
    property; the door refused it. A layout edits only what the model has."""
    assert refused_on_save(model_key, designed()[model_key].get('form') or {}) == []
