"""An org takes a contact's values: as its default bill-to or ship-to party, and to fill what
it lacks (Bill, 2026-11-05, on the customer's contact card).

The org's parties live in its aspects — addresses.bill_to / ship_to (company, attention,
full_address, contact_id), emails.<role> (email), phones.<role> (number) — and a document takes
them when its customer is chosen (applyCustomerDefaults). The values come from the contact's
own records: its address record's full text, its phone record's number, its login email.
One formula, on the server; the card only asks.

POST /wcapi/<org model>/<id>/from_contact/  {contact_id, bill_to?: true, ship_to?: true, fill?: true}
  bill_to / ship_to  set that party from the contact (overwrites: it is an explicit choice)
  fill               what the org lacks — attention, email, and the pointers to the contact's
                     email, phone, address and domain records — it takes from the contact;
                     what it has, it keeps
"""
from __future__ import annotations

from typing import Any, Dict

from apps.core.services.door import Refused
from apps.orgs.behaviours import ORG_MODELS
from apps.orgs.services.contact_linking import FOLLOWED, contacts_of

PARTIES = ('bill_to', 'ship_to')


def party_values(contact, org) -> Dict[str, Dict[str, Any]]:
    """What the contact gives a party: the address entry, the email entry, the phone entry."""
    from apps.communications.models import Address, Phone
    address = Address.objects.filter(pk=contact.address_id).only('full').first() if contact.address_id else None
    phone = Phone.objects.filter(pk=contact.phone_id).only('number').first() if contact.phone_id else None
    attention = (contact.attention or contact.get_full_name() or '').strip()
    return {
        'addresses': {'contact_id': contact.pk, 'company': (contact.company or org.company or '').strip(),
                      'attention': attention, 'full_address': (address.full if address else '') or '',
                      'instructions': ''},
        'emails': {'email_id': contact.email_id, 'email': contact.email or ''},
        'phones': {'phone_id': contact.phone_id, 'number': (phone.number if phone else '') or ''},
    }


def from_contact(ctx) -> Dict[str, Any]:
    org, data = ctx.obj, ctx.data
    contact_id = data.get('contact_id')
    contact = contacts_of(org).filter(pk=contact_id).first() if contact_id else None
    if contact is None:
        raise Refused(400, 'not_this_orgs_contact',
                      f"Contact #{contact_id} is not one of this {ctx.model_key}'s contacts: "
                      f"add it in the Contacts panel first.", {'contact_id': contact_id})
    roles = [r for r in PARTIES if data.get(r)]
    fill = bool(data.get('fill'))
    if not roles and not fill:
        raise Refused(400, 'nothing_asked', 'Say what to take: bill_to, ship_to, or fill.', {})

    values = party_values(contact, org)
    changed = set()
    for role in roles:
        for aspect, entry in values.items():
            current = dict(getattr(org, aspect) or {})
            current[role] = {**(current.get(role) or {}), **entry}
            setattr(org, aspect, current)
            changed.add(aspect)
    filled = []
    if fill:
        for field in FOLLOWED:
            if not getattr(org, field) and getattr(contact, field):
                setattr(org, field, getattr(contact, field))
                filled.append(field)
                changed.add(field)
    if changed:
        org.save(update_fields=sorted(changed) + ['dt_modified', 'version'])
    ctx.messages.append(
        f"{ctx.model_key} #{org.pk} takes contact #{contact.pk}: "
        + ', '.join([*roles, *(['fill ' + ', '.join(filled)] if filled else [])]))
    return {'contact_id': contact.pk, 'set': roles, 'filled': filled, 'version': org.version}


def register() -> None:
    from apps.core.services.verbs import register_command
    for key in ORG_MODELS:
        register_command(key, 'from_contact', from_contact)
