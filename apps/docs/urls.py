from django.urls import path
from apps.docs.views.document_views import (
    DocumentListCreateView,
    DocumentRetrieveUpdateView,
    DocumentSearchView,
    ReadmeIndexView,
    ReadmeDetailView,
    ReadmeSearchIndexView,
    ReadmeTopView,
    ReadmeSyncView,
)
from apps.docs.views.linkage_views import (
    LinkageListCreateView,
    LinkageRetrieveUpdateView,
    LinkageAddRemoveLinkView,
)
from apps.docs.views.qa_views import (
    QAListCreateView,
    QARetrieveUpdateView,
    QASearchView,
)
from apps.docs.views.tag_views import (
    TagListCreateView,
    TagRetrieveUpdateView,
    TagHierarchyView,
    TagSearchView,
)
from apps.docs.views.related_views import (
    RelatedDocumentsView,
    RelatedActionsView,
)

urlpatterns = [
    path('documents/', DocumentListCreateView.as_view(), name='document-list'),
    path('documents/<int:pk>/', DocumentRetrieveUpdateView.as_view(), name='document-detail'),
    path('documents/search/', DocumentSearchView.as_view(), name='document-search'),
    # Readme specialized endpoints (slug-based)
    path('readmes/', ReadmeIndexView.as_view(), name='readme-index'),
    path('readmes/search-index/', ReadmeSearchIndexView.as_view(), name='readme-search-index'),
    path('readmes/top/', ReadmeTopView.as_view(), name='readme-top'),
    path('readmes/sync/', ReadmeSyncView.as_view(), name='readme-sync'),
    path('readmes/<slug:slug>/', ReadmeDetailView.as_view(), name='readme-detail'),
    # Linkages
    path('linkages/', LinkageListCreateView.as_view(), name='linkage-list'),
    path('linkages/<int:pk>/', LinkageRetrieveUpdateView.as_view(), name='linkage-detail'),
    path('linkages/<int:pk>/links/', LinkageAddRemoveLinkView.as_view(), name='linkage-links'),
    # Generic related endpoints
    path('<str:model>/<int:pk>/documents/', RelatedDocumentsView.as_view(), name='model-related-documents'),
    path('<str:model>/<int:pk>/actions/', RelatedActionsView.as_view(), name='model-related-actions'),
    # QA
    path('qas/', QAListCreateView.as_view(), name='qa-list'),
    path('qas/<int:pk>/', QARetrieveUpdateView.as_view(), name='qa-detail'),
    path('qas/search/', QASearchView.as_view(), name='qa-search'),
    # Tags
    path('tags/', TagListCreateView.as_view(), name='tag-list'),
    path('tags/<int:pk>/', TagRetrieveUpdateView.as_view(), name='tag-detail'),
    path('tags/<int:pk>/hierarchy/', TagHierarchyView.as_view(), name='tag-hierarchy'),
    path('tags/search/', TagSearchView.as_view(), name='tag-search'),
]