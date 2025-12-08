from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.transactions.views.payment_views import (
    process_payment,
    execute_paypal_payment,
    stripe_webhook,
    paypal_webhook,
    reconcile_payments,
    payment_status,
    payment_history
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
    SalesOrderViewSet,
    PurchaseOrderViewSet,
    InvoiceViewSet,
    PaymentViewSet,
)
from apps.transactions.views.sales_order_views import SalesOrderToPurchaseOrderView

router = DefaultRouter()
router.register(r'proposals', ProposalViewSet, basename='proposal')
router.register(r'orders', SalesOrderViewSet, basename='salesorder')
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchaseorder')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = [
    # DRF router URLs for CRUD operations
    path('', include(router.urls)),

    # Backwards-compatible conversion endpoints (legacy paths used by docs/tests)
    path('proposals/<int:pk>/convert-to-sales-order/', ProposalViewSet.as_view({'post': 'convert_to_order'}), name='proposal-convert-to-sales-order'),
    path('sales-orders/<int:pk>/convert-to-invoice/', SalesOrderViewSet.as_view({'post': 'convert_to_invoice'}), name='salesorder-convert-to-invoice'),
    path('sales-orders/<int:pk>/convert-to-purchase-order/', SalesOrderToPurchaseOrderView.as_view(), name='salesorder-convert-to-purchase-order'),

    # Transfer operations
    path('transfers/validate/', validate_transfer, name='validate_transfer'),
    path('transfers/execute/', execute_transfer, name='execute_transfer'),
    path('transfers/bulk/proposals-to-orders/', bulk_transfer_proposals, name='bulk_transfer_proposals'),
    path('transfers/bulk/orders-to-invoices/', bulk_transfer_orders, name='bulk_transfer_orders'),

    # Payment operations
    path('payments/process/', process_payment, name='process_payment'),
    path('payments/paypal/execute/', execute_paypal_payment, name='execute_paypal_payment'),
    path('payments/apply/', apply_payment, name='apply_payment'),
    path('payments/webhooks/stripe/', stripe_webhook, name='stripe_webhook'),
    path('payments/webhooks/paypal/', paypal_webhook, name='paypal_webhook'),
    path('payments/reconcile/', reconcile_payments, name='reconcile_payments'),
    path('payments/<int:payment_id>/status/', payment_status, name='payment_status'),
    path('payments/history/', payment_history, name='payment_history'),

    # Inventory operations
    path('inventory/reserve/', reserve_inventory, name='reserve_inventory'),
    path('inventory/release/<int:invoice_id>/', release_inventory, name='release_inventory'),
]
