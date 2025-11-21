from django.contrib import admin
from .models.campaign import Campaign


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "type", "status", "dt_created")
    list_filter = ("type", "status")
    search_fields = ("name", "description")
