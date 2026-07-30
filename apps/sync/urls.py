from django.urls import path

from apps.sync.views.connection import (
    ConnectionListView,
    ConnectionDetailView,
    ConnectionSearchView,
)
from apps.sync.views.bundle_sync import BundleReceiveView

urlpatterns = [
    # Connection CRUD
    path("connections/", ConnectionListView.as_view(), name="connection-list"),
    path("connections/<int:pk>/", ConnectionDetailView.as_view(), name="connection-detail"),
    path("connections/search/", ConnectionSearchView.as_view(), name="connection-search"),

    # Bundle sync — machine-to-machine, key-authenticated
    path("receive/", BundleReceiveView.as_view(), name="bundle-receive"),
]
