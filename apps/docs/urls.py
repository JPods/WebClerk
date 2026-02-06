from django.urls import path
from . import views_stats
from .views_upload import DocumentUploadView, DocumentDownloadView, DocumentDeleteView

urlpatterns = [
    path('stats/', views_stats.DocsStatsView.as_view(), name='docs-stats'),
]

# Upload endpoints (mounted at wcapi/ in main urls.py)
upload_urlpatterns = [
    path('upload/', DocumentUploadView.as_view(), name='document-upload'),
    path('document/<int:document_id>/', DocumentDownloadView.as_view(), name='document-download'),
    path('document/<int:document_id>/delete/', DocumentDeleteView.as_view(), name='document-delete'),
]