from django.urls import path
from apps.docs.views_tag import TagHierarchyView
from apps.docs.views_readme import (
    ReadmeSearchIndexView,
    ReadmeDetailView,
    ReadmeTopView,
    ReadmeSyncView,
)

urlpatterns = [
    # Tag hierarchy (support both with and without trailing slash)
    path("tag/<int:pk>/hierarchy", TagHierarchyView.as_view(), name="tag-hierarchy"),
    path("tag/<int:pk>/hierarchy/", TagHierarchyView.as_view(), name="tag-hierarchy-slash"),

    # Readme endpoints
    path("readme/search-index", ReadmeSearchIndexView.as_view(), name="readme-search-index"),
    path("readme/top", ReadmeTopView.as_view(), name="readme-top"),
    path("readme/sync", ReadmeSyncView.as_view(), name="readme-sync"),
    path("readme/<slug:slug>/", ReadmeDetailView.as_view(), name="readme-detail"),
]