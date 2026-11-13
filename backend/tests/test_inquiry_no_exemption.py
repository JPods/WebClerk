"""No mailbox is exempt from an inquiry form's limits (Bill, 2026-11-13: zz and qq removed)."""
import importlib

import pytest
from pydantic import ValidationError

from apps.core.models.action_pydantic import InquiryLimits


def test_limits_have_no_tester_list():
    assert 'testing' not in InquiryLimits.model_fields
    with pytest.raises(ValidationError):
        InquiryLimits.model_validate({'testing': [{'email': 'a@b.c', 'until_utc': '2030-01-01T00:00:00Z'}]})


def test_the_view_has_no_exemption():
    from apps.core.views import inquiry_view
    assert not hasattr(inquiry_view, '_tester')


@pytest.mark.django_db
def test_migration_strips_a_stored_tester_list():
    from django.apps import apps
    from apps.core.models import Report
    report = Report.objects.create(name='exemption test form', category='form', config={'inquiry': {'limits': {
        'testing': [{'email': 'a@b.c', 'until_utc': '2026-10-19T04:59:59Z'}],
        'one_open_per_contact': True, 'links_per_mailbox_per_day': 3}}})
    untouched = Report.objects.create(name='plain form', category='form',
                                      config={'inquiry': {'limits': {'links_per_mailbox_per_day': 5}}})
    migration = importlib.import_module('apps.core.migrations.0074_inquiry_forms_drop_tester_exemption')
    migration.forward(apps, None)
    report.refresh_from_db()
    untouched.refresh_from_db()
    assert report.config['inquiry']['limits'] == {'one_open_per_contact': True, 'links_per_mailbox_per_day': 3}
    InquiryLimits.model_validate(report.config['inquiry']['limits'])
    assert untouched.config['inquiry']['limits'] == {'links_per_mailbox_per_day': 5}
