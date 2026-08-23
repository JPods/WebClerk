from django.urls import path

from apps.accounts.views.reports import AgedReceivablesView, CustomerStatementView

urlpatterns = [
    path('aged_receivables/', AgedReceivablesView.as_view(), name='aged-receivables'),
    path('statement/<int:customer_id>/', CustomerStatementView.as_view(), name='customer-statement'),
]
