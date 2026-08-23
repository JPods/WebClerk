import pytest
from apps.communications.models.address import Address
from django.db import transaction

pytestmark = pytest.mark.unit


def make_loc(**kw):
    return Address(**{
        'address1': '123 Main St',
        'address2': 'Apt 5',
        'city': 'Springfield',
        'state': 'IL',
        'zip': '62704',
        'country': 'US',
        **kw
    })


def test_full_us_basic():
    loc = make_loc()
    assert loc.full_us() == '123 Main St, Apt 5, Springfield, IL 62704'
    assert loc.lines_us() == ['123 Main St', 'Apt 5', 'Springfield, IL 62704']


def test_full_eu_basic():
    loc = make_loc(country='DE', state='BY', zip='80331', city='München')
    assert loc.full_eu() == '123 Main St, Apt 5, 80331 München, BY'
    assert loc.lines_eu() == ['123 Main St', 'Apt 5', '80331 München', 'BY']


def test_format_auto_includes_country_when_foreign():
    us = make_loc()
    de = make_loc(country='Germany', state='BY', zip='80331', city='München')
    assert us.format_auto() == '123 Main St, Apt 5, Springfield, IL 62704'
    assert de.format_auto().endswith('Germany')


def test_as_standard_auto_switches():
    us = make_loc()
    d = us.as_standard('auto')
    assert d['standard'] == 'us'
    assert d['full'] == '123 Main St, Apt 5, Springfield, IL 62704'
    assert d['parts']['city'] == 'Springfield'
    
    eu = make_loc(country='FR', city='Paris', state='Île-de-France', zip='75001')
    d2 = eu.as_standard('auto')
    assert d2['standard'] == 'eu'
    assert 'Paris' in d2['full']


def test_metadata_display_full_location_is_set(db):
    loc = Address(
        address1='1600 Pennsylvania Ave NW',
        city='Washington', state='DC', zip='20500', country='USA'
    )
    loc.save()
    assert isinstance(loc.metadata, dict)
    disp = loc.metadata.get('display', {})
    assert disp.get('full_location', '').startswith('1600 Pennsylvania Ave')
    assert disp.get('country_code') == 'US'


def test_metadata_display_for_eu_example(db):
    loc = Address(
        address1='55 Rue du Faubourg Saint-Honoré',
        city='Paris', state='Île-de-France', zip='75008', country='France'
    )
    loc.save()
    disp = loc.metadata.get('display', {})
    assert disp.get('full_location')
    assert disp.get('country_code') in ('FR', 'FRANCE'[:2])
