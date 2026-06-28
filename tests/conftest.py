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


# ---------------------------------------------------------------------------
# Org factories
# ---------------------------------------------------------------------------

class OrgBaseFactory(DjangoModelFactory):
    class Meta:
        model = "orgs.OrgBase"

    display_name = factory.Sequence(lambda n: f"Org {n}")
    org_type = "customer"
    is_active = True
    is_deleted = False


class CustomerFactory(OrgBaseFactory):
    org_type = "customer"
    display_name = factory.Sequence(lambda n: f"Customer {n}")


class VendorFactory(OrgBaseFactory):
    org_type = "vendor"
    display_name = factory.Sequence(lambda n: f"Vendor {n}")


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
    is_deleted = False


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
    is_deleted = False


class OrderLineFactory(DjangoModelFactory):
    class Meta:
        model = "transactions.OrderLine"

    order = factory.SubFactory(OrderFactory)
    ida = factory.Sequence(lambda n: f"SOL-{n:05d}")
    status = "open"
    is_active = True
    is_deleted = False


class InvoiceFactory(DjangoModelFactory):
    class Meta:
        model = "transactions.Invoice"

    ida = factory.Sequence(lambda n: f"INV-{n:05d}")
    status = "open"
    is_active = True
    is_deleted = False


class ProposalFactory(DjangoModelFactory):
    class Meta:
        model = "transactions.Proposal"

    ida = factory.Sequence(lambda n: f"QT-{n:05d}")
    status = "open"
    is_active = True
    is_deleted = False


class PurchaseFactory(DjangoModelFactory):
    class Meta:
        model = "transactions.Purchase"

    ida = factory.Sequence(lambda n: f"PO-{n:05d}")
    status = "open"
    is_active = True
    is_deleted = False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
def proposal(db):
    """A single active proposal/quote."""
    return ProposalFactory()


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
