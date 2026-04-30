from django.urls import path
from django.views.generic import TemplateView
from . import views, views_ui

app_name = "jpods"

urlpatterns = [
    # ── Natalie API (Bearer token) ────────────────────────────────────────────
    path("price/",   views.PriceQueryView.as_view(), name="price-query"),
    path("invoice/", views.InvoiceView.as_view(),    name="invoice"),

    # ── Browser trip app UI API (myCarryOn Bearer token) ─────────────────────
    path("ui/contacts/",  views_ui.ContactsView.as_view(),  name="ui-contacts"),
    path("ui/identify/",  views_ui.IdentifyView.as_view(),  name="ui-identify"),
    path("ui/stations/",  views_ui.StationsView.as_view(),  name="ui-stations"),
    path("ui/price/",     views_ui.UIPriceView.as_view(),   name="ui-price"),
    path("ui/travel/",    views_ui.TravelView.as_view(),    name="ui-travel"),

    # ── Trip booking app (served at /jpods/trip/) ─────────────────────────────
    path("trip/", TemplateView.as_view(template_name="jpods/trip_app.html"), name="trip-app"),
]
