from django.contrib import admin
from .models import Currency, ExchangeRate, ExchangeTransaction, Term, GlAccount

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
