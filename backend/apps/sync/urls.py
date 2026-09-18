from django.urls import path

from apps.sync.views.connection import (
    ConnectionListView,
    ConnectionDetailView,
    ConnectionSearchView,
)
from apps.sync.views.bundle_sync import BundleReceiveView
from apps.sync.views.po_so_bundle import (
    POToSOSendView,
    BundleApproveView,
    BundleStatusView,
    BundleCallbackView,
    POStatusPollView,
)
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

    # PO → SO cross-instance commerce
    path("po-to-so/<int:pk>/", POToSOSendView.as_view(), name="po-to-so-send"),
    path("bundle/<str:bundle_uuid>/approve/", BundleApproveView.as_view(), name="bundle-approve"),
    path("bundle/<str:bundle_uuid>/status/", BundleStatusView.as_view(), name="bundle-status"),
    path("bundle/callback/", BundleCallbackView.as_view(), name="bundle-callback"),
    path("po-status/<int:pk>/<str:bundle_uuid>/", POStatusPollView.as_view(), name="po-status-poll"),

    # Form library — Andi/Alice is librarian, local checks out on demand
    path("form-library/", FormLibraryCatalogView.as_view(), name="form-library-catalog"),
    path("form-library/checkout/", FormLibraryCheckoutView.as_view(), name="form-library-checkout"),
    path("form-library/submit/", FormLibrarySubmitView.as_view(), name="form-library-submit"),
    path("form-library/restore/", FormLibraryRestoreView.as_view(), name="form-library-restore"),
]
