"""The stamp a comment carries — one shape for a person and for a hook.

CommentsPanel writes ``{user, mgs, time, user_id}`` into ``comments.<channel>``
(Bill, 2026-09-24: a comment a hook adds carries the same dt/user stamp as one
entered by hand).

``time`` is a displayed dt, not a functional one (Bill, 2026-09-24): local time with its
zone — "Sep 24, 2026, 05:05 PM EDT" — the exception to Axiom 14 recorded in
readmes/accepted-deviations.md. Nothing sorts or computes on it; order is list position.
A hook has no browser, so it uses the installation's zone (settings.TIME_ZONE).
"""
from __future__ import annotations

from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone


def stamp(user=None) -> dict:
    """Who and when, for a new comment. ``user`` is a Contact login or None (the system)."""
    if user is not None and getattr(user, 'is_authenticated', False):
        name = (' '.join(filter(None, (getattr(user, 'name_first', ''),
                                       getattr(user, 'name_last', '')))).strip()
                or getattr(user, 'email', '') or f'contact {user.pk}')
        who = {'user': name, 'user_id': user.pk}
    else:
        who = {'user': 'system', 'user_id': None}
    return {**who, 'time': display_time()}


def display_time(now=None) -> str:
    """The panel's 'datetime_tz' label, in the installation's zone."""
    local = (now or timezone.now()).astimezone(ZoneInfo(settings.TIME_ZONE))
    return local.strftime('%b %-d, %Y, %I:%M %p %Z')
