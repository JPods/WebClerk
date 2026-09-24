"""The stamp a comment carries — one shape for a person and for a hook.

CommentsPanel writes ``{user, mgs, time, user_id}`` into ``comments.<channel>``
(Bill, 2026-09-24: a comment a hook adds carries the same dt/user stamp as one
entered by hand). ``time`` is stored in UTC (Axiom 14); the panel shows it as stored.
"""
from __future__ import annotations

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
    return {**who, 'time': timezone.now().strftime('%Y-%m-%dT%H:%M:%SZ')}
