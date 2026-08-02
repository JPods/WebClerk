"""Products app URLs for BOM, serial, and inventory views."""
from django.urls import path
from apps.products.views.bom_views import (
    BOMListCreateView, BOMDetailView, BOMRecalcCostView,
    BOMExpandTreeView, BOMConsumeView, BOMWhereUsedView, BOMPropagateCostView,
)
from apps.products.views.serial_views import (
    SerialListByItemView, SerialReceiveView, SerialIssueView, SerialReturnView,
    SerialReferenceView, SerialHistoryView, SerialSearchView, SerialWarrantyView,
    SerialStatusChangeView,
)
from apps.products.views.item_inventory_views import BulkItemInventoryView

app_name = 'products'

urlpatterns = [
    # Bulk inventory lookup (line card L button, QuickQuote)
    path('items/inventory/', BulkItemInventoryView.as_view(), name='item-bulk-inventory'),

    # BOM endpoints - nested under items
    path('items/<int:parent_id>/bom/', BOMListCreateView.as_view(), name='bom-list-create'),
    path('items/<int:parent_id>/bom/recalc-cost/', BOMRecalcCostView.as_view(), name='bom-recalc-cost'),
    path('items/<int:parent_id>/bom/expand/', BOMExpandTreeView.as_view(), name='bom-expand-tree'),
    path('items/<int:parent_id>/bom/consume/', BOMConsumeView.as_view(), name='bom-consume'),
    path('items/<int:item_id>/bom/where-used/', BOMWhereUsedView.as_view(), name='bom-where-used'),
    path('items/<int:item_id>/bom/propagate-cost/', BOMPropagateCostView.as_view(), name='bom-propagate-cost'),
    path('bom/<int:pk>/', BOMDetailView.as_view(), name='bom-detail'),

    # Serial endpoints
    path('items/<int:item_id>/serials/', SerialListByItemView.as_view(), name='serial-list-by-item'),
    path('items/<int:item_id>/serials/receive/', SerialReceiveView.as_view(), name='serial-receive'),
    path('items/<int:item_id>/serials/reference/', SerialReferenceView.as_view(), name='serial-reference'),
    path('serials/search/', SerialSearchView.as_view(), name='serial-search'),
    path('serials/warranty/', SerialWarrantyView.as_view(), name='serial-warranty'),
    path('serials/<int:serial_id>/issue/', SerialIssueView.as_view(), name='serial-issue'),
    path('serials/<int:serial_id>/return/', SerialReturnView.as_view(), name='serial-return'),
    path('serials/<int:serial_id>/history/', SerialHistoryView.as_view(), name='serial-history'),
    path('serials/<int:serial_id>/status/', SerialStatusChangeView.as_view(), name='serial-status'),
]
