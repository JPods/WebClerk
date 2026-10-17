"""Unassigned emails for the Administration dashboard card (Bill, 2026-10-16).

An Email record with no contact belongs to no one: no one can reach it, mail it, or sign
in with it. Admins correct these by hand from the list the card links to
(/databrowser?model=email&contact__isnull=true) — Alice does not guess an owner.
"""
from apps.communications.models import Email


def get_email_health(params: dict = None) -> dict:
    unassigned = Email.objects.filter(contact__isnull=True).count()
    return {'metrics': [
        {'label': 'Unassigned', 'value': str(unassigned)},
        {'label': 'Emails', 'value': str(Email.objects.count())},
    ]}
