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


#: What an org copies from its primary contact (Bill, 2026-10-31: a de-normalized value is
#: never edited where it is copied, only on the record it comes from). The name and email are
#: stored on the org; the pointers lead to the contact's own email/phone/address/domain.
FOLLOWED = ('attention', 'email', 'email_id', 'phone_id', 'address_id', 'domain_id')


def contact_values(contact_id) -> dict:
    """The values an org takes from this contact, as stored now."""
    row = Contact.objects.filter(pk=contact_id).values(*FOLLOWED).first() or {}
    return {k: row.get(k) for k in FOLLOWED}


def follow_contact(contact_id) -> int:
    """The orgs whose primary contact this is take its values again. Returns how many changed."""
    from django.db.models import Q
    from apps.orgs.models import OrgBase
    values = contact_values(contact_id)
    if not values:
        return 0
    stale = Q()
    for k, v in values.items():
        stale |= ~Q(**{k: v}) if v is not None else Q(**{f'{k}__isnull': False})
    return OrgBase.objects.filter(contact_id=contact_id).filter(stale).update(**values)
