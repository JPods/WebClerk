"""The GlAccount table is the chart of accounts: the only accounts that exist.

Defaults come from the company GL role map (config.gl_defaults); any account
code that is not an active GlAccount is refused wherever it is used.
"""
import pytest

from apps.accounts.models import GlAccount, GlJournal
from apps.accounts.services.chart import UndefinedAccountError, role_account
from apps.products.models import Item

pytestmark = pytest.mark.django_db


def test_item_save_seeds_missing_gls_from_company_roles(chart_of_accounts):
    item = Item.objects.create(name="Default GL Item", kind=Item.KIND_PHYSICAL, gls={})

    assert item.gls["revenue"] == chart_of_accounts["sales_revenue"]
    assert item.gls["inventory"] == chart_of_accounts["inventory"]
    assert item.gls["cogs"] == chart_of_accounts["cost_of_goods_sold"]
    assert item.gls["purchase"] == chart_of_accounts["accounts_payable"]


def test_item_keeps_its_own_chart_account(chart_of_accounts):
    item = Item.objects.create(name="Service", kind=Item.KIND_PHYSICAL, gls={"revenue": "4010-service_revenue"})

    assert item.gls["revenue"] == "4010-service_revenue"
    assert item.gls["inventory"] == chart_of_accounts["inventory"]


def test_item_with_undefined_account_is_refused(chart_of_accounts):
    with pytest.raises(UndefinedAccountError, match="4000-Sales"):
        Item.objects.create(name="Bad GL Item", kind=Item.KIND_PHYSICAL, gls={"revenue": "4000-Sales"})


def test_journal_to_undefined_account_is_refused(chart_of_accounts):
    GlJournal.objects.create(account="1100-accounts_receivable", debit=1.0)
    with pytest.raises(UndefinedAccountError, match="ASSET-AR-000"):
        GlJournal.objects.create(account="ASSET-AR-000", debit=1.0)
    with pytest.raises(UndefinedAccountError):
        GlJournal.objects.create(debit=1.0)


def test_inactive_account_is_refused(chart_of_accounts):
    GlAccount.objects.filter(ida="6700-travel_meals").update(is_active=False)
    with pytest.raises(UndefinedAccountError, match="inactive"):
        GlJournal.objects.create(account="6700-travel_meals", debit=1.0)


def test_account_codes_are_uniform(chart_of_accounts):
    with pytest.raises(UndefinedAccountError, match="lowercase_words"):
        GlAccount.objects.create(ida="4500-Consulting", name="Consulting", type="revenue", category="revenue", used_for="sales")
    GlAccount.objects.create(ida="4500-consulting_revenue", name="Consulting", type="revenue", category="revenue", used_for="sales")


def test_every_role_maps_to_a_chart_account(chart_of_accounts):
    for role, code in chart_of_accounts.items():
        assert role_account(role) == code


def test_unmapped_role_fails_with_the_role_named(db):
    with pytest.raises(UndefinedAccountError, match="sales_tax_payable"):
        role_account("sales_tax_payable")


def test_every_seeded_account_has_a_use_summary(chart_of_accounts):
    for account in GlAccount.objects.all():
        notes = [c for c in (account.comments or {}).get("process", []) if c.get("key") == "account_use"]
        assert notes and notes[0]["mgs"], account.ida
        assert account.name and account.type and account.category and account.used_for, account.ida


def test_documents_are_numbered_number_first_by_type(db):
    from apps.transactions.models import Invoice, Quote

    first = Quote.objects.create(status="planned")
    second = Quote.objects.create(status="planned")
    invoice = Invoice.objects.create(status="planned")
    training = Quote(status="planned")
    training._training_prefix = "qq"
    training.save()

    assert (first.ida, second.ida, invoice.ida, training.ida) == ("1001-qt", "1002-qt", "1001-inv", "1003-qt-qq")


def test_other_records_use_their_pk(db):
    from apps.core.models import Contact

    contact = Contact.objects.create(name_first="Ida", name_last="Plain")
    assert contact.ida == str(contact.pk)


def test_term_resolves_from_document_or_company_default(db):
    from apps.accounts.models import Term
    from apps.accounts.services.terms_ledger import resolve_term
    from apps.core.models import Setting
    from apps.transactions.models import Invoice

    assert Term.objects.filter(ida__in=["N30", "DOR"]).count() == 2  # created with the test database
    assert Setting.objects.get(purpose="wc:company_profile").config["receivables"]["default_term"] == "N30"

    assert resolve_term(Invoice.objects.create(status="planned", terms="dor")).ida == "DOR"
    assert resolve_term(Invoice.objects.create(status="planned")).ida == "N30"
    with pytest.raises(ValueError, match="net 45"):
        resolve_term(Invoice.objects.create(status="planned", terms="net 45"))
