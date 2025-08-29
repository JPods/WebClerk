from django.urls import path
from apps.transactions.views import line_views as views

urlpatterns = [
    # Proposal
    path('proposals/', views.ProposalListCreate.as_view(), name='proposal-list'),
    path('proposals/<int:pk>/', views.ProposalRetrieveUpdate.as_view(), name='proposal-detail'),
    path('proposal-lines/', views.ProposalLineListCreate.as_view(), name='proposal-line-list'),
    path('proposal-lines/<int:pk>/', views.ProposalLineRetrieveUpdate.as_view(), name='proposal-line-detail'),

    # Order
    path('orders/', views.OrderListCreate.as_view(), name='order-list'),
    path('orders/<int:pk>/', views.OrderRetrieveUpdate.as_view(), name='order-detail'),
    path('order-lines/', views.OrderLineListCreate.as_view(), name='order-line-list'),
    path('order-lines/<int:pk>/', views.OrderLineRetrieveUpdate.as_view(), name='order-line-detail'),

    # Invoice
    path('invoices/', views.InvoiceListCreate.as_view(), name='invoice-list'),
    path('invoices/<int:pk>/', views.InvoiceRetrieveUpdate.as_view(), name='invoice-detail'),
    path('invoice-lines/', views.InvoiceLineListCreate.as_view(), name='invoice-line-list'),
    path('invoice-lines/<int:pk>/', views.InvoiceLineRetrieveUpdate.as_view(), name='invoice-line-detail'),

    # Purchase
    path('purchases/', views.PurchaseListCreate.as_view(), name='purchase-list'),
    path('purchases/<int:pk>/', views.PurchaseRetrieveUpdate.as_view(), name='purchase-detail'),
    path('purchase-lines/', views.PurchaseLineListCreate.as_view(), name='purchase-line-list'),
    path('purchase-lines/<int:pk>/', views.PurchaseLineRetrieveUpdate.as_view(), name='purchase-line-detail'),

    # Workorder
    path('workorders/', views.WorkorderListCreate.as_view(), name='workorder-list'),
    path('workorders/<int:pk>/', views.WorkorderRetrieveUpdate.as_view(), name='workorder-detail'),
    path('workorder-lines/', views.WorkorderLineListCreate.as_view(), name='workorder-line-list'),
    path('workorder-lines/<int:pk>/', views.WorkorderLineRetrieveUpdate.as_view(), name='workorder-line-detail'),

    # Requisition
    path('requisitions/', views.RequisitionListCreate.as_view(), name='requisition-list'),
    path('requisitions/<int:pk>/', views.RequisitionRetrieveUpdate.as_view(), name='requisition-detail'),
    path('requisition-lines/', views.RequisitionLineListCreate.as_view(), name='requisition-line-list'),
    path('requisition-lines/<int:pk>/', views.RequisitionLineRetrieveUpdate.as_view(), name='requisition-line-detail'),

    # Aggregation
    path('lines/aggregate/', views.LineAggregateView.as_view(), name='line-aggregate'),
    path('auth/fields/', views.FieldAuthMatrixView.as_view(), name='line-field-auth'),
    path('auth/fields/batch/', views.FieldAuthMatrixBatchView.as_view(), name='line-field-auth-batch'),
]
