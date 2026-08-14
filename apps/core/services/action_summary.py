"""Action summary metrics for dashboard cards — status + deadline buckets.

Graph notes:
  - Status distribution (donut — open, in_progress, complete, review)
  - Overdue trend (line — count of overdue actions per week, trailing 12 weeks)
  - Actions by assignee (horizontal bar — who has the most open)
  - Completion rate (line — completed per week vs created per week)
"""
from datetime import timedelta
from django.utils import timezone
from apps.core.models import Action


ACTIVE_STATUSES = ['open', 'in_progress', 'created', 'Not started', 'In progress', 'active']


def _ms(dt):
    return int(dt.timestamp() * 1000)


def get_action_summary(params: dict = None) -> dict:
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    tomorrow_end = today_start + timedelta(days=2)
    week_end = today_start + timedelta(days=7)

    ms_today_start = _ms(today_start)
    ms_today_end = _ms(today_end)
    ms_tomorrow_end = _ms(tomorrow_end)
    ms_week_end = _ms(week_end)

    active = Action.objects.filter(status__in=ACTIVE_STATUSES)
    total_active = active.count()
    overdue = active.filter(dt_deadline__gt=0, dt_deadline__lt=ms_today_start).count()
    today = active.filter(dt_deadline__gte=ms_today_start, dt_deadline__lt=ms_today_end).count()
    tomorrow = active.filter(dt_deadline__gte=ms_today_end, dt_deadline__lt=ms_tomorrow_end).count()
    this_week = active.filter(dt_deadline__gte=ms_tomorrow_end, dt_deadline__lt=ms_week_end).count()
    no_date = active.filter(dt_deadline=0).count() + active.filter(dt_deadline__isnull=True).count()

    return {
        "metrics": [
            {"label": "Active", "value": f"{total_active:,}"},
            {"label": "Overdue", "value": f"{overdue:,}"},
            {"label": "Today", "value": f"{today:,}"},
            {"label": "Tomorrow", "value": f"{tomorrow:,}"},
            {"label": "This Week", "value": f"{this_week:,}"},
            {"label": "No Date", "value": f"{no_date:,}"},
        ],
    }
