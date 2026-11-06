"""A fresh install's forms work (the lead's item 2, 2026-11-06): an empty database, migrated,
seeded the way a new company's is (seed_freshstart + init-bundle.json), then every stored
definition scanned — no form field the door refuses, no select without a list, no lookup on
an unregistered model, no stored behavior lagging the code, no layout carrying options. The
scan is definition_scan.py; the same scan audits a live database through manage.py
scan_definitions.

The seeding happens inside this test's own transaction and is rolled back with it: a
module-scoped fixture that committed through django_db_blocker left a whole install behind,
and every later test in the same database that did Setting.get() found three (the lead's
cohort 1 on 33191a2: nine failures, all pollution)."""
import pytest
from django.core.management import call_command

from apps.core.services.definition_scan import scan

pytestmark = pytest.mark.django_db


def test_a_fresh_install_has_no_form_a_door_refuses_and_no_empty_select():
    call_command('seed_freshstart', verbosity=0)
    call_command('unpack_init_bundle', verbosity=0)
    found = scan()
    assert found == {'refused': [], 'no_list': [], 'no_model': [], 'stale': [], 'inline': []}
