"""A fresh install's forms work (the lead's item 2, 2026-11-06): an empty database, migrated,
seeded the way a new company's is (seed_freshstart + init-bundle.json), then every stored
definition scanned — no form field the door refuses, no select without a list, no lookup on
an unregistered model, no stored behavior lagging the code. The scan is definition_scan.py;
the same scan audits a live database through manage.py scan_definitions."""
import pytest
from django.core.management import call_command

from apps.core.services.definition_scan import scan

pytestmark = pytest.mark.django_db


@pytest.fixture(scope='module')
def fresh_install(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('seed_freshstart', verbosity=0)
        call_command('unpack_init_bundle', verbosity=0)
    yield


def test_a_fresh_install_has_no_form_a_door_refuses_and_no_empty_select(fresh_install):
    found = scan()
    assert found == {'refused': [], 'no_list': [], 'no_model': [], 'stale': []}
