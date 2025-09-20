from django.urls import path
from apps.transactions.views import line_views as views
from apps.transactions.views import unified as unified_views
from apps.transactions.views.requisition import (
    RequisitionListView, RequisitionDetailView, RequisitionSearchView
)
from apps.transactions.views.proposal_views import (
    ProposalActionView,
    ProposalToSalesOrderView,
)
from apps.transactions.views.sales_order_views import SalesOrderToInvoiceView
from apps.transactions.views.purchase_order_views import ReceivePurchaseOrderView

urlpatterns = [
    # Proposal
    path('proposals/', views.ProposalListCreate.as_view(), name='proposal-list'),
    path('proposals/<int:pk>/', views.ProposalRetrieveUpdate.as_view(), name='proposal-detail'),
    path('proposal-lines/', views.ProposalLineListCreate.as_view(), name='proposal-line-list'),
    path('proposal-lines/<int:pk>/', views.ProposalLineRetrieveUpdate.as_view(), name='proposal-line-detail'),

    # Sales Order
    path('sales-orders/', views.SalesOrderListCreate.as_view(), name='sales-order-list'),
    path('sales-orders/<int:pk>/', views.SalesOrderRetrieveUpdate.as_view(), name='sales-order-detail'),
    path('sales-order-lines/', views.SalesOrderLineListCreate.as_view(), name='sales-order-line-list'),
    path('sales-order-lines/<int:pk>/', views.SalesOrderLineRetrieveUpdate.as_view(), name='sales-order-line-detail'),

    # Invoice
    path('invoices/', views.InvoiceListCreate.as_view(), name='invoice-list'),
    path('invoices/<int:pk>/', views.InvoiceRetrieveUpdate.as_view(), name='invoice-detail'),
    path('invoice-lines/', views.InvoiceLineListCreate.as_view(), name='invoice-line-list'),
    path('invoice-lines/<int:pk>/', views.InvoiceLineRetrieveUpdate.as_view(), name='invoice-line-detail'),

    # Purchase Order
    path('purchase-orders/', views.PurchaseOrderListCreate.as_view(), name='purchase-order-list'),
    path('purchase-orders/<int:pk>/', views.PurchaseOrderRetrieveUpdate.as_view(), name='purchase-order-detail'),
    path('purchase-order-lines/', views.PurchaseOrderLineListCreate.as_view(), name='purchase-order-line-list'),
    path('purchase-order-lines/<int:pk>/', views.PurchaseOrderLineRetrieveUpdate.as_view(), name='purchase-order-line-detail'),

    # WorkOrder
    path('workorders/', views.WorkOrderListCreate.as_view(), name='workorder-list'),
    path('workorders/<int:pk>/', views.WorkOrderRetrieveUpdate.as_view(), name='workorder-detail'),
    path('workorder-lines/', views.WorkOrderLineListCreate.as_view(), name='workorder-line-list'),
    path('workorder-lines/<int:pk>/', views.WorkOrderLineRetrieveUpdate.as_view(), name='workorder-line-detail'),

    # Requisition
    path('requisitions/', views.RequisitionListCreate.as_view(), name='requisition-list'),
    path('requisitions/<int:pk>/', views.RequisitionRetrieveUpdate.as_view(), name='requisition-detail'),
    path('requisition-lines/', views.RequisitionLineListCreate.as_view(), name='requisition-line-list'),
    path('requisition-lines/<int:pk>/', views.RequisitionLineRetrieveUpdate.as_view(), name='requisition-line-detail'),

    # Requisition (standardized BaseModel pattern v2)
    path('requisitions/std/', RequisitionListView.as_view(), name='requisition2-list'),
    path('requisitions/std/<int:pk>/', RequisitionDetailView.as_view(), name='requisition2-detail'),
    path('requisitions/std/search/', RequisitionSearchView.as_view(), name='requisition2-search'),

    # Aggregation
    path('lines/aggregate/', views.LineAggregateView.as_view(), name='line-aggregate'),
    path('auth/fields/', views.FieldAuthMatrixView.as_view(), name='line-field-auth'),
    path('auth/fields/batch/', views.FieldAuthMatrixBatchView.as_view(), name='line-field-auth-batch'),

    # Projects
    path('projects/', views.ProjectListCreate.as_view(), name='project-list'),
    path('projects/<int:pk>/', views.ProjectRetrieveUpdate.as_view(), name='project-detail'),
    # Unified endpoints (experimental consolidated schema)
    # Flow actions
    # Flow actions
    # Flow actions
    path('sales-orders/<int:pk>/convert-to-invoice/', SalesOrderToInvoiceView.as_view(), name='so-to-invoice'),
    # path('sales-orders/<int:pk>/convert-to-purchase-order/', views.SalesOrderToPurchaseOrderView.as_view(), name='so-to-po'),  # Disabled: view not found in line_views
    # WorkOrder transitions
    # WorkOrder transitions
    # WorkOrder transitions
    path("proposals/<int:pk>/convert-to-sales-order/", ProposalToSalesOrderView.as_view(), name='proposal-to-so'),

    # Proposal Action
    path("proposals/action/", ProposalActionView.as_view(), name="proposal-action"),
    path('purchase-orders/<int:pk>/receive/', ReceivePurchaseOrderView.as_view(), name='po-receive'),
]
