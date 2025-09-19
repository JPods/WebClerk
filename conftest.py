import os
import pytest

@pytest.fixture(autouse=True)
def _configure_test_db(request, settings):
    if 'PYTEST_KEEP_DB' in os.environ:
        return
    needs_db = (
        request.node.get_closest_marker("django_db")
        or request.node.get_closest_marker("transactional_db")
    )
    if not needs_db:
        return
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'ATOMIC_REQUESTS': False,
    }


def pytest_sessionfinish(session, exitstatus):  # pragma: no cover - reporting utility
    """At end of test session, print a concise summary of any envelope skips.

    This surfaces endpoints that returned raw (legacy) JSON or were exempt so we can
    drive toward 100% standardized responses.
    """
    try:
        from common.middleware import ENVELOPE_SKIPS
    except Exception:
        return
    if not ENVELOPE_SKIPS:
        print("\n[ENVELOPE] All JSON responses were standardized (no skips recorded).")
        return
    # Aggregate by reason
    from collections import Counter
    reason_counts = Counter(s['reason'] for s in ENVELOPE_SKIPS)
    print("\n[ENVELOPE] Skip summary (count by reason):")
    for reason, count in reason_counts.most_common():
        print(f"  - {reason}: {count}")
    # Optionally show first few samples for each reason
    MAX_SHOW = 3
    print("[ENVELOPE] Sample skipped paths:")
    shown = {}
    for rec in ENVELOPE_SKIPS:
        r = rec['reason']
        if shown.get(r, 0) >= MAX_SHOW:
            continue
        print(f"  [{r}] {rec['status']} {rec['path']}")
        shown[r] = shown.get(r, 0) + 1
    pending_raw = reason_counts.get('raw_query', 0)
    if pending_raw:
        print(f"[ENVELOPE] INFO: {pending_raw} raw_query responses used ?raw=1 (transitional clients). Set API_ENVELOPE_ALLOW_RAW=0 to disable.")
