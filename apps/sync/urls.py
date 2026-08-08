from django.urls import path

from apps.sync.views.connection import (
    ConnectionListView,
    ConnectionDetailView,
    ConnectionSearchView,
)
from apps.sync.views.bundle_sync import BundleReceiveView
from apps.sync.views.form_library import (
    FormLibraryCatalogView,
    FormLibraryCheckoutView,
    FormLibrarySubmitView,
    FormLibraryRestoreView,
)

urlpatterns = [
    # Connection CRUD
    path("connections/", ConnectionListView.as_view(), name="connection-list"),
    path("connections/<int:pk>/", ConnectionDetailView.as_view(), name="connection-detail"),
    path("connections/search/", ConnectionSearchView.as_view(), name="connection-search"),

    # Bundle sync — machine-to-machine, key-authenticated
    path("receive/", BundleReceiveView.as_view(), name="bundle-receive"),

    # Form library — Andi/Alice is librarian, local checks out on demand
    path("form-library/", FormLibraryCatalogView.as_view(), name="form-library-catalog"),
    path("form-library/checkout/", FormLibraryCheckoutView.as_view(), name="form-library-checkout"),
    path("form-library/submit/", FormLibrarySubmitView.as_view(), name="form-library-submit"),
    path("form-library/restore/", FormLibraryRestoreView.as_view(), name="form-library-restore"),
]
