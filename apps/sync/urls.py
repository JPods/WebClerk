from django.urls import path
from .views.connection import ConnectionListView, ConnectionDetailView, ConnectionSearchView

app_name = 'sync'

urlpatterns = [
    path('connections/', ConnectionListView.as_view(), name='connection-list'),
    path('connections/<int:pk>/', ConnectionDetailView.as_view(), name='connection-detail'),
    path('connections/search/', ConnectionSearchView.as_view(), name='connection-search'),
]
