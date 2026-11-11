"""The sweep (readme 106 step 4): existing records get the defaults they were born without;
a value off its list is reported, never rewritten; the
profile's unread currency keys go. Alice's check (watch_defaults) uses the same finder."""
import os

import pytest
from django.core.management import call_command
from io import StringIO

from apps.core.models import Setting
from apps.core.services import defaults_sweep, select_lists
from apps.core.services.door import Actor
from apps.orgs.models import Customer
from apps.transactions.models import Quote

pytestmark = pytest.mark.django_db

DAY_MS = 86_400_000


@pytest.fixture
def admin(django_user_model):
    return django_user_model.objects.create_superuser(
        email='sweep@example.com', password=None, name_first='Swe', name_last='Ep', username='')


def _as(user):
    return Actor(user=user, kind='user', source='wcapi')


def _by(findings, model, field, kind='blank'):
    return next((f for f in findings if f.model == model and f.field == field and f.kind == kind), None)


def test_the_sweep_finds_and_fills_what_was_born_outside_the_door(admin, model_defaults):
    bare = Quote.objects.create(finance={'sales_tax_rate': 0})            # outside the door: no defaults
    assert (bare.terms, bare.priority, bare.dt_needed) == (None, None, None)
    found = defaults_sweep.find_blanks()
    terms = _by(found, 'quote', 'terms')
    assert terms.count == 1 and terms.ids == [bare.pk] and terms.value == 'N30'
    assert _by(found, 'quote', 'dt_needed').value == 'dt_needed_days'
    written = defaults_sweep.apply(found)
    bare.refresh_from_db()
    assert (bare.terms, bare.price_level, bare.priority) == ('N30', 'retail', 'medium')
    assert bare.dt_needed == bare.dt_created + 14 * DAY_MS, 'born plus the days, from its own birth'
    assert written['quote.terms'] == 1 and written['quote.dt_needed'] == 1
    assert defaults_sweep.find_blanks() == [] or all(f.model != 'quote' for f in defaults_sweep.find_blanks())


def test_a_document_the_lock_covers_is_kept_and_a_swept_one_bumps_its_version(admin, model_defaults):
    """The lead's review: terms on a released or journalized invoice moves its due date after
    the books took it — the sweep never writes past the lock; and every write bumps version and
    dt_modified so an open form meets the version check instead of saving over the fill."""
    from apps.transactions.models import Invoice
    released = Invoice.objects.create(finance={'sales_tax_rate': 0}, status='released')
    journaled = Invoice.objects.create(finance={'sales_tax_rate': 0}, status='planned', dt_journaled=1_700_000_000_000)
    locked = Invoice.objects.create(finance={'sales_tax_rate': 0}, status='planned',
                                    metadata={'health': {'lock': {'dt': 1, 'by': {'id': 1, 'name': 'x'}, 'reason': 'audit', 'status_before': 'planned'}}})
    done = Invoice.objects.create(finance={'sales_tax_rate': 0}, status='complete')
    open_ = Invoice.objects.create(finance={'sales_tax_rate': 0}, status='planned')
    before = (open_.version, open_.dt_modified)
    found = defaults_sweep.find_blanks()
    assert _by(found, 'invoice', 'terms').ids == [open_.pk]
    assert sorted(_by(found, 'invoice', 'terms', 'kept').ids) == sorted([released.pk, journaled.pk, locked.pk, done.pk])
    defaults_sweep.apply(found)
    for doc in (released, journaled, locked, done):
        doc.refresh_from_db(); assert doc.terms is None, doc.status
    open_.refresh_from_db()
    assert open_.terms == 'N30' and open_.version > before[0] and open_.dt_modified > before[1], 'one bump per field filled'


def test_a_value_off_its_list_is_reported_never_rewritten(admin, model_defaults):
    select_lists.replace_list('quote', 'priority', [{'value': 'low'}, {'value': 'medium'}], actor=_as(admin))
    odd = Quote.objects.create(finance={'sales_tax_rate': 0}, priority='rush')
    found = defaults_sweep.find_all()
    off = _by(found, 'quote', 'priority', 'unlisted')
    assert off.count == 1 and off.value == 'rush' and off.ids == [odd.pk]
    defaults_sweep.apply(found)
    odd.refresh_from_db()
    assert odd.priority == 'rush'


def test_the_profiles_unread_currency_keys_go_and_the_precisions_stay(model_defaults):
    company = Setting.objects.get(purpose='wc:company_profile')
    company.prefs = {**(company.prefs or {}), 'currency': {'code': 'USD', 'locale': 'en-US', 'symbol': '$', 'qty_precision': 0, 'unit_cost_precision': 5}}
    company._setting_create_authorized = True
    company.save()
    found = defaults_sweep.find_profile_currency()
    assert found and found[0].value == ['code', 'locale', 'symbol']
    defaults_sweep.apply(found)
    company.refresh_from_db()
    assert company.prefs['currency'] == {'qty_precision': 0, 'unit_cost_precision': 5}
    assert defaults_sweep.find_profile_currency() == []


def test_the_command_is_a_dry_run_unless_a_backup_is_named(admin, model_defaults, tmp_path):
    from django.core.management.base import CommandError
    bare = Quote.objects.create(finance={'sales_tax_rate': 0})
    out = StringIO()
    call_command('sweep_defaults', stdout=out)
    assert 'Dry run' in out.getvalue() and 'quote.terms' in out.getvalue()
    bare.refresh_from_db(); assert bare.terms is None
    with pytest.raises(CommandError, match='backup'):
        call_command('sweep_defaults', '--apply', stdout=StringIO())
    dump = tmp_path / 'wc.dump'; dump.write_bytes(b'x')
    out = StringIO()
    call_command('sweep_defaults', '--apply', '--backup', str(dump), stdout=out)
    bare.refresh_from_db(); assert bare.terms == 'N30'
    assert 'Applied' in out.getvalue()


def test_alices_check_observes_each_finding_once(admin, model_defaults):
    from apps.ai_assistant.models.alice import AliceObservation
    from apps.ai_assistant.services.watch_defaults import check_defaults
    Quote.objects.create(finance={'sales_tax_rate': 0})
    Customer.objects.create(company='Bare Co')                             # no terms, no level
    first = check_defaults()
    assert first['blank_rows'] >= 2 and first['observations'] >= 2
    assert AliceObservation.objects.filter(category='defaults', dedup_key='defaults:blank:customer.terms').count() == 1
    again = check_defaults()
    assert again['observations'] == 0, 'deduplicated while unresolved'
