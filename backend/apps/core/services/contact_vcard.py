"""
vCard service — import, export, and collision check for contacts.

Handles Google Contacts, Apple Contacts, Dot, Popl, HiHello — anything
that exports vCard (.vcf).  One parser, all sources.
Supports batch: a .vcf file may contain hundreds of vCards.

Usage via manage actions:
    export_vcard       — single contact/org → .vcf text
    export_vcards      — batch contacts → .vcf text
    preview_vcard      — parse vCards + check for existing matches
    import_vcard       — batch create Contacts + optional Customer orgs
    check_collisions   — Contact Loader calls this to check batch against DB
    import_bundle      — import cleaned bundle.json (merge or create per row)
"""
from __future__ import annotations

import logging
from typing import Any

from django.db import transaction

logger = logging.getLogger('webclerk3')


def _detect_source(vcard_text: str) -> str:
    """Guess the source app from vCard metadata."""
    text = vcard_text.lower()
    if 'google' in text:
        return 'Google Contacts'
    if 'apple' in text:
        return 'Apple Contacts'
    if 'dot.cards' in text or 'x-socialprofile' in text:
        return 'Contact Share'
    return 'vCard Import'


def _parse_one(vcard) -> dict[str, Any]:
    """Extract WC3 fields from a single parsed vobject vCard."""
    result: dict[str, Any] = {}

    # Name
    if hasattr(vcard, 'n'):
        n = vcard.n.value
        result['name_first'] = n.given or ''
        result['name_last'] = n.family or ''
    elif hasattr(vcard, 'fn'):
        parts = vcard.fn.value.split(None, 1)
        result['name_first'] = parts[0] if parts else ''
        result['name_last'] = parts[1] if len(parts) > 1 else ''

    if hasattr(vcard, 'fn'):
        result['full_name'] = vcard.fn.value

    # Organization
    if hasattr(vcard, 'org'):
        result['company'] = vcard.org.value[0] if vcard.org.value else ''

    # Title
    if hasattr(vcard, 'title'):
        result['title'] = vcard.title.value

    # Email (first one)
    emails = vcard.contents.get('email', [])
    if emails:
        result['email'] = emails[0].value

    # Phone (first one)
    phones = vcard.contents.get('tel', [])
    if phones:
        result['phone'] = phones[0].value
        result['phone_type'] = (phones[0].params.get('TYPE', ['work'])[0]
                                if phones[0].params else 'work')

    # Address (first one)
    addrs = vcard.contents.get('adr', [])
    if addrs:
        a = addrs[0].value
        result['address'] = {
            'address1': a.street or '',
            'city': a.city or '',
            'state': a.region or '',
            'zip': a.code or '',
            'country': a.country or '',
        }

    return result


def preview_vcard(params: dict) -> dict[str, Any]:
    """Parse all vCards in the text and return preview data with matches.

    Params:
        vcard_text: raw vCard string (may contain multiple BEGIN:VCARD blocks)

    Returns:
        contacts: list of preview dicts, each with fields + match info
        source_name: detected source app
        total: count of vCards found
    """
    vcard_text = params.get('vcard_text', '')
    if not vcard_text.strip():
        return {'error': 'No vCard text provided'}

    try:
        import vobject
    except ImportError:
        return {'error': 'vobject library not installed'}

    source_name = _detect_source(vcard_text)

    # Parse all vCards in the file
    contacts = []
    try:
        for vcard in vobject.readComponents(vcard_text):
            fields = _parse_one(vcard)
            if not fields.get('name_first') and not fields.get('name_last') and not fields.get('email'):
                continue  # skip empty entries
            fields['source_name'] = source_name
            contacts.append(fields)
    except Exception as e:
        return {'error': f'Parse failed: {e}'}

    if not contacts:
        return {'error': 'No valid contacts found in vCard data'}

    # Batch check for existing emails and companies
    from apps.core.models import Contact
    from apps.orgs.models import OrgBase

    all_emails = [c['email'].lower() for c in contacts if c.get('email')]
    existing_emails = set(
        Contact.objects.filter(
            email__in=all_emails, is_active=True, is_deleted=False
        ).values_list('email', flat=True)
    ) if all_emails else set()

    all_orgs = list({c['company'] for c in contacts if c.get('company')})
    existing_orgs = {}
    if all_orgs:
        for org in OrgBase.objects.filter(
            display_name__in=all_orgs, is_active=True, is_deleted=False
        ).values('id', 'display_name', 'status', 'org_type'):
            existing_orgs[org['display_name'].lower()] = org

    # Annotate each contact with match status
    for c in contacts:
        email = (c.get('email') or '').lower()
        c['duplicate'] = email in existing_emails if email else False

        company = c.get('company', '')
        org_match = existing_orgs.get(company.lower()) if company else None
        c['org_match'] = org_match  # None or {id, display_name, ...}

    return {
        'contacts': contacts,
        'source_name': source_name,
        'total': len(contacts),
        'duplicates': sum(1 for c in contacts if c.get('duplicate')),
        'new_orgs': len([c for c in contacts
                         if c.get('company') and not c.get('org_match')
                         and not c.get('duplicate')]),
    }


