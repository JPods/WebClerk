from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.transactions.views.cash_views import (
    cash_status,
    cash_history,
    gateway_config,
    checkout_pricing,
)
from apps.transactions.views.transfer_views import validate_transfer

app_name = 'transactions'

# Transaction CRUD views (using DRF ViewSets)
from apps.transactions.views.transaction_views import (
    QuoteViewSet,
    OrderViewSet,
    PurchaseViewSet,
    InvoiceViewSet,
)

router = DefaultRouter()
# wcapi paths are wcapi/<model_name>/... — the app name never appears in the path,
# and a model name is singular, as WC3 names its models (Bill, 2026-09-17).
router.register(r'quote', QuoteViewSet, basename='quote')
router.register(r'order', OrderViewSet, basename='order')
router.register(r'purchase', PurchaseViewSet, basename='purchase')
router.register(r'invoice', InvoiceViewSet, basename='invoice')

urlpatterns = [
    # DRF router URLs for CRUD operations
    path('', include(router.urls)),

    # Conversion is a command: POST /wcapi/<source>/<id>/convert/ {to} (services/convert).

    # Transfer operations
    path('transfers/validate/', validate_transfer, name='validate_transfer'),

    # Cash operations
    path('cash/<int:cash_id>/status/', cash_status, name='cash_status'),
    path('cash/history/', cash_history, name='cash_history'),
    path('cash/gateway-config/', gateway_config, name='gateway_config'),
    path('cash/checkout-pricing/<int:invoice_id>/', checkout_pricing, name='checkout_pricing'),

    # Statement harvester — JSON-based
]
