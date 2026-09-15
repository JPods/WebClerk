import json
import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_schema_integrity_no_diffs():
    """Run the verify_schema management command across all apps and assert no diffs.

    Uses --ignore-extra to tolerate automatically created indexes or columns that
    are not declared (should be none for columns). If legitimate extra/missing
    columns appear this will fail, alerting us early in CI.
    """
    # Capture JSON output by temporarily redirecting stdout via Django's call_command capture.
    from io import StringIO
    buf = StringIO()
    call_command('verify_schema', '--all', '--json', '--types', stdout=buf)
    data = json.loads(buf.getvalue())
    results = data.get('results', [])
    diffs = [r for r in results if not r.get('ok')]
    assert not diffs, f"Schema diffs detected: {diffs}"
