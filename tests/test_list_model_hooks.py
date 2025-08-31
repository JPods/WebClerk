import io
import pytest
from django.core.management import call_command
from django.apps import apps


@pytest.mark.django_db
@pytest.mark.hooks
def test_list_model_hooks_includes_phone_model():
    # Capture command output
    out = io.StringIO()
    call_command('list_model_hooks', stdout=out)
    output = out.getvalue()
    # Phone model should appear with custom pre_save_hook
    assert 'Phone' in output
    # We know phone overrides all three hooks -> expect 'custom' at least once
    assert 'custom' in output