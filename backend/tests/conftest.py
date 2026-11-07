"""Shared test fixtures and factories for wc3 test suite.

Usage in tests::

    def test_customer_creation(customer):
        assert customer.org_type == "customer"
        assert customer.is_active is True

    def test_order_with_lines(order, order_line_factory):
        line = order_line_factory(order=order)
        assert line.order == order
"""
import pytest
import factory
from factory.django import DjangoModelFactory
from tests.utils import wcapi_get


# ---------------------------------------------------------------------------
# Org factories
# ---------------------------------------------------------------------------

class OrgBaseFactory(DjangoModelFactory):
    class Meta:
        model = "orgs.OrgBase"

    company = factory.Sequence(lambda n: f"Org {n}")
    org_type = "customer"
    is_active = True


class CustomerFactory(OrgBaseFactory):
    org_type = "customer"
    company = factory.Sequence(lambda n: f"Customer {n}")


class VendorFactory(OrgBaseFactory):
    org_type = "vendor"
    company = factory.Sequence(lambda n: f"Vendor {n}")


# ---------------------------------------------------------------------------
# Core factories
# ---------------------------------------------------------------------------

class ContactFactory(DjangoModelFactory):
    class Meta:
        model = "core.Contact"

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    name_first = factory.Faker("first_name")
    name_last = factory.Faker("last_name")
    is_active = True


class ActionFactory(DjangoModelFactory):
    class Meta:
        model = "core.Action"

    name = factory.Sequence(lambda n: f"Action {n}")
    purpose = "test"
    is_active = True


# ---------------------------------------------------------------------------
# Product factories
# ---------------------------------------------------------------------------

class ItemFactory(DjangoModelFactory):
    class Meta:
        model = "products.Item"

    ida = factory.Sequence(lambda n: f"ITEM-{n:04d}")
    description = factory.Faker("sentence", nb_words=4)
    is_active = True


class WarehouseFactory(DjangoModelFactory):
    class Meta:
        model = "products.Warehouse"

    name = factory.Sequence(lambda n: f"Warehouse {n}")
    code = factory.Sequence(lambda n: f"WH{n:03d}")
    is_active = True


# ---------------------------------------------------------------------------
# Transaction factories
# ---------------------------------------------------------------------------

class OrderFactory(DjangoModelFactory):
    class Meta:
        model = "transactions.Order"

    ida = factory.Sequence(lambda n: f"SO-{n:05d}")
    status = "open"
    is_active = True


class OrderLineFactory(DjangoModelFactory):
    class Meta:
        model = "transactions.OrderLine"

    order = factory.SubFactory(OrderFactory)
    ida = factory.Sequence(lambda n: f"SOL-{n:05d}")
    status = "open"
    is_active = True


class InvoiceFactory(DjangoModelFactory):
    class Meta:
        model = "transactions.Invoice"

    ida = factory.Sequence(lambda n: f"INV-{n:05d}")
    status = "open"
    is_active = True


class QuoteFactory(DjangoModelFactory):
    class Meta:
        model = "transactions.Quote"

    ida = factory.Sequence(lambda n: f"QT-{n:05d}")
    status = "open"
    is_active = True


class PurchaseFactory(DjangoModelFactory):
    class Meta:
        model = "transactions.Purchase"

    ida = factory.Sequence(lambda n: f"PO-{n:05d}")
    status = "open"
    is_active = True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def chart_of_accounts(db):
    """The standard chart (GlAccount rows) plus a company profile whose
    config.gl_defaults maps every posting role to a chart account — as a new database
    gets them (apps/accounts/charts/standard.json). Returns the role map."""
    from django.apps import apps
    from apps.accounts.services import chart
    from apps.core.models import Setting

    if not Setting.objects.filter(purpose='wc:company_profile').exists():
        company = Setting(ida='company-profile', name='Company Profile', purpose='wc:company_profile',
                          scope='system', config={})
        company._setting_create_authorized = True
        company.save()
    standard = chart.standard_chart()
    GlAccount = apps.get_model('accounts', 'GlAccount')
    if not GlAccount.objects.exists():
        result = chart.install(standard)
        assert result['errors'] == [], result['errors']
    else:                       # a class that keeps its data between tests installed it already
        missing = {a['ida'] for a in standard['accounts']} - set(GlAccount.objects.values_list('ida', flat=True))
        assert not missing, f'the chart in this test database lacks {sorted(missing)}'
        company = Setting.objects.filter(purpose='wc:company_profile').first()
        company.config = {**(company.config or {}), 'gl_defaults': dict(standard['roles'])}
        company.save()
    return standard['roles']


@pytest.fixture
def customer(db):
    """A single active customer org."""
    return CustomerFactory()


@pytest.fixture
def vendor(db):
    """A single active vendor org."""
    return VendorFactory()


@pytest.fixture
def contact(db):
    """A single active contact/user."""
    return ContactFactory()


@pytest.fixture
def item(db):
    """A single active product item."""
    return ItemFactory()


