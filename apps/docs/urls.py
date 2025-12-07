from django.urls import path
from . import views_stats

urlpatterns = [
    path('stats/', views_stats.DocsStatsView.as_view(), name='docs-stats'),
]