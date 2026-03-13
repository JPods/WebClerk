from django.urls import path
from . import views

app_name = "ai_assistant"

urlpatterns = [
    # Core
    path("ask/", views.AskView.as_view(), name="ai-ask"),
    path("feedback/", views.FeedbackView.as_view(), name="ai-feedback"),
    path("health/", views.HealthView.as_view(), name="ai-health"),
    path("history/", views.HistoryView.as_view(), name="ai-history"),
    path("modes/", views.ModesView.as_view(), name="ai-modes"),
    # Specialized dev tools
    path("debug/", views.DebugView.as_view(), name="ai-debug"),
    path("review/", views.ReviewView.as_view(), name="ai-review"),
    path("generate/", views.GenerateView.as_view(), name="ai-generate"),
    # Admin
    path("reindex/", views.ReindexView.as_view(), name="ai-reindex"),
    # Alice notes & reporting
    path("note/", views.NoteView.as_view(), name="ai-note"),
    path("report/", views.ReportView.as_view(), name="ai-report"),
    path("search-feedback/", views.SearchFeedbackView.as_view(), name="ai-search-feedback"),
]