@pytest.fixture
def warehouse(db):
    """A single active warehouse."""
    return WarehouseFactory()


@pytest.fixture
def order(db):
    """A single active sales order."""
    return OrderFactory()


@pytest.fixture
def invoice(db):
    """A single active invoice."""
    return InvoiceFactory()


@pytest.fixture
def quote(db):
    """A single active quote/quote."""
    return QuoteFactory()


@pytest.fixture
def purchase(db):
    """A single active purchase order."""
    return PurchaseFactory()


# Factory fixtures (for creating multiple instances in a test)

@pytest.fixture
def customer_factory(db):
    """Factory for creating customer orgs."""
    return CustomerFactory


@pytest.fixture
def order_line_factory(db):
    """Factory for creating order lines."""
    return OrderLineFactory


@pytest.fixture
def item_factory(db):
    """Factory for creating product items."""
    return ItemFactory


# ---------------------------------------------------------------------------
# Auth & WCAPI fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def authenticated_client(db):
    """APIClient authenticated as a superuser via force_authenticate."""
    from tests.helpers.auth import make_authenticated_client
    return make_authenticated_client()


class _WcapiNamespace:
    """Convenience wrapper: wcapi.save('contact', {...}) etc."""

    def __init__(self, client):
        self._client = client

    def save(self, model, data):
        return self._client.post(
            '/wcapi/save', {'model': model, 'data': data}, format='json'
        )

    def get(self, model, **params):
        params['model_name'] = model
        return wcapi_get(self._client, params)

    def query(self, model, filters=None):
        return self._client.post(
            '/wcapi/query', {'model': model, 'filters': filters or {}},
            format='json',
        )

    def delete(self, model, ids):
        return self._client.delete(
            f'/{model}/', data={'ids': ids}, format='json'
        )


@pytest.fixture
def wcapi(authenticated_client):
    """WCAPI helper namespace bound to an authenticated client.

    Usage::

        def test_create_contact(wcapi):
            resp = wcapi.save('contact', {'email': 'a@b.com'})
            assert resp.status_code == 200
    """
    return _WcapiNamespace(authenticated_client)


@pytest.fixture
def model_defaults(chart_of_accounts):
    """Every document and org model has its definition with the shipped defaults block
    (core/services/defaults.SHIPPED_FIELDS; readme 106 A) and N30 is a Term, so a record born
    through the door gets terms, level, dt_needed and priority as wc_demo's would."""
    from apps.accounts.models import Term
    from apps.core.models import Setting
    from apps.core.services import definition
    from apps.core.services.defaults import SHIPPED_FIELDS, shipped_defaults
    Term.objects.get_or_create(ida='N30', defaults={'name': 'N30', 'is_active': True})
    made = {}
    for model_key in SHIPPED_FIELDS:
        setting = Setting.objects.filter(purpose='wc:model', parent_model=model_key).first()
        if setting is None:
            setting = make_setting(purpose='wc:model', parent_model=model_key, name=model_key,
                                   config={'defaults': shipped_defaults(model_key)})
        else:
            setting.config = {**(setting.config or {}), 'defaults': shipped_defaults(model_key)}
            setting._setting_create_authorized = True
            setting.save()
        made[model_key] = setting
    definition.clear()
    yield made
    definition.clear()


def make_setting(**kwargs):
    """Create a Setting in a test.

    Setting.save() requires explicit authorization (apps/core/models/setting.py) so that
    no code path creates settings by accident. Tests are a deliberate caller, so they
    authorize once, here, instead of each test learning the flag.
    """
    from apps.core.models import Setting
    setting = Setting(**kwargs)
    setting._setting_create_authorized = True
    setting.save()
    return setting


def make_saved_search(*, name, model_name, role="", config=None, is_active=True, **kwargs):
    """Create a stored search in a test.

    A stored search is a Report record marked `purpose='search_stored'`
    (Bill, 2026-09-20). It used to be a Setting with `purpose='wc:search'`, or an
    entry in UserProfile.prefs.search[]; migration core.0011 brought both into
    Report and the read path now filters on the marker, so a fixture that creates
    a Setting is creating something the system no longer recognises.

    A search belongs to no person (Bill, 2026-10-28); role set = shared with that role.
    """
    from apps.core.models.report import Report
    from apps.core.services.report_registry import REPORT_PURPOSE_SEARCH

    spec = dict(config or {})
    return Report.objects.create(
        name=name,
        target_model=model_name,
        purpose=REPORT_PURPOSE_SEARCH,
        category=kwargs.pop("category", "search"),
        output_type=kwargs.pop("output_type", "search"),
        role_required=role,
        config=spec,
        is_active=is_active,
        **kwargs,
    )


@pytest.fixture(autouse=True)
def _company_profile_cache_per_test():
    """price_resolver caches the company profile (an item save pays no query for the cost
    basis); one test's profile must not be the next test's."""
    from apps.core.services.cache import cache_service
    cache_service.invalidate_namespace('company_profile')
    yield
    cache_service.invalidate_namespace('company_profile')
