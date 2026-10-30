"""The system administrator — who Alice sends the installation's problems to (Bill, 2026-10-29).

    company profile Setting: config.system_admin = {"name": "...", "id": <contact id>,
                                                     "action_delay": <days, default 3>}

action_delay is how long a problem may sit flagged on its own record (a Bundle in defects)
before Alice makes it an Action for the system administrator; each company sets its own.

The company names one. Until it does, Alice names the first admin login (lowest contact id) and
asks every admin to confirm or change the choice — one Action each. A system_admin who is no
longer an active admin (deleted, demoted, deactivated) is named again the same way, so the
problems never go to nobody. The company changes it by editing its profile; Setting.save
refuses an id that is not an active admin and writes the name from the contact.
"""
from __future__ import annotations

import logging
from typing import Optional

from django.db import transaction
from django.db.models import Q

logger = logging.getLogger(__name__)

ACTION_PURPOSE = 'system_admin'
DEFAULT_DELAY = 3                # days; config.system_admin.action_delay


def admins():
    """The active admin logins, first named first: own role admin, or superuser."""
    from apps.core.models import Contact
    return (Contact.objects.filter(is_active=True)
            .filter(Q(role='admin') | Q(is_superuser=True)).order_by('id'))


def entry(contact, action_delay: int = DEFAULT_DELAY) -> dict:
    """{name, id, action_delay} for a contact."""
    name = ' '.join(x for x in (contact.name_first, contact.name_last) if x) or contact.email or ''
    return {'name': name, 'id': contact.id, 'action_delay': action_delay}


def _delay(value) -> int:
    delay = value.get('action_delay', DEFAULT_DELAY) if isinstance(value, dict) else DEFAULT_DELAY
    if isinstance(delay, bool) or not isinstance(delay, int) or delay < 0:
        raise ValueError(f'system_admin.action_delay is a whole number of days, not {delay!r}.')
    return delay


def checked(value) -> dict:
    """config.system_admin as the company wrote it, made whole — or ValueError saying why."""
    if not isinstance(value, dict) or not value.get('id'):
        raise ValueError('system_admin is {"name": ..., "id": <contact id>, "action_delay": <days>}.')
    delay = _delay(value)
    contact = admins().filter(id=value['id']).first()
    if contact is None:
        raise ValueError(f'system_admin {value["id"]} is not an active admin login.')
    return entry(contact, delay)


def current() -> Optional[dict]:
    """{name, id, action_delay} of the system administrator; Alice names one when there is none to read.
    None only when the installation has no active admin at all."""
    from apps.core.models import Setting
    profile = Setting.objects.filter(purpose='wc:company_profile').order_by('id').first()
    if profile is None:
        logger.warning('system_admin: no company profile to read it from')
        return None
    named = (profile.config or {}).get('system_admin')
    if isinstance(named, dict) and named.get('id') and admins().filter(id=named['id']).exists():
        return {**named, 'action_delay': _delay(named)}
    return _name_first_admin(profile.pk, named)


def _name_first_admin(profile_pk: int, before) -> Optional[dict]:
    from apps.core.models import Setting
    from apps.core.models.log import Log
    first = admins().first()
    if first is None:
        logger.warning('system_admin: no active admin login to name')
        return None
    try:
        delay = _delay(before)                             # the company's delay outlives its admin
    except ValueError:
        delay = DEFAULT_DELAY
    chosen = entry(first, delay)
    with transaction.atomic():
        profile = Setting.objects.select_for_update().get(pk=profile_pk)
        config = dict(profile.config or {})
        if config.get('system_admin') != before:          # someone named one meanwhile
            return config.get('system_admin')
        config['system_admin'] = chosen
        Setting.objects.filter(pk=profile_pk).update(config=config)
        Log.write('audit', 'system_admin_named', model_name='setting', record_id=profile_pk,
                  name='company_profile.system_admin',
                  changes={'system_admin': {'old': before, 'new': chosen}},
                  details={'by': 'alice', 'rule': 'first active admin login'})
    _ask_admins(chosen, before)
    return chosen


def _ask_admins(chosen: dict, before) -> None:
    """One Action per admin: Alice named the system administrator; confirm or change it."""
    from apps.core.models import Action
    from apps.core.services import select_lists
    if select_lists.unlisted('action', {'purpose': ACTION_PURPOSE}):
        select_lists.add_value('action', 'purpose', ACTION_PURPOSE, label='System administrator')
    why = ('There was none.' if not before else
           f'{before.get("name") or before.get("id")} is no longer an active admin.')
    for admin in admins():
        Action(
            purpose=ACTION_PURPOSE,
            action={'en': f'Confirm the system administrator: {chosen["name"]}'},
            description={'en': (
                f'{why} Alice named {chosen["name"]} (contact {chosen["id"]}), the first admin '
                'login, as system administrator: bundle import defects and other installation '
                'problems go to them. To name someone else, edit config.system_admin '
                '{"name", "id"} on the Company Profile setting. Close this when settled.')},
            status='planned',
            priority=2,
            assigned_to=[{'id': admin.id}],
            refs={'alice': {'source': 'system_admin', 'named': chosen}},
        ).save()
