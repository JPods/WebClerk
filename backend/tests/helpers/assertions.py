"""WebClerk test assertion helpers.

Envelope-first assertions that enforce the WC3 contract:
- JSON envelope is the only source of truth
- All datetimes UTC ISO-8601 with Z suffix
- No scalar fallbacks — missing JSON = error, never silent substitution
"""
import re
from datetime import datetime, timezone


# ISO-8601 UTC with Z suffix: 2026-08-31T12:00:00Z or 2026-08-31T12:00:00.000Z
_UTC_PATTERN = re.compile(
    r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$'
)


def assert_utc_iso8601(value, *, field_name=''):
    """Assert a datetime string is UTC ISO-8601 with Z suffix.

    Accepts both string values and datetime objects.
    Returns the parsed datetime for further assertions.
    """
    label = f" (field: {field_name})" if field_name else ""

    if isinstance(value, datetime):
        assert value.tzinfo is not None, (
            f"Datetime has no timezone{label}: {value!r}"
        )
        assert value.tzinfo == timezone.utc or value.utcoffset().total_seconds() == 0, (
            f"Datetime is not UTC{label}: {value!r}"
        )
        return value

    assert isinstance(value, str), (
        f"Expected datetime string, got {type(value).__name__}{label}: {value!r}"
    )
    assert _UTC_PATTERN.match(value), (
        f"Datetime not UTC ISO-8601 with Z suffix{label}: {value!r}"
    )
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def assert_json_envelope_shape(record, model_name=None):
    """Assert a record from wcapi response has the expected JSON envelope fields.

    Every BaseModel record should have metadata, refs, prefs, and comments
    as JSON dict fields (possibly empty dicts, never None).
    """
    assert isinstance(record, dict), f"Record not dict: {type(record).__name__}"

    for field in ('metadata', 'refs'):
        val = record.get(field)
        assert isinstance(val, dict), (
            f"record['{field}'] should be dict, got {type(val).__name__}: {val!r}"
        )

    if model_name:
        assert 'id' in record, f"Record missing 'id' for model {model_name}"


def assert_no_scalar_fallback(response_body):
    """Assert the response body is a proper envelope dict, not a list or scalar.

    The wcapi contract: every response is {status, code, message, data}.
    Never a bare list. Never a scalar. Never None.
    """
    assert isinstance(response_body, dict), (
        f"Response is {type(response_body).__name__}, not dict envelope: "
        f"{str(response_body)[:200]}"
    )
    assert 'status' in response_body, (
        f"Response missing 'status' key — not a valid envelope: "
        f"{list(response_body.keys())}"
    )
    assert response_body['status'] in ('success', 'fail', 'error'), (
        f"Invalid envelope status: {response_body['status']!r}"
    )
