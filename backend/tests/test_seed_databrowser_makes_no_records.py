"""seed_databrowser seeds layouts only. Every record is a real record (Bill, 2026-11-13):
a fresh start must not plant a placeholder customer, item or account in the books."""
import pytest
from django.core.management import call_command

from apps.core.constants.model_registry import MODEL_REGISTRY, get_model_meta
from apps.core.models.setting import Setting

pytestmark = pytest.mark.django_db


def _counts():
    counts = {}
    for key in MODEL_REGISTRY:
        try:
            model = get_model_meta(key).import_model()
        except Exception:
            continue
        if model is Setting:
            continue
        counts[model._meta.label] = model.objects.count()
    return counts


def test_seed_databrowser_seeds_layouts_and_no_records():
    before = _counts()
    call_command('seed_databrowser', verbosity=0)
    assert _counts() == before
    assert Setting.objects.filter(purpose='wc:workbench_fields', parent_model='customer').exists()
    assert not Setting.objects.filter(purpose='fake_seed').exists()


def test_seed_databrowser_has_no_fakes_switch():
    with pytest.raises(Exception):
        call_command('seed_databrowser', fakes=True, verbosity=0)
