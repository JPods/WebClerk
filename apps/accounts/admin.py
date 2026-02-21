from django.contrib import admin
from .models import Currency, ExchangeRate, ExchangeTransaction, Term, GlAccount
from .models.ledger import Ledger
from .models.tax_jurisdiction import TaxJurisdiction
from .models.gl_journal import GlJournal
from .models.audit import Audit

@admin.register(GlAccount)
class GLAccountAdmin(admin.ModelAdmin):
	list_display = ("id", "account_number", "name", "type", "category", "division", "used_for", "account_debit", "account_credit")
	list_filter = ("is_active",)
	search_fields = ("account_number", "name")


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
	list_display = ("code", "name", "precision", "is_active")
	list_filter = ("is_active",)
	search_fields = ("code", "name")


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
	list_display = ("currency_base", "currency_target", "rate", "dt_start", "dt_end", "is_active")
	list_filter = ("is_active", "currency_base", "currency_target")
	search_fields = ("currency_base", "currency_target")


@admin.register(ExchangeTransaction)
class ExchangeTransactionAdmin(admin.ModelAdmin):
	list_display = ("name", "currency_base", "currency_target", "rate", "dt_start", "dt_end", "is_active")
	list_filter = ("is_active", "currency_base", "currency_target")
	search_fields = ("name", "currency_base", "currency_target")


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
	list_display = ("name", "days_due", "days_discount", "discount_rate", "day_cut_off_due", "day_cut_off_invoice")
	list_filter = ("days_due", "days_discount")
	search_fields = ("name", "description")


@admin.register(Ledger)
class LedgerAdmin(admin.ModelAdmin):
	list_display = ("id", "source", "model_name", "value_original", "value_available", "is_settled", "is_void", "dt_posted", "is_active")
	list_filter = ("source", "model_name", "is_settled", "is_cleared", "is_void", "is_active")
	search_fields = ("ida",)
	readonly_fields = ("uuid", "dt_created", "dt_modified")


@admin.register(TaxJurisdiction)
class TaxJurisdictionAdmin(admin.ModelAdmin):
	list_display = ("id", "tax_jurisdiction", "tax_name", "service_provider", "tax_rate_sales", "tax_rate_cost", "is_active")
	list_filter = ("service_provider", "is_active")
	search_fields = ("tax_jurisdiction", "tax_name", "gl_account_payable")
	readonly_fields = ("uuid", "dt_created", "dt_modified")


@admin.register(GlJournal)
class GlJournalAdmin(admin.ModelAdmin):
	list_display = ("id", "account", "debit", "credit", "source", "type", "is_active", "dt_created")
	list_filter = ("source", "type", "is_active")
	search_fields = ("account", "ida")
	readonly_fields = ("uuid", "dt_created", "dt_modified")


@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "purpose", "rating", "priority", "is_completed", "is_active", "dt_created")
	list_filter = ("purpose", "is_completed", "is_active")
	search_fields = ("name", "purpose", "ida")
	readonly_fields = ("uuid", "dt_created", "dt_modified")
