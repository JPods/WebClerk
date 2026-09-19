from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.transactions.views.cash_views import (
    process_cash,
    refund_cash_view,
    spreedly_webhook,
    stripe_webhook,
    paypal_webhook,
    cash_status,
    cash_history,
    gateway_config,
    checkout_pricing,
)
from apps.transactions.views.transfer_views import (
    validate_transfer,
    execute_transfer,
    reserve_inventory,
    release_inventory,
    bulk_transfer_quotes,
    bulk_transfer_orders,
)

app_name = 'transactions'

# Transaction CRUD views (using DRF ViewSets)
from apps.transactions.views.transaction_views import (
    QuoteViewSet,
    OrderViewSet,
    PurchaseViewSet,
    InvoiceViewSet,
    CashViewSet,
)
from apps.transactions.views.actions import OrderToPurchaseView

router = DefaultRouter()
# wcapi paths are wcapi/<model_name>/... — the app name never appears in the path,
# and a model name is singular, as WC3 names its models (Bill, 2026-09-17).
router.register(r'quote', QuoteViewSet, basename='quote')
router.register(r'order', OrderViewSet, basename='order')
router.register(r'purchase', PurchaseViewSet, basename='purchase')
router.register(r'invoice', InvoiceViewSet, basename='invoice')
router.register(r'cash', CashViewSet, basename='cash')

urlpatterns = [
    # DRF router URLs for CRUD operations
    path('', include(router.urls)),

    # Conversion endpoints
    path('quote/<int:pk>/convert-to-order/', QuoteViewSet.as_view({'post': 'convert_to_order'}), name='quote-convert-to-order'),
    path('order/<int:pk>/convert-to-invoice/', OrderViewSet.as_view({'post': 'convert_to_invoice'}), name='order-convert-to-invoice'),
    path('order/<int:pk>/convert-to-purchase/', OrderToPurchaseView.as_view(), name='order-convert-to-purchase'),
    path('purchase/<int:pk>/receive-goods/', PurchaseViewSet.as_view({'post': 'receive_goods'}), name='purchase-receive-goods'),

    # Transfer operations
    path('transfers/validate/', validate_transfer, name='validate_transfer'),
    path('transfers/execute/', execute_transfer, name='execute_transfer'),
    path('transfers/bulk/quotes-to-orders/', bulk_transfer_quotes, name='bulk_transfer_quotes'),
    path('transfers/bulk/orders-to-invoices/', bulk_transfer_orders, name='bulk_transfer_orders'),

    # Cash operations
    path('cash/process/', process_cash, name='process_cash'),
    path('cash/refund/', refund_cash_view, name='refund_cash'),
    path('cash/webhooks/spreedly/', spreedly_webhook, name='spreedly_webhook'),
    path('cash/webhooks/stripe/', stripe_webhook, name='stripe_webhook'),
    path('cash/webhooks/paypal/', paypal_webhook, name='paypal_webhook'),
    path('cash/<int:cash_id>/status/', cash_status, name='cash_status'),
    path('cash/history/', cash_history, name='cash_history'),
    path('cash/gateway-config/', gateway_config, name='gateway_config'),
    path('cash/checkout-pricing/<int:invoice_id>/', checkout_pricing, name='checkout_pricing'),

    # Inventory operations
    path('inventory/reserve/', reserve_inventory, name='reserve_inventory'),
    path('inventory/release/<int:invoice_id>/', release_inventory, name='release_inventory'),

    # Statement harvester — JSON-based
    path('statements/harvest/',
         __import__('apps.transactions.views.statement_views', fromlist=['harvest_statements']).harvest_statements,
         name='harvest_statements'),
    path('statements/files/',
         __import__('apps.transactions.views.statement_views', fromlist=['list_statement_files']).list_statement_files,
         name='list_statement_files'),
    path('statements/lines/',
         __import__('apps.transactions.views.statement_views', fromlist=['get_statement_lines']).get_statement_lines,
         name='get_statement_lines'),
    path('statements/save/',
         __import__('apps.transactions.views.statement_views', fromlist=['save_statement_changes']).save_statement_changes,
         name='save_statement_changes'),
    path('statements/promote/',
         __import__('apps.transactions.views.statement_views', fromlist=['promote_statements']).promote_statements,
         name='promote_statements'),
    path('statements/export/',
         __import__('apps.transactions.views.statement_views', fromlist=['export_personal']).export_personal,
         name='export_personal_statements'),
]
