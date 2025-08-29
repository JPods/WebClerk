from django.urls import path
from apps.docs.views.document_views import (
    DocumentListCreateView,
    DocumentRetrieveUpdateView,
    DocumentSearchView,
)

urlpatterns = [
    path('documents/', DocumentListCreateView.as_view(), name='document-list'),
    path('documents/<int:pk>/', DocumentRetrieveUpdateView.as_view(), name='document-detail'),
    path('documents/search/', DocumentSearchView.as_view(), name='document-search'),
]