@transaction.atomic
def import_vcard(params: dict) -> dict[str, Any]:
    """Batch create Contacts + Customer orgs from previewed vCard data.

    Params:
        contacts: list of contact field dicts (from preview)
        skip_duplicates: bool (default True) — skip contacts with existing email
        create_orgs: bool (default True) — create new Customer for unmatched companies
        source_name: attribution string
    """
    from apps.core.models import Contact
    from apps.orgs.models import OrgBase

    contact_list = params.get('contacts', [])
    # Single-contact legacy format
    if not contact_list and params.get('contact_fields'):
        contact_list = [params['contact_fields']]
        if params.get('phone'):
            contact_list[0]['phone'] = params['phone'].get('number', '')
            contact_list[0]['phone_type'] = params['phone'].get('type', 'work')
        if params.get('address'):
            contact_list[0]['address'] = params['address']
        if params.get('create_org'):
            contact_list[0]['company'] = params['create_org'].get('display_name', '')
        if params.get('org_id'):
            contact_list[0]['_org_id'] = params['org_id']

    skip_duplicates = params.get('skip_duplicates', True)
    create_orgs = params.get('create_orgs', True)
    source_name = params.get('source_name', 'vCard Import')

    # Pre-fetch existing emails for duplicate check
    all_emails = [c.get('email', '').lower() for c in contact_list if c.get('email')]
    existing_emails = set(
        Contact.objects.filter(
            email__in=all_emails, is_active=True, is_deleted=False
        ).values_list('email', flat=True)
    ) if all_emails else set()

    # Org cache: reuse orgs created during this batch
    org_cache: dict[str, OrgBase] = {}
    # Pre-fetch existing orgs
    all_companies = list({c.get('company', '') for c in contact_list if c.get('company')})
    if all_companies:
        for org in OrgBase.objects.filter(
            display_name__in=all_companies, is_active=True, is_deleted=False
        ):
            org_cache[org.display_name.lower()] = org

    created = 0
    skipped = 0
    orgs_created = 0
    results = []

    for cf in contact_list:
        email = (cf.get('email') or '').lower()

        # Skip duplicates
        if skip_duplicates and email and email in existing_emails:
            skipped += 1
            continue

        # Create contact
        contact = Contact(
            name_first=cf.get('name_first', ''),
            name_last=cf.get('name_last', ''),
            email=cf.get('email') or None,
            company=cf.get('company', ''),
            title=cf.get('title', ''),
            source_name=cf.get('source_name', source_name),
            role='user',
        )
        contact.save()

        # Phone
        phone_num = cf.get('phone', '')
        if phone_num:
            try:
                from apps.core.models import Phone
                ph = Phone.objects.create(
                    contact=contact,
                    number=phone_num,
                    name=cf.get('phone_type', 'work'),
                )
                contact.phone_id = ph.pk
                contact.save(update_fields=['phone_id'])
            except Exception as e:
                logger.warning(f"[VCARD] Phone create failed: {e}")

        # Address
        addr_data = cf.get('address')
        if addr_data and isinstance(addr_data, dict) and any(addr_data.values()):
            try:
                from apps.core.models import Address
                addr = Address.objects.create(
                    contact=contact,
                    address1=addr_data.get('address1', ''),
                    city=addr_data.get('city', ''),
                    state=addr_data.get('state', ''),
                    zip=addr_data.get('zip', ''),
                    country=addr_data.get('country', ''),
                )
                contact.address_id = addr.pk
                contact.save(update_fields=['address_id'])
            except Exception as e:
                logger.warning(f"[VCARD] Address create failed: {e}")

        # Org — link existing or create new
        org = None
        explicit_org_id = cf.get('_org_id')
        company = cf.get('company', '')

        if explicit_org_id:
            try:
                org = OrgBase.objects.get(pk=int(explicit_org_id), is_active=True)
            except OrgBase.DoesNotExist:
                pass
        elif company:
            org = org_cache.get(company.lower())
            if not org and create_orgs:
                org = OrgBase(
                    display_name=company,
                    org_type='customer',
                    status='active',
                    contact_id=contact.pk,
                )
                if contact.email:
                    org.email = contact.email
                org.save()
                org_cache[company.lower()] = org
                orgs_created += 1

        if org:
            if org.org_type == 'customer':
                contact.customer_id = org.pk
            elif org.org_type == 'vendor':
                contact.vendor_id = org.pk
            contact.save(update_fields=['customer_id', 'vendor_id'])

        if email:
            existing_emails.add(email)  # prevent duplicates within batch

        created += 1
        results.append({
            'contact_id': contact.pk,
            'contact_ida': contact.ida,
            'name': str(contact),
            'org': org.display_name if org else None,
        })

    return {
        'created': created,
        'skipped': skipped,
        'orgs_created': orgs_created,
        'total': len(contact_list),
        'results': results[:50],  # cap response size
        'message': f"Created {created} contacts, {orgs_created} orgs. Skipped {skipped} duplicates.",
    }


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
        contacts = Contact.objects.filter(is_active=True, is_deleted=False, **params['filter'])[:500]
    else:
        return {'error': 'contact_ids or filter required'}

    vcards = [_contact_to_vcard(c) for c in contacts]
    return {
        'vcard': '\r\n'.join(vcards),
        'count': len(vcards),
        'filename': f'contacts-{len(vcards)}.vcf',
    }


