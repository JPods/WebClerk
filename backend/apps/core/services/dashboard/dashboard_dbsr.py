"""DB Health summary for dashboard card.

Returns counts of database supporting records by category,
with approval and issue tracking.
"""
from django.db.models import Q
from apps.core.models.setting import Setting
from apps.core.models.report import Report


def get_dbsr_health(params: dict = None) -> dict:
    total_settings = Setting.objects.count()
    total_reports = Report.objects.count()

    # Use database-level JSON queries for speed
    explained_settings = Setting.objects.filter(
        metadata__explanation__isnull=False
    ).exclude(metadata__explanation='').count()

    approved_settings = Setting.objects.filter(
        metadata__explanation_approved=True
    ).count()

    explained_reports = Report.objects.filter(
        metadata__explanation__isnull=False
    ).exclude(metadata__explanation='').count()

    approved_reports = Report.objects.filter(
        metadata__explanation_approved=True
    ).count()

    total = total_settings + total_reports
    total_explained = explained_settings + explained_reports
    total_approved = approved_settings + approved_reports
    needs_review = total_explained - total_approved

    # Get health manifest issue count
    try:
        health = Setting.objects.get(ida='database-health', purpose='wc:database_health')
        config = health.config or {}
        issue_count = len(config.get('issues', []))
    except Setting.DoesNotExist:
        issue_count = 1  # manifest itself is missing

    return {
        'metrics': [
            {'label': 'Settings', 'value': str(total_settings)},
            {'label': 'Reports', 'value': str(total_reports)},
            {'label': 'Explained', 'value': str(total_explained)},
            {'label': 'Approved', 'value': f'{total_approved}/{total_explained}'},
            {'label': 'Review', 'value': str(needs_review)},
            {'label': 'Issues', 'value': str(issue_count)},
        ],
    }
