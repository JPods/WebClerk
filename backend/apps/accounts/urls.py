from django.urls import path

from apps.accounts.views.reports import AgedReceivablesView, CustomerStatementView
from apps.accounts.views.gl_export_view import GlExportView

urlpatterns = [
    path('aged_receivables/', AgedReceivablesView.as_view(), name='aged-receivables'),
    path('statement/<int:customer_id>/', CustomerStatementView.as_view(), name='customer-statement'),
    path('gl-export/', GlExportView.as_view(), name='gl-export'),
]
