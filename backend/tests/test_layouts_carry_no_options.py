"""No layout field carries an option list (Bill, 2026-11-05: "I selected 'low' from the
selectlist. We should not have a difference between the selectlist and approved values").
The form's options and the door's check read one source, the model's selectlists. A layout
with inline options is a second source and the two drift; this fails on the first one back,
in layouts.json, the three shipped bundles, or the stored definitions after migration."""
import json
from pathlib import Path

import pytest

from apps.core.models import Setting

ROOT = Path(__file__).resolve().parent.parent


def _with_options(node, path, out, lists=None):
    """Layout fields carrying options, and — when the definition's lists are given — fields
    typed select that have no list there (the layout's type wins over the behavior's, so such
    a field would draw an empty select; 0066)."""
    if isinstance(node, dict):
        if 'options' in node and node.get('field'):
            out.append(f'{path}/{node["field"]}')
        if lists is not None and node.get('type') == 'select' and node.get('field') and node['field'] not in lists:
            out.append(f'{path}/{node["field"]} (select without a list)')
        for k, v in node.items():
            _with_options(v, f'{path}/{k}', out, lists)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _with_options(v, f'{path}[{i}]', out, lists)
    return out


def test_layouts_json_carries_no_options():
    layouts = json.loads((ROOT / 'apps/core/layouts/layouts.json').read_text())
    assert _with_options(layouts, '', []) == []


@pytest.mark.parametrize('bundle', ['settings-bundle.json', 'init-bundle.json', 'demo-bundle.json'])
def test_the_shipped_bundles_carry_no_layout_options(bundle):
    data = json.loads((ROOT / bundle).read_text())
    found = []
    for item in data['settings']:
        if item.get('purpose') == 'wc:model':
            config = item.get('config') or {}
            _with_options(config.get('layout'), item.get('parent_model', '?'), found, set(config.get('selectlists') or {}))
    assert found == []


@pytest.mark.django_db
def test_the_stored_definitions_carry_no_layout_options():
    found = []
    for s in Setting.objects.filter(purpose='wc:model'):
        _with_options((s.config or {}).get('layout'), s.parent_model, found, set((s.config or {}).get('selectlists') or {}))
    assert found == []
