from django.urls import path
from apps.docs.views.document_views import (
    DocumentListCreateView,
    DocumentRetrieveUpdateView,
    DocumentSearchView,
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

urlpatterns = [
    path('documents/', DocumentListCreateView.as_view(), name='document-list'),
    path('documents/<int:pk>/', DocumentRetrieveUpdateView.as_view(), name='document-detail'),
    path('documents/search/', DocumentSearchView.as_view(), name='document-search'),
    # Linkages
    path('linkages/', LinkageListCreateView.as_view(), name='linkage-list'),
    path('linkages/<int:pk>/', LinkageRetrieveUpdateView.as_view(), name='linkage-detail'),
    path('linkages/<int:pk>/links/', LinkageAddRemoveLinkView.as_view(), name='linkage-links'),
    # QA
    path('qas/', QAListCreateView.as_view(), name='qa-list'),
    path('qas/<int:pk>/', QARetrieveUpdateView.as_view(), name='qa-detail'),
    path('qas/search/', QASearchView.as_view(), name='qa-search'),
]