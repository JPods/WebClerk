"""Superusers change Setting records (Bill, 2026-09-29).

A Setting's config is untyped, so its schema names only config.layout.* and config.is_new;
the edit enumeration trimmed a superuser's company-profile save to nothing and answered 200
(audit A3-H-2). The company's pay_to, sequences and access lists could not be changed.
"""
import pytest
from rest_framework.test import APIClient

from apps.core.models import Contact, Setting

pytestmark = pytest.mark.django_db


def _client(**flags):
    user = Contact.objects.create(email=f"{'su' if flags.get('is_superuser') else 'x'}@example.com",
                                  **flags)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _profile():
    setting, _ = Setting.objects.get_or_create(
        ida='company-profile', purpose='wc:company_profile',
        defaults={'name': 'company_profile', 'config': {'company': {'name': 'Test Co'}}})
    return setting


def test_a_superuser_changes_the_company_pay_to():
    profile = _profile()
    pay_to = {'name': 'Test Co', 'address_full': 'PO Box 9, Tulsa, OK 74101'}
    config = dict(profile.config or {})
    config['company'] = {**(config.get('company') or {}), 'pay_to': pay_to}
    response = _client(is_superuser=True, is_staff=True).put(
        f'/wcapi/setting/{profile.pk}/', {'config': config, 'version': profile.version}, format='json')
    assert response.status_code == 200, response.content
    profile.refresh_from_db()
    assert profile.config['company']['pay_to'] == pay_to


def test_a_non_superuser_still_cannot_change_a_setting():
    profile = _profile()
    before = dict(profile.config or {})
    response = _client(role='admin', is_staff=True).put(
        f'/wcapi/setting/{profile.pk}/', {'config': {**before, 'company': {'name': 'Hijack'}}},
        format='json')
    assert response.status_code == 403
    profile.refresh_from_db()
    assert profile.config.get('company', {}).get('name') != 'Hijack'
