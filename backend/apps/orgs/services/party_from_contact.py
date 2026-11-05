"""An org takes a contact's values: as its default bill-to or ship-to party, and to fill what
it lacks (Bill, 2026-11-05, on the customer's contact card).

The org's parties live in its aspects — addresses.bill_to / ship_to (company, attention,
full_address, contact_id), emails.<role> (email), phones.<role> (number) — and a document takes
them when its customer is chosen (applyCustomerDefaults). The values come from the contact's
own records: its address record's full text, its phone record's number, its login email.
One formula, on the server; the card only asks.

The write goes through the save door (services/save.py), so every gate a save has applies:
the record must be visible and the role may edit it (the command runner, verbs.py), someone
else's edit hold refuses with 423, a stale version with 412, and the role's edit enumeration
is checked here first — the door would drop a field the role may not write (Bill, 2026-09-20),
and a command that quietly did nothing is worse than a refusal.

POST /wcapi/<org model>/<id>/from_contact/
     {contact_id, version, bill_to?: true, ship_to?: true, fill?: true}
  bill_to / ship_to  set that party from the contact (overwrites: it is an explicit choice)
  fill               an org with no primary contact takes this one as its primary, and with it
                     its name, email and the pointers to its email, phone, address and domain
                     records (the org hook follows a primary contact; Bill, 2026-10-31). An org
                     that has a primary keeps its name and email and takes only the pointers it
                     lacks — the address, phone, domain or email record this contact has and
                     the org does not.
"""
from __future__ import annotations

from typing import Any, Dict

from apps.core.services.door import Refused
from apps.orgs.behaviours import ORG_MODELS
from apps.orgs.services.contact_linking import contacts_of

PARTIES = ('bill_to', 'ship_to')
POINTERS = ('email_id', 'phone_id', 'address_id', 'domain_id')


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


def _writable(actor, model_key: str, fields) -> None:
    """The fields this role's edit enumeration names, else a refusal that says which are not."""
    from apps.core.services.role_filter import get_allowed_fields
    allowed = get_allowed_fields(actor, model_key, mode='edit')
    denied = sorted(f for f in fields if f not in allowed and not any(a.startswith(f + '.') for a in allowed))
    if denied:
        raise Refused(403, 'field_not_permitted',
                      f"Your role may not write {', '.join(denied)} on a {model_key}.",
                      {'model_name': model_key, 'fields': denied})


def from_contact(ctx) -> Dict[str, Any]:
    from apps.core.services.save import save_record
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

    changes: Dict[str, Any] = {}
    values = party_values(contact, org)
    for role in roles:
        for aspect, entry in values.items():
            current = changes.get(aspect) or dict(getattr(org, aspect) or {})
            current[role] = {**(current.get(role) or {}), **entry}
            changes[aspect] = current
    filled = []
    if fill:
        if not org.contact_id:
            changes['contact_id'] = contact.pk        # the hook takes its name, email and pointers
            filled = ['contact_id', 'attention', 'email', *POINTERS]
        else:
            for field in POINTERS:
                if not getattr(org, field) and getattr(contact, field):
                    changes[field] = getattr(contact, field)
                    filled.append(field)

    if changes:
        _writable(ctx.actor, ctx.model_key, changes.keys())
        saved = save_record(ctx.actor, {'id': org.pk, 'version': data.get('version'), **changes},
                            model_key=ctx.model_key)
        version = saved.version
    else:
        version = org.version
    ctx.messages.append(
        f"{ctx.model_key} #{org.pk} takes contact #{contact.pk}: "
        + ', '.join([*roles, *(['fill ' + ', '.join(filled)] if filled else ['nothing lacking'] if fill else [])]))
    return {'contact_id': contact.pk, 'set': roles, 'filled': filled, 'version': version}


def register() -> None:
    from apps.core.services.verbs import register_command
    for key in ORG_MODELS:
        register_command(key, 'from_contact', from_contact)
