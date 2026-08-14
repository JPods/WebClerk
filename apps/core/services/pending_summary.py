"""Pending posting summary for dashboard cards.

Graph notes:
  - Unapplied payments aging (bar — buckets: 0-7d, 8-14d, 15-30d, 30+d)
  - Average time to post trend (line — weekly average over trailing 90 days)
  - Worst offenders table (top 5 oldest unposted records)
"""
from django.utils import timezone
from apps.accounts.models import GlJournal


def get_pending_summary(params: dict = None) -> dict:
    now_ms = int(timezone.now().timestamp() * 1000)

    # Unposted GL entries
    unposted = GlJournal.objects.filter(is_posted=False)
    unapplied_count = unposted.count()

    # Average time to post (posted entries only, trailing 90 days)
    ninety_days_ms = now_ms - (90 * 24 * 60 * 60 * 1000)
    posted_recent = GlJournal.objects.filter(
        is_posted=True,
        dt_created__gte=ninety_days_ms,
    ).values_list('dt_created', 'date_posted')

    post_times = []
    for dt_created, date_posted in posted_recent:
        if dt_created and date_posted:
            try:
                # date_posted is a date field, dt_created is epoch ms
                import datetime
                posted_ms = int(datetime.datetime.combine(
                    date_posted, datetime.time.min,
                    tzinfo=datetime.timezone.utc
                ).timestamp() * 1000)
                delta_hours = (posted_ms - dt_created) / (1000 * 60 * 60)
                if delta_hours >= 0:
                    post_times.append(delta_hours)
            except (TypeError, ValueError):
                pass

    avg_hours = sum(post_times) / len(post_times) if post_times else 0
    worst_hours = max(post_times) if post_times else 0

    # Format time display
    if avg_hours < 24:
        avg_display = f"{avg_hours:.1f}h"
    else:
        avg_display = f"{avg_hours / 24:.1f}d"

    if worst_hours < 24:
        worst_display = f"{worst_hours:.1f}h"
    else:
        worst_display = f"{worst_hours / 24:.1f}d"

    return {
        "metrics": [
            {"label": "Unapplied", "value": f"{unapplied_count:,}"},
            {"label": "Avg Post", "value": avg_display},
            {"label": "Worst Post", "value": worst_display},
        ],
    }
