import io
import json
import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_profile_api_validation_json_output():
    out = io.StringIO()
    call_command('profile_api_validation', '--iterations', '5', '--json', stdout=out)
    data = json.loads(out.getvalue())
    assert isinstance(data, list)
    # Each row should contain required keys if present
    if data:
        sample = data[0]
        for key in ['app', 'model', 'iterations', 'avg_ms', 'p95_ms', 'max_ms', 'min_ms', 'custom']:
            assert key in sample