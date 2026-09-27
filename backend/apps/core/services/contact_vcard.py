"""
vCard export — a contact or org out as .vcf text (Google, Apple, Dot, Popl, HiHello read it).

    export_vcard       — single contact/org → .vcf text
    export_vcards      — batch contacts → .vcf text

Import went with the other file parsers (import plan §17, 2026-09-27): WebClerk parses no file.
A .vcf is cleaned outside (Alice or any tool) into a bundle and comes in through the import route.
"""
from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger('webclerk3')


# ── Export ────────────────────────────────────────────────────────────────

def _contact_to_vcard(contact) -> str:
    """Convert a Contact record to vCard 3.0 text."""
    lines = ['BEGIN:VCARD', 'VERSION:3.0', 'PRODID:-//WebClerk//Contact Export']

    first = contact.name_first or ''
    last = contact.name_last or ''
    if first or last:
        lines.append(f'FN:{first} {last}'.strip())
        lines.append(f'N:{last};{first};;;')

    if contact.company:
        lines.append(f'ORG:{contact.company}')
    if contact.title:
        lines.append(f'TITLE:{contact.title}')
    if contact.email:
        lines.append(f'EMAIL;TYPE=WORK:{contact.email}')

    # Phone — try linked Phone record
    if contact.phone_id:
        try:
            from apps.core.models import Phone
            ph = Phone.objects.filter(pk=contact.phone_id).first()
            if ph and ph.number:
                ptype = (ph.name or 'work').upper()
                lines.append(f'TEL;TYPE={ptype}:{ph.number}')
        except Exception:
            pass

    # Address — try linked Address record
    if contact.address_id:
        try:
            from apps.core.models import Address
            addr = Address.objects.filter(pk=contact.address_id).first()
            if addr:
                # ADR: PO;ext;street;city;state;zip;country
                lines.append(
                    f'ADR;TYPE=WORK:;;{addr.address1 or ""};'
                    f'{addr.city or ""};{addr.state or ""};'
                    f'{addr.zip or ""};{addr.country or ""}'
                )
        except Exception:
            pass

    if contact.department:
        lines.append(f'X-DEPARTMENT:{contact.department}')

    lines.append('END:VCARD')
    return '\r\n'.join(lines)


def export_vcard(params: dict) -> dict[str, Any]:
    """Export a single contact as vCard text.

    Params:
        contact_id: int — the Contact PK
    """
    from apps.core.models import Contact

    contact_id = params.get('contact_id')
    if not contact_id:
        return {'error': 'contact_id required'}

    try:
        contact = Contact.objects.get(pk=int(contact_id), is_active=True)
    except Contact.DoesNotExist:
        return {'error': f'Contact {contact_id} not found'}

    return {
        'vcard': _contact_to_vcard(contact),
        'filename': f'{contact.name_first or ""}_{contact.name_last or ""}_{contact.ida}.vcf'.strip('_'),
    }


def export_vcards(params: dict) -> dict[str, Any]:
    """Export multiple contacts as a single .vcf file (batch).

    Params:
        contact_ids: list of int — Contact PKs
        OR
        filter: dict — query filter (e.g. {"company": "Acme"})
    """
    from apps.core.models import Contact

    contact_ids = params.get('contact_ids', [])
    if contact_ids:
        contacts = Contact.objects.filter(pk__in=contact_ids, is_active=True)
    elif params.get('filter'):
        contacts = Contact.objects.filter(is_active=True, **params['filter'])[:500]
    else:
        return {'error': 'contact_ids or filter required'}

    vcards = [_contact_to_vcard(c) for c in contacts]
    return {
        'vcard': '\r\n'.join(vcards),
        'count': len(vcards),
        'filename': f'contacts-{len(vcards)}.vcf',
    }


# ── Collision Check (for Contact Loader standalone page) ──────────────────

# ── Bundle Import (merge or create per row) ───────────────────────────────

