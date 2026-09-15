import pytest
from common.models import BaseModel, CoreModel, model_capabilities, AtomicJSONMixin
from apps.core.models.pending import Pending
from apps.core.models.action import Action

@pytest.mark.django_db
def test_capabilities_full_base_model():
    caps = set(model_capabilities(Action))
    # Expect all main feature flags for BaseModel composition
    for expected in {"metadata","refs","prefs","comments","health","keywords","lifecycle","core","universal_dict","atomic_json"}:
        assert expected in caps

@pytest.mark.django_db
def test_capabilities_core_only():
    caps = set(model_capabilities(Pending))
    assert caps == {"core"}

@pytest.mark.django_db
def test_atomic_methods_absent_on_core_only():
    # Pending has no metadata/refs/prefs/comments fields, calling atomic_json_set with one should error
    p = Pending.objects.create()
    assert not hasattr(Pending, 'atomic_json_set')
    # Control: Action supports atomic update
    obj = Action.objects.create(action="Check Atomic")
    updated, new_version = Action.atomic_json_set(obj.pk, 'metadata', ['flags','schema_rev'], 2)
    assert updated == 1
    assert isinstance(new_version, int)