# ── Collision Check (for Contact Loader standalone page) ──────────────────

def check_collisions(params: dict) -> dict[str, Any]:
    """Check a batch of parsed contacts against existing WC3 data.

    Called by the standalone Contact Loader page via API.
    Returns match info for each contact so the user can decide merge vs create.

    Params:
        contacts: list of {email, name_first, name_last, company, phone}
    """
    from apps.core.models import Contact
    from apps.orgs.models import OrgBase

    contact_list = params.get('contacts', [])
    if not contact_list:
        return {'error': 'No contacts provided'}

    # Batch lookup emails
    all_emails = [c.get('email', '').lower() for c in contact_list if c.get('email')]
    email_matches = {}
    if all_emails:
        for c in Contact.objects.filter(
            email__in=all_emails, is_active=True, is_deleted=False
        ).values('id', 'ida', 'email', 'name_first', 'name_last', 'company'):
            email_matches[c['email'].lower()] = c

    # Batch lookup companies
    all_companies = list({c.get('company', '').lower() for c in contact_list if c.get('company')})
    org_matches = {}
    if all_companies:
        for org in OrgBase.objects.filter(
            display_name__iexact__in=all_companies, is_active=True, is_deleted=False
        ).values('id', 'display_name', 'status', 'org_type', 'ida'):
            org_matches[org['display_name'].lower()] = org

    # If iexact__in doesn't work, fall back to case-insensitive loop
    if not org_matches and all_companies:
        from django.db.models import Q
        q = Q()
        for comp in all_companies:
            q |= Q(display_name__iexact=comp)
        for org in OrgBase.objects.filter(
            q, is_active=True, is_deleted=False
        ).values('id', 'display_name', 'status', 'org_type', 'ida'):
            org_matches[org['display_name'].lower()] = org

    # Annotate each contact
    results = []
    for c in contact_list:
        email = (c.get('email') or '').lower()
        company = (c.get('company') or '').lower()

        match = {
            'email_match': email_matches.get(email),  # existing contact or None
            'org_match': org_matches.get(company),     # existing org or None
            'action': 'create',  # default suggestion
        }

        if match['email_match']:
            match['action'] = 'merge'  # suggest merge if email exists

        results.append(match)

    return {
        'results': results,
        'total': len(results),
        'merges': sum(1 for r in results if r['action'] == 'merge'),
        'creates': sum(1 for r in results if r['action'] == 'create'),
    }


