from django.contrib import admin, messages

from .models import (
    Invoice, InvoiceLine,
)


# Scoped: other model admin registrations are deferred for now


##


##


##


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
	list_display = ("id", "dt_created")
	search_fields = ("id",)


@admin.register(InvoiceLine)
class InvoiceLineAdmin(admin.ModelAdmin):
	list_display = ("id", "parent_id", "status")
	list_filter = ("status",)


##


##


##


##


##


##
