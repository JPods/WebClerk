"""Fable #4 + Bill, 2026-09-26: refs.links elements are rich {} built by one writer
(link_entry) from one definition (get_denorm_fields); normalize_links rewrites stored lists."""
from io import StringIO

import pytest
from django.core.management import call_command

from common.denorm_registry import DENORM_REGISTRY, ORG_ROLE_KEYS, get_denorm_fields, link_entry


def test_every_field_a_link_copies_exists_on_its_source_model():
    """The ratchet: a renamed or removed field cannot linger in a snapshot definition."""
    from apps.core.management.commands.normalize_links import _source_model
    missing = {}
    for bucket in sorted(set(DENORM_REGISTRY) | ORG_ROLE_KEYS | {'orgbase', 'contact'}):
        model = _source_model(bucket)
        assert model is not None, f'{bucket}: no source model'
        names = {f.name for f in model._meta.get_fields()} | \
                {getattr(f, 'attname', None) for f in model._meta.get_fields()} | \
                {n for n in dir(model) if isinstance(getattr(model, n, None), property)}
        bad = [f for f in get_denorm_fields(bucket) if f != f.strip() or f not in names]
        if bad:
            missing[bucket] = bad
    assert not missing, missing


def test_contact_links_read_the_models_own_definition():
    """apps.get_model('contact') without an app label always raised, so the stale registry
    copy was used instead of Contact.DENORM_FIELDS."""
    from apps.core.models import Contact
    from apps.orgs.models import OrgBase
    assert get_denorm_fields('contact') == list(Contact.DENORM_FIELDS)
    assert get_denorm_fields('customer') == list(OrgBase.DENORM_FIELDS)


@pytest.mark.django_db
def test_an_invoices_line_links_are_id_dicts_in_one_shape():
    from apps.transactions.models import Invoice, InvoiceLine
    inv = Invoice.objects.create(finance={"sales_tax_rate": 0})
    a = InvoiceLine.objects.create(invoice=inv, quantity={"active": 1}, price={"unit": 1.0})
    b = InvoiceLine.objects.create(invoice=inv, quantity={"active": 1}, price={"unit": 2.0})
    inv.refresh_from_db()
    assert inv.refs['links']['invoice_line'] == [{'id': a.pk}, {'id': b.pk}]


@pytest.mark.django_db
def test_normalize_rebuilds_mixed_lists_drops_dead_links_and_leaves_history_alone():
    from apps.core.models import Contact
    from apps.orgs.models import OrgBase
    person = Contact.objects.create(email='now@example.com', name_first='Now', name_last='Name')
    org = OrgBase.objects.create(company='Mixed Co', org_type='customer', is_active=True)
    stale = [{'purpose': 'primary', 'contact_id': person.pk, 'display_name': 'Old Name'},
             {'id': person.pk, 'name': 'x'}, 10 ** 9]
    OrgBase.objects.filter(pk=org.pk).update(refs={'links': {'contact': stale}})

    out = StringIO()
    call_command('normalize_links', apply=True, stdout=out)
    org.refresh_from_db()
    links = org.refs['links']['contact']
    assert len(links) == 1, 'the duplicate collapses and the dead link is dropped'
    assert links[0]['id'] == person.pk and links[0]['purpose'] == 'primary'
    assert links[0] == {**link_entry(person, 'contact'), 'purpose': 'primary'}
    assert 'dropped' in out.getvalue()


def test_normalize_is_scheduled_weekly():
    from apps.support.scheduler.registry import build_celery_beat_schedule
    assert build_celery_beat_schedule()['normalize-links-weekly']['task'].endswith('task_normalize_links')
