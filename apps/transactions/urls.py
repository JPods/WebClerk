from django.urls import path
from apps.transactions.views.payment_views import (
    process_payment,
    execute_paypal_payment,
    stripe_webhook,
    paypal_webhook,
    reconcile_payments,
    payment_status,
    payment_history
)

app_name = 'transactions'

urlpatterns = [
    # Payment processing endpoints
    path('payments/process/', process_payment, name='process_payment'),
    path('payments/paypal/execute/', execute_paypal_payment, name='execute_paypal_payment'),
    path('payments/webhooks/stripe/', stripe_webhook, name='stripe_webhook'),
    path('payments/webhooks/paypal/', paypal_webhook, name='paypal_webhook'),
    path('payments/reconcile/', reconcile_payments, name='reconcile_payments'),
    path('payments/<int:payment_id>/status/', payment_status, name='payment_status'),
    path('payments/history/', payment_history, name='payment_history'),
]
