"""An org's contacts are the contacts whose ForeignKey of the org's role points at it
(Contact.customer / vendor / manufacturer / rep). That is the one source (Bill, 2026-10-17):
the org's ``refs.links.contact`` is served from it, and linking a contact to an org is an
edit of the contact's own field (the CONTACTS panel writes the contact), so nothing drifts."""
from __future__ import annotations

from typing import List, Optional

from apps.core.models import Contact

#: The org a contact can belong to, by org_type: the contact's ForeignKey of the same name.
CONTACT_ROLES = ('customer', 'vendor', 'manufacturer', 'rep')


def contact_role(org) -> Optional[str]:
    role = (getattr(org, 'org_type', None) or '').lower()
    return role if role in CONTACT_ROLES else None


def contacts_of(org):
    """The contacts linked to this org, its primary contact first."""
    role = contact_role(org)
    if role is None or not getattr(org, 'pk', None):
        return Contact.objects.none()
    return Contact.objects.filter(**{f'{role}_id': org.pk}).order_by('id')


def served_contact_links(org) -> List[dict]:
    """``refs.links.contact`` as the org's GET serves it."""
    links = [{'id': c.pk, 'name': c.attention or c.email or f'Contact #{c.pk}'}
             for c in contacts_of(org).only('id', 'attention', 'email')]
    primary = getattr(org, 'contact_id', None)
    links.sort(key=lambda link: link['id'] != primary)
    return links
