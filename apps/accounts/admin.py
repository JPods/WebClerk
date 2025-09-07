from django.contrib import admin
from .models import Currency, ExchangeRate, ExchangeTransaction


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
	list_display = ("code", "name", "precision", "is_active", "connection_id")
	list_filter = ("is_active",)
	search_fields = ("code", "name")


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
	list_display = ("currency_base", "currency_target", "rate", "dt_start", "dt_end", "is_active", "connection_id")
	list_filter = ("is_active", "currency_base", "currency_target")
	search_fields = ("currency_base", "currency_target")


@admin.register(ExchangeTransaction)
class ExchangeTransactionAdmin(admin.ModelAdmin):
	list_display = ("name", "currency_base", "currency_target", "rate", "dt_start", "dt_end", "is_active", "connection_id")
	list_filter = ("is_active", "currency_base", "currency_target")
	search_fields = ("name", "currency_base", "currency_target")
