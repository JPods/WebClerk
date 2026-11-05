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
