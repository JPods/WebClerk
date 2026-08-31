import os

# Ensure Django settings are configured for test imports that access settings at import-time
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webclerk3_api.settings")

# Do not call django.setup() here — let pytest-django manage Django setup and test DB creation.

# All former shell-script exclusions have been deleted.
# If new non-test files appear, add them here.
