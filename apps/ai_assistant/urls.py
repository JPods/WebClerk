from django.urls import path
from . import views

app_name = "ai_assistant"

urlpatterns = [
    path("ask/", views.AskView.as_view(), name="ai-ask"),
    path("feedback/", views.FeedbackView.as_view(), name="ai-feedback"),
    path("health/", views.HealthView.as_view(), name="ai-health"),
    path("history/", views.HistoryView.as_view(), name="ai-history"),
]
