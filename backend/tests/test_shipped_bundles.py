"""The bundles WebClerk ships carry definitions that load: every wc:model definition in them is
for a model that exists, and its access validates as Setting.save would (2026-10-29: 67 of 70
shipped definitions had drifted — fields long gone, a 'manager' role, wildcards — and every
installation that loaded them was refused)."""
import json
from pathlib import Path

import pytest

from apps.core.services import access

BACKEND = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('name', ['init-bundle.json', 'settings-bundle.json'])
def test_every_shipped_definition_validates(name):
    bundle = json.loads((BACKEND / name).read_text())
    problems = {s['parent_model']: p[:3] for s in bundle['settings'] if s.get('purpose') == 'wc:model'
                for p in [access.validate_access(s['parent_model'],
                                                 (s.get('config') or {}).get('access') or {})] if p}
    assert not problems, problems
