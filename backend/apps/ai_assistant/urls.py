from django.urls import path
from . import views

app_name = "ai_assistant"

urlpatterns = [
    # Core
    path("ask/", views.AskView.as_view(), name="ai-ask"),
    path("feedback/", views.FeedbackView.as_view(), name="ai-feedback"),
    path("health/", views.HealthView.as_view(), name="ai-health"),
    path("diagnose/", views.DiagnoseView.as_view(), name="ai-diagnose"),
    path("device-status/", views.DeviceStatusView.as_view(), name="ai-device-status"),
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
    # PII parse & correct
    path("pii/parse/", views.PiiParseView.as_view(), name="pii-parse"),
    path("pii/correct/", views.PiiCorrectView.as_view(), name="pii-correct"),
    # Contact paste parser
    path("contact/parse/", views.ContactParseView.as_view(), name="contact-parse"),
    path("contact/detect/", views.ContactDetectView.as_view(), name="contact-detect"),
    path("contact/parse-confirmed/", views.ContactParseConfirmedView.as_view(), name="contact-parse-confirmed"),
    path("contact/search/", views.ContactSearchView.as_view(), name="contact-search"),
    path("contact/correct/", views.ContactParseCorrectView.as_view(), name="contact-correct"),
    # Upstream Alice — any WC3 can serve these for downstream instances
    path("alice/ask/", views.AliceAskUpstreamView.as_view(), name="alice-ask-upstream"),
    path("alice/ask-claude/", views.AliceAskClaudeUpstreamView.as_view(), name="alice-ask-claude-upstream"),
    # Episodes — telemetry-style feed and review
    path("episodes/feed/", views.EpisodeFeedView.as_view(), name="episode-feed"),
    path("episodes/review/", views.EpisodeReviewView.as_view(), name="episode-review"),
    path("episodes/review/bulk/", views.EpisodeBulkReviewView.as_view(), name="episode-review-bulk"),
    path("episodes/summary/", views.EpisodeSummaryView.as_view(), name="episode-summary"),
    path("episodes/detect-patterns/", views.EpisodeDetectPatternsView.as_view(), name="episode-detect-patterns"),
    # Support — coaching distribution, help patterns, summary
    path("coaching/", views.CoachingFeedView.as_view(), name="coaching-feed"),
    path("support/summary/", views.SupportSummaryView.as_view(), name="support-summary"),
    path("support/detect-patterns/", views.SupportDetectPatternsView.as_view(), name="support-detect-patterns"),
]
