import os

# Ensure Django settings are configured for test imports that access settings at import-time
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webclerk3_api.settings")

# Do not call django.setup() here — let pytest-django manage Django setup and test DB creation.

# Shell scripts that are not pytest tests — exclude from collection
collect_ignore_glob = [
    "test_line_save.py",
    "tests/test_pending_path.py",
    "tests/test_sequence_001.py",
    "tools/test_invoice_trace.py",
    "tools/test_proposal_trace.py",
    "tools/test_wo_trace.py",
]
