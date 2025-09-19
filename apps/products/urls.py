from django.urls import path
from apps.products.views.bom_views import BOMListCreateView, BOMDetailView, BOMRecalcCostView
from apps.products.views.inventory_views import (
    InventoryAvailabilityView, InventoryReservationCreateView, InventoryReservationActionView, InventoryMetricsView,
    InventoryPrometheusMetricsView,
)

app_name = 'products'

urlpatterns = [
    path('bill_of_material/<int:parent_id>/', BOMListCreateView.as_view(), name='bill_of_material-list-create'),
    path('bill_of_material/line/<int:pk>/', BOMDetailView.as_view(), name='bill_of_material-detail'),
    path('bill_of_material/<int:parent_id>/recalc/', BOMRecalcCostView.as_view(), name='bill_of_material-recalc'),
    # Inventory availability & reservations
    path('inventory/availability/<int:stack_id>/', InventoryAvailabilityView.as_view(), name='inventory-availability'),
    path('inventory/reservations/', InventoryReservationCreateView.as_view(), name='inventory-reservation-create'),
    path('inventory/reservations/action/', InventoryReservationActionView.as_view(), name='inventory-reservation-action'),
    path('inventory/metrics/', InventoryMetricsView.as_view(), name='inventory-metrics'),
    path('inventory/metrics/prometheus', InventoryPrometheusMetricsView.as_view(), name='inventory-metrics-prom'),
]
