from django.contrib import admin
from common.admin_schema_labels import SchemaLabelsAdminMixin
from common.admin_mixins import ScalarFirstFieldsetMixin
from .models import Currency, ExchangeRate, ExchangeTransaction, Term, GlAccount
from .models.ledger import Ledger
from .models.tax_jurisdiction import TaxJurisdiction
from .models.gl_journal import GlJournal
from .models.audit import Audit

@admin.register(GlAccount)
class GLAccountAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
	# Scalar fields: account_credit, account_debit, account_number, category, comment, division, dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, name, security_level, type, type_id, used_for, uuid, version
	list_display = ("ida", "name", "type", "account_credit", "account_debit", "account_number", "is_active", "dt_created")
	list_filter = ("is_active",)
	search_fields = ("account_number", "name")


@admin.register(Currency)
class CurrencyAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
	# Scalar fields: code, dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, name, precision, security_level, symbol, uuid, version
	list_display = ("ida", "name", "code", "health_rating", "is_locked", "precision", "is_active", "dt_created")
	list_filter = ("is_active",)
	search_fields = ("code", "name")


@admin.register(ExchangeRate)
class ExchangeRateAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
	# Scalar fields: currency_base, currency_target, dt_created, dt_end, dt_modified, dt_start, health_rating, ida, is_active, is_archived, is_deleted, is_locked, name, precision_convert, precision_display, rate, security_level, uuid, version
	list_display = ("ida", "name", "currency_base", "currency_target", "dt_end", "dt_start", "is_active", "dt_created")
	list_filter = ("is_active", "currency_base", "currency_target")
	search_fields = ("currency_base", "currency_target")


@admin.register(ExchangeTransaction)
class ExchangeTransactionAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
	# Scalar fields: currency_base, currency_target, dt_created, dt_end, dt_modified, dt_start, health_rating, ida, is_active, is_archived, is_deleted, is_locked, name, precision_convert, precision_display, rate, security_level, uuid, version
	list_display = ("ida", "name", "currency_base", "currency_target", "dt_end", "dt_start", "is_active", "dt_created")
	list_filter = ("is_active", "currency_base", "currency_target")
	search_fields = ("name", "currency_base", "currency_target")


@admin.register(Term)
class TermAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
	# Scalar fields: approved_by, day_cut_off_due, day_cut_off_invoice, days_discount, days_due, days_in_period, description, discount_rate, dt_begin, dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, name, period_count, security_level, uuid, version
	list_display = ("ida", "name", "description", "approved_by", "day_cut_off_due", "day_cut_off_invoice", "is_active", "dt_created")
	list_filter = ("days_due", "days_discount")
	search_fields = ("name", "description")


@admin.register(Ledger)
class LedgerAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
	# Scalar fields: discount_potential, dt_created, dt_discount_due, dt_due, dt_modified, dt_posted, dt_recorded, dt_settled, health_rating, ida, is_active, is_archived, is_cleared, is_deleted, is_locked, is_settled, is_void, model_name, parent_id, security_level, source, uuid, value_available, value_original, version
	list_display = ("ida", "discount_potential", "dt_discount_due", "dt_due", "dt_posted", "dt_recorded", "is_active", "dt_created")
	list_filter = ("source", "model_name", "is_settled", "is_cleared", "is_void", "is_active")
	search_fields = ("ida",)
	readonly_fields = ("uuid", "dt_created", "dt_modified")


@admin.register(TaxJurisdiction)
class TaxJurisdictionAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
	# Scalar fields: dt_created, dt_modified, gl_account_payable, health_rating, ida, is_active, is_archived, is_deleted, is_locked, security_level, service_provider, tax_jurisdiction, tax_name, tax_rate_cost, tax_rate_on_shipping, tax_rate_sales, uuid, version
	list_display = ("ida", "gl_account_payable", "health_rating", "is_locked", "security_level", "service_provider", "is_active", "dt_created")
	list_filter = ("service_provider", "is_active")
	search_fields = ("tax_jurisdiction", "tax_name", "gl_account_payable")
	readonly_fields = ("uuid", "dt_created", "dt_modified")


@admin.register(GlJournal)
class GlJournalAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
	# Scalar fields: account, credit, debit, dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, security_level, source, type, uuid, version
	list_display = ("ida", "type", "account", "credit", "debit", "health_rating", "is_active", "dt_created")
	list_filter = ("source", "type", "is_active")
	search_fields = ("account", "ida")
	readonly_fields = ("uuid", "dt_created", "dt_modified")


@admin.register(Audit)
class AuditAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
	# Scalar fields: dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_completed, is_deleted, is_locked, name, priority, purpose, rating, security_level, uuid, version
	list_display = ("ida", "name", "health_rating", "is_completed", "is_locked", "priority", "is_active", "dt_created")
	list_filter = ("purpose", "is_completed", "is_active")
	search_fields = ("name", "purpose", "ida")
	readonly_fields = ("uuid", "dt_created", "dt_modified")
