from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.transactions.views.payment_views import (
    process_payment,
    refund_payment_view,
    spreedly_webhook,
    stripe_webhook,
    paypal_webhook,
    reconcile_payments,
    payment_status,
    payment_history,
    gateway_config,
)
from apps.transactions.views.transfer_views import (
    validate_transfer,
    execute_transfer,
    apply_payment,
    reserve_inventory,
    release_inventory,
    bulk_transfer_proposals,
    bulk_transfer_orders,
)

app_name = 'transactions'

# Transaction CRUD views (using DRF ViewSets)
from apps.transactions.views.transaction_views import (
    ProposalViewSet,
    OrderViewSet,
    PurchaseViewSet,
    InvoiceViewSet,
    PaymentViewSet,
)
from apps.transactions.views.actions import OrderToPurchaseView

router = DefaultRouter()
router.register(r'proposals', ProposalViewSet, basename='proposal')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'purchases', PurchaseViewSet, basename='purchase')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = [
    # DRF router URLs for CRUD operations
    path('', include(router.urls)),

    # Conversion endpoints
    path('proposals/<int:pk>/convert-to-order/', ProposalViewSet.as_view({'post': 'convert_to_order'}), name='proposal-convert-to-order'),
    path('orders/<int:pk>/convert-to-invoice/', OrderViewSet.as_view({'post': 'convert_to_invoice'}), name='order-convert-to-invoice'),
    path('orders/<int:pk>/convert-to-purchase/', OrderToPurchaseView.as_view(), name='order-convert-to-purchase'),

    # Transfer operations
    path('transfers/validate/', validate_transfer, name='validate_transfer'),
    path('transfers/execute/', execute_transfer, name='execute_transfer'),
    path('transfers/bulk/proposals-to-orders/', bulk_transfer_proposals, name='bulk_transfer_proposals'),
    path('transfers/bulk/orders-to-invoices/', bulk_transfer_orders, name='bulk_transfer_orders'),

    # Payment operations
    path('payments/process/', process_payment, name='process_payment'),
    path('payments/refund/', refund_payment_view, name='refund_payment'),
    path('payments/apply/', apply_payment, name='apply_payment'),
    path('payments/webhooks/spreedly/', spreedly_webhook, name='spreedly_webhook'),
    path('payments/webhooks/stripe/', stripe_webhook, name='stripe_webhook'),
    path('payments/webhooks/paypal/', paypal_webhook, name='paypal_webhook'),
    path('payments/reconcile/', reconcile_payments, name='reconcile_payments'),
    path('payments/<int:payment_id>/status/', payment_status, name='payment_status'),
    path('payments/history/', payment_history, name='payment_history'),
    path('payments/gateway-config/', gateway_config, name='gateway_config'),

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
