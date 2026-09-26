"""A document's ida follows its company sequence format (Bill, 2026-09-26).

Tokens {number} (required) {tag} {yy} {yyyy} {mm}; literal text for a prefix or suffix;
reset "yearly" needs a year token; the year is the company's local date; training keeps -qq.
"""
from datetime import date, datetime, timezone
from unittest import mock

import pytest

from common.ida import (company_today, format_document_ida, next_document_ida,
                        validate_sequences)


SEQ = {'tag': 'inv', 'pad': 4, 'next': 42}


@pytest.mark.parametrize('fmt, expect', [
    (None, '0042-inv'),                                  # today's default, unchanged
    ('{number}-{tag}', '0042-inv'),
    ('{yy}-{number}-{tag}', '26-0042-inv'),
    ('NE-{tag}{yyyy}{mm}-{number}', 'NE-inv202609-0042'),
    ('{number}-{tag}-A', '0042-inv-A'),
])
def test_the_format_builds_the_ida(fmt, expect):
    seq = {**SEQ, **({'format': fmt} if fmt else {})}
    assert format_document_ida(42, seq, on=date(2026, 9, 26)) == expect


def test_a_training_document_keeps_qq_whatever_the_format():
    seq = {**SEQ, 'format': '{yy}-{number}-{tag}'}
    assert format_document_ida(42, seq, training=True, on=date(2026, 1, 2)) == '26-0042-inv-qq'


@pytest.mark.parametrize('seq, words', [
    ({'tag': 'inv', 'format': '{tag}-{yy}'}, 'needs {number}'),
    ({'tag': 'inv', 'format': '{number}-{branch}'}, "['branch']"),
    ({'tag': 'inv', 'format': '{number}-{tag}', 'reset': 'yearly'}, 'needs {yy} or {yyyy}'),
    ({'tag': 'inv', 'format': '{number}', 'reset': 'weekly'}, 'use "yearly"'),
])
def test_a_format_that_cannot_make_unique_idas_is_refused_with_coaching(seq, words):
    with pytest.raises(ValueError) as e:
        validate_sequences({'invoice': seq, 'note': 'a string is skipped'})
    assert words in str(e.value)


def test_the_year_is_the_companys_local_date():
    # 2027-01-01 03:00 UTC is still 2026-12-31 in New York.
    fake_now = datetime(2027, 1, 1, 3, 0, tzinfo=timezone.utc)
    with mock.patch('common.ida.datetime', wraps=datetime) as dt:
        dt.now.side_effect = lambda tz=None: fake_now.astimezone(tz) if tz else fake_now
        assert company_today({'regional': {'timezone': 'America/New_York'}}) == date(2026, 12, 31)
        assert company_today({}) == date(2027, 1, 1)


@pytest.mark.django_db
def test_yearly_reset_starts_over_in_a_new_year_and_saving_a_bad_format_is_refused():
    from django.core.exceptions import ValidationError
    from apps.core.models import Setting
    company = Setting.objects.filter(purpose='wc:company_profile', is_active=True).first()
    if company is None:
        company = Setting(purpose='wc:company_profile', name='Company', config={})
        company._setting_create_authorized = True
        company.save()
    cfg = dict(company.config or {})
    cfg['regional'] = {'timezone': 'America/New_York'}
    cfg['sequences'] = {'invoice': {'tag': 'inv', 'pad': 3, 'next': 57, 'year': 2025,
                                    'format': '{yy}-{number}-{tag}', 'reset': 'yearly'}}
    Setting.objects.filter(pk=company.pk).update(config=cfg)

    with mock.patch('common.ida.company_today', return_value=date(2026, 3, 4)):
        assert next_document_ida('invoice') == '26-001-inv'   # new year: starts over
        assert next_document_ida('invoice') == '26-002-inv'

    company.refresh_from_db()
    company.config = {**company.config, 'sequences': {'invoice': {'tag': 'inv', 'format': '{tag}'}}}
    company._setting_update_authorized = True
    with pytest.raises(ValidationError, match='needs {number}'):
        company.save()
