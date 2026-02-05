"""Products app URLs for BOM and inventory views."""
from django.urls import path
from apps.products.views.bom_views import BOMListCreateView, BOMDetailView, BOMRecalcCostView

app_name = 'products'

urlpatterns = [
    # BOM endpoints - nested under items
    path('items/<int:parent_id>/bom/', BOMListCreateView.as_view(), name='bom-list-create'),
    path('items/<int:parent_id>/bom/recalc-cost/', BOMRecalcCostView.as_view(), name='bom-recalc-cost'),
    path('bom/<int:pk>/', BOMDetailView.as_view(), name='bom-detail'),
]
