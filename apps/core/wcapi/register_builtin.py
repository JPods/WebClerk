from rest_framework import permissions
from django.apps import apps

from .registry import ModelConfig, register

# Tag: dev-fallback list (envelope sets data = list)
try:
    Tag = apps.get_model('docs', 'Tag')
    register(ModelConfig(
        key='tag',
        model=Tag,
        search_fields=('name', 'purpose', 'status'),
        ordering=('-dt_modified',),
        permission_classes=(permissions.IsAuthenticated,),
        basename='tag',
        dev_fallback=True,
    ))
except Exception:
    pass

# Domain -> Connection (standard list; envelope data is dict with results/items)
try:
    Connection = apps.get_model('sync', 'Connection')
    register(ModelConfig(
        key='domain',
        model=Connection,
        search_fields=('name', 'type'),
        ordering=('name',),
        permission_classes=(permissions.IsAuthenticated,),
        basename='domain',
        dev_fallback=False,
    ))
except Exception:
    pass

# Actions v2: /actions/std/, reverse('action2-list')
try:
    Action = apps.get_model('core', 'Action')
    register(ModelConfig(
        key='actions/std',
        model=Action,
        search_fields=('action', 'status', 'priority', 'who', 'notes'),
        ordering=('-id',),
        permission_classes=(permissions.IsAuthenticated,),
        basename='action2',
        dev_fallback=False,
    ))
except Exception:
    pass

# Inventory reservations endpoint (if a model exists)
try:
    Reservation = apps.get_model('products', 'InventoryReservation')
    register(ModelConfig(
        key='products/inventory/reservations',
        model=Reservation,
        search_fields=('id',),
        ordering=('-id',),
        permission_classes=(permissions.IsAuthenticated,),
        basename='inventory-reservation',
        dev_fallback=False,
    ))
except Exception:
    pass