from django.urls import path
from apps.products.views.bom_views import BOMListCreateView, BOMDetailView, BOMRecalcCostView

app_name = 'products'

urlpatterns = [
    path('bom/<int:parent_id>/', BOMListCreateView.as_view(), name='bom-list-create'),
    path('bom/line/<int:pk>/', BOMDetailView.as_view(), name='bom-detail'),
    path('bom/<int:parent_id>/recalc/', BOMRecalcCostView.as_view(), name='bom-recalc'),
]
