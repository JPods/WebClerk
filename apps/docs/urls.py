from django.urls import path
from . import views_stats
from .views_upload import DocumentUploadView, DocumentDownloadView, DocumentDeleteView
from .views_qa import ApplyQuestionsView, ListQuestionGroupsView, ParentQAView

urlpatterns = [
    path('stats/', views_stats.DocsStatsView.as_view(), name='docs-stats'),
    # QA endpoints
    path('qa/apply/', ApplyQuestionsView.as_view(), name='qa-apply'),
    path('qa/groups/', ListQuestionGroupsView.as_view(), name='qa-groups'),
    path('qa/<str:parent_model>/<int:parent_id>/', ParentQAView.as_view(), name='qa-parent'),
]

# Upload endpoints (mounted at wcapi/ in main urls.py)
upload_urlpatterns = [
    path('upload/', DocumentUploadView.as_view(), name='document-upload'),
    path('document/<int:document_id>/', DocumentDownloadView.as_view(), name='document-download'),
    path('document/<int:document_id>/delete/', DocumentDeleteView.as_view(), name='document-delete'),
]