"""Line contacts — the people associated with what a line sold (readme 109 P6).

Bill, 2026-11-12: "a customer is a furniture store that buys a warranty for one of their
customers. The end contact would be listed [as] the contacts.warranty_holder", and where:
"in the invoice_line.refs.contacts[{"role": …}] and in the serialized record. They are also
listed as a contact with their .refs.links.serial[{}], invoice, invoice_line".

One list, four places, one writer (this module):

    line.refs.contacts[]            {role, contact_id, display_name, company, email, phone}
    serial.refs.contacts[]          the same entries, on each serial the invoice line issued
    contact.refs.links.<doc>_line   [{id}]   the lines that name the contact
    contact.refs.links.<doc>        [{id}]   their documents
    contact.refs.links.serial       [{id}]   the serials

A quote, order and invoice line carries the list, and convert carries it forward. The role is
on the list each installation edits: the contact definition's ``selectlists.transaction_role``
(a person who saves a role not on it is asked first and may add it — select_lists.py).
``contact_id`` is the pointer; the rest of an entry is what the contact read when it was first
named on the line, and is not rewritten by later saves (a document does not change when the
contact does).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from apps.core.services.door import Refused

#: The line models that carry contacts, by Django model name → their document's key.
LINE_DOCUMENTS = {'quoteline': 'quote', 'orderline': 'order', 'invoiceline': 'invoice'}

#: Where the role list lives: one list for every line and serial (select_lists.py).
ROLE_LIST_MODEL, ROLE_LIST_FIELD = 'contact', 'transaction_role'

#: The first role every installation starts with (Bill's example).
SEED_ROLES = [('warranty_holder', 'Warranty Holder')]

#: What an entry copies from the contact, named as the contact names it.
SNAPSHOT_FIELDS = ('display_name', 'company', 'email', 'phone')


def document_key(line) -> Optional[str]:
    """'invoice' for an invoice line; None for a line that carries no contacts."""
    return LINE_DOCUMENTS.get(type(line)._meta.model_name)


def entries(refs) -> List[Dict[str, Any]]:
    rows = refs.get('contacts') if isinstance(refs, dict) else None
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def contact_ids(refs) -> Set[int]:
    out: Set[int] = set()
    for row in entries(refs):
        try:
            out.add(int(row.get('contact_id')))
        except (TypeError, ValueError):
            continue
    return out


def _role_is_listed(role: str, actor) -> None:
    from apps.core.services import definition, select_lists
    off = select_lists.unlisted(ROLE_LIST_MODEL, {ROLE_LIST_FIELD: role})
    if not off:
        return
    is_person = actor is not None and getattr(actor, 'kind', None) in ('user', 'staff')
    may_add = {ROLE_LIST_FIELD: bool(is_person and definition.may_change(actor))}
    if not is_person:
        message = (f"'{role}' is not on the list of roles a contact can have on a line. Code wrote "
                   f"it: fix the writer, or a staff member adds the role to the list first.")
        may_add = {}
    elif may_add[ROLE_LIST_FIELD]:
        message = f"'{role}' is not on the list of roles yet. Add it to the list and save again?"
    else:
        message = (f"'{role}' is not on the list of roles yet. Choose a listed role, or ask a "
                   f"staff member to add it.")
    raise Refused(400, 'value_not_listed', message,
                  {'model_name': ROLE_LIST_MODEL, 'unlisted': off, 'may_add': may_add})


def _text(value) -> str:
    return '' if value is None else str(value)


def settle(line, before_refs=None) -> None:
    """Before the line saves: each contact entry is whole. Refuses an entry with no role or no
    contact, a role not on the list, and a contact that does not exist. An entry already stored
    with the same role and contact keeps what it copied; a new one copies from the contact."""
    if document_key(line) is None:
        return
    refs = line.refs if isinstance(line.refs, dict) else {}
    raw = refs.get('contacts')
    if raw is None or raw == []:
        return
    if not isinstance(raw, list):
        raise Refused(400, 'line_contacts_not_a_list',
                      'refs.contacts is a list: [{"role": "warranty_holder", "contact_id": 12}].',
                      {'line_id': line.pk})
    from apps.core.models import Contact
    stored = {(r.get('role'), r.get('contact_id')): r for r in entries(before_refs)}
    actor = getattr(line, '_actor', None)
    out: List[Dict[str, Any]] = []
    seen = set()
    for row in raw:
        role = _text(row.get('role')).strip() if isinstance(row, dict) else ''
        raw_id = row.get('contact_id') if isinstance(row, dict) else None
        try:
            contact_id = int(raw_id)
        except (TypeError, ValueError):
            contact_id = None
        if not role or contact_id is None:
            raise Refused(400, 'line_contact_incomplete',
                          'Each contact on a line names its role and the contact: '
                          '{"role": "warranty_holder", "contact_id": 12}.',
                          {'line_id': line.pk, 'entry': row})
        if (role, contact_id) in seen:
            continue
        seen.add((role, contact_id))
        if (role, contact_id) in stored:
            out.append(stored[(role, contact_id)])
            continue
        _role_is_listed(role, actor)
        contact = Contact.objects.filter(pk=contact_id).first()
        if contact is None:
            raise Refused(400, 'line_contact_not_found',
                          f'There is no contact {contact_id} to be the {role} of this line.',
                          {'line_id': line.pk, 'contact_id': contact_id})
        out.append({'role': role, 'contact_id': contact.pk,
                    **{f: _text(getattr(contact, f, '')) for f in SNAPSHOT_FIELDS}})
    line.refs = {**refs, 'contacts': out}


def _named_on_another_line(line, doc: str, contact_id: int) -> bool:
    others = type(line).objects.filter(**{f'{doc}_id': getattr(line, f'{doc}_id')}).exclude(pk=line.pk)
    return any(contact_id in contact_ids(refs) for refs in others.values_list('refs', flat=True))


def _serials_of(line):
    """The serials an invoice line issued (Serial.issue_on_invoice stamps both ids)."""
    from apps.products.models.serial import Serial
    if document_key(line) != 'invoice' or not line.pk:
        return Serial.objects.none()
    return Serial.objects.filter(config__sales_line_ref=line.pk, config__invoice_id=line.invoice_id)


def write_serial(serial, new_entries: List[Dict[str, Any]]) -> None:
    """A serial's contacts become ``new_entries``; the contacts list the serial, or stop."""
    from apps.core.models import Contact
    from apps.core.services.reciprocal_links import set_side
    refs = serial.refs if isinstance(serial.refs, dict) else {}
    old, new = contact_ids(refs), contact_ids({'contacts': new_entries})
    if entries(refs) == new_entries:
        return
    serial.refs = {**refs, 'contacts': new_entries}
    serial.save(update_fields=['refs'])
    for contact_id in new - old:
        set_side(Contact, contact_id, 'serial', serial.pk, True)
    for contact_id in old - new:
        set_side(Contact, contact_id, 'serial', serial.pk, False)


def link(line, before_refs) -> None:
    """After the line saved: the contacts it names list it and its document; the ones it no
    longer names stop. Its serials carry the same list."""
    doc = document_key(line)
    if doc is None:
        return
    old, new = contact_ids(before_refs), contact_ids(line.refs)
    if old != new:
        from apps.core.models import Contact
        from apps.core.services.reciprocal_links import set_side
        doc_id = getattr(line, f'{doc}_id')
        for contact_id in new - old:
            set_side(Contact, contact_id, f'{doc}_line', line.pk, True)
            set_side(Contact, contact_id, doc, doc_id, True)
        for contact_id in old - new:
            set_side(Contact, contact_id, f'{doc}_line', line.pk, False)
            if not _named_on_another_line(line, doc, contact_id):
                set_side(Contact, contact_id, doc, doc_id, False)
    if entries(before_refs) != entries(line.refs):
        for serial in _serials_of(line):
            write_serial(serial, entries(line.refs))


def unlink(line) -> None:
    """The line is deleted: its contacts no longer list it, nor its document unless another of
    the document's lines names them. A serial keeps who holds it."""
    doc = document_key(line)
    if doc is None:
        return
    from apps.core.models import Contact
    from apps.core.services.reciprocal_links import set_side
    for contact_id in contact_ids(line.refs):
        set_side(Contact, contact_id, f'{doc}_line', line.pk, False)
        if not _named_on_another_line(line, doc, contact_id):
            set_side(Contact, contact_id, doc, getattr(line, f'{doc}_id'), False)


def onto_serial(serial, invoice_line_id) -> None:
    """A serial issued on an invoice line takes that line's contacts."""
    if not invoice_line_id:
        return
    from apps.transactions.models import InvoiceLine
    refs = InvoiceLine.objects.filter(pk=invoice_line_id).values_list('refs', flat=True).first()
    if refs is not None:
        write_serial(serial, entries(refs))


def carried(src_line) -> List[Dict[str, Any]]:
    """What convert carries to the next document's line: role and contact; the new line copies
    the rest from the contact as it stands when that line is made."""
    return [{'role': r.get('role'), 'contact_id': r.get('contact_id')}
            for r in entries(getattr(src_line, 'refs', None))]