# ── Bundle Import (merge or create per row) ───────────────────────────────

@transaction.atomic
def import_bundle(params: dict) -> dict[str, Any]:
    """Import a cleaned bundle.json — each row specifies merge or create.

    Params:
        contacts: list of dicts, each with:
            action: "create" | "merge" | "skip"
            target_id: int (for merge — existing Contact PK)
            name_first, name_last, email, company, title, phone, address, source_name
        create_orgs: bool (default True)
    """
    from apps.core.models import Contact
    from apps.orgs.models import OrgBase

    contact_list = params.get('contacts', [])
    create_orgs = params.get('create_orgs', True)
    source_name = params.get('source_name', 'vCard Import')

    org_cache: dict[str, OrgBase] = {}
    all_companies = list({c.get('company', '') for c in contact_list if c.get('company')})
    if all_companies:
        for org in OrgBase.objects.filter(display_name__in=all_companies, is_active=True, is_deleted=False):
            org_cache[org.display_name.lower()] = org

    created = 0
    merged = 0
    skipped = 0

    for cf in contact_list:
        action = cf.get('action', 'create')

        if action == 'skip':
            skipped += 1
            continue

        if action == 'merge' and cf.get('target_id'):
            # Merge: update existing contact with non-empty fields
            try:
                contact = Contact.objects.get(pk=int(cf['target_id']), is_active=True)
                for field in ('name_first', 'name_last', 'title', 'company', 'source_name'):
                    val = cf.get(field, '')
                    if val and not getattr(contact, field, ''):
                        setattr(contact, field, val)
                if cf.get('email') and not contact.email:
                    contact.email = cf['email']
                contact.save()
                merged += 1
                continue
            except Contact.DoesNotExist:
                pass  # fall through to create

        # Create new contact
        contact = Contact(
            name_first=cf.get('name_first', ''),
            name_last=cf.get('name_last', ''),
            email=cf.get('email') or None,
            company=cf.get('company', ''),
            title=cf.get('title', ''),
            source_name=cf.get('source_name', source_name),
            role='user',
        )
        contact.save()

        # Phone
        phone_num = cf.get('phone', '')
        if phone_num:
            try:
                from apps.core.models import Phone
                ph = Phone.objects.create(contact_id=contact.pk, number=phone_num, name='work')
                contact.phone_id = ph.pk
                contact.save(update_fields=['phone_id'])
            except Exception:
                pass

        # Address
        addr = cf.get('address')
        if addr and isinstance(addr, dict) and any(addr.values()):
            try:
                from apps.core.models import Address
                a = Address.objects.create(
                    contact_id=contact.pk,
                    address1=addr.get('address1', ''), city=addr.get('city', ''),
                    state=addr.get('state', ''), zip=addr.get('zip', ''),
                    country=addr.get('country', ''),
                )
                contact.address_id = a.pk
                contact.save(update_fields=['address_id'])
            except Exception:
                pass

        # Org
        company = cf.get('company', '')
        if company and create_orgs:
            org = org_cache.get(company.lower())
            if not org:
                org = OrgBase(
                    display_name=company, org_type='customer',
                    status='active', contact_id=contact.pk,
                )
                if contact.email:
                    org.email = contact.email
                org.save()
                org_cache[company.lower()] = org

            if org:
                contact.customer_id = org.pk
                contact.save(update_fields=['customer_id'])

        created += 1

    return {
        'created': created,
        'merged': merged,
        'skipped': skipped,
        'total': len(contact_list),
        'message': f"Created {created}, merged {merged}, skipped {skipped}.",
    }
