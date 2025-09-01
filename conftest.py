import os
import pytest
from django.conf import settings

# Force lightweight SQLite for tests unless explicitly disabled
@pytest.fixture(scope='session', autouse=True)
def _configure_test_db():
    if 'PYTEST_KEEP_DB' in os.environ:
        return
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
