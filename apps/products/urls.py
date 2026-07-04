"""Products app URLs for BOM and inventory views."""
from django.urls import path
from apps.products.views.bom_views import (
    BOMListCreateView, BOMDetailView, BOMRecalcCostView,
    BOMExpandTreeView, BOMConsumeView, BOMWhereUsedView, BOMPropagateCostView,
)

app_name = 'products'

urlpatterns = [
    # BOM endpoints - nested under items
    path('items/<int:parent_id>/bom/', BOMListCreateView.as_view(), name='bom-list-create'),
    path('items/<int:parent_id>/bom/recalc-cost/', BOMRecalcCostView.as_view(), name='bom-recalc-cost'),
    path('items/<int:parent_id>/bom/expand/', BOMExpandTreeView.as_view(), name='bom-expand-tree'),
    path('items/<int:parent_id>/bom/consume/', BOMConsumeView.as_view(), name='bom-consume'),
    path('items/<int:item_id>/bom/where-used/', BOMWhereUsedView.as_view(), name='bom-where-used'),
    path('items/<int:item_id>/bom/propagate-cost/', BOMPropagateCostView.as_view(), name='bom-propagate-cost'),
    path('bom/<int:pk>/', BOMDetailView.as_view(), name='bom-detail'),
]
