from __future__ import annotations

from typing import Any

from apps.core.models import Contact


def _ids_from_link_bucket(value: Any) -> set[int]:
    ids: set[int] = set()
    if isinstance(value, list):
        for item in value:
            if isinstance(item, int) and item > 0:
                ids.add(item)
                continue
            if isinstance(item, dict):
                raw = item.get("id")
                if isinstance(raw, int) and raw > 0:
                    ids.add(raw)
    elif isinstance(value, int) and value > 0:
        ids.add(value)
    return ids


def resolve_contact_ids_for_customer_org(org) -> set[int]:
    """Resolve linked contact IDs for a customer org from FK + refs data.

    Sources:
    - Contact.customer_id FK
    - OrgBase.contacts denormalized bucket
    - OrgBase.refs.links.contact
    - Contact.refs.links.customer reverse link
    """
    org_id = getattr(org, "pk", None)
    if not isinstance(org_id, int) or org_id <= 0:
        return set()

    contact_ids: set[int] = set(
        Contact.objects.filter(customer_id=org_id).values_list("id", flat=True)
    )

    contacts_bucket = getattr(org, "contacts", None)
    if isinstance(contacts_bucket, list):
        for item in contacts_bucket:
            if isinstance(item, dict):
                raw = item.get("id") or item.get("contact_id")
                if isinstance(raw, int) and raw > 0:
                    contact_ids.add(raw)

    refs = getattr(org, "refs", None)
    if isinstance(refs, dict):
        links = refs.get("links")
        if isinstance(links, dict):
            contact_ids.update(_ids_from_link_bucket(links.get("contact")))

    for contact in Contact.objects.filter(is_deleted=False).only("id", "refs"):
        cref = contact.refs if isinstance(contact.refs, dict) else {}
        links = cref.get("links") if isinstance(cref, dict) else None
        if not isinstance(links, dict):
            continue
        customer_ids = _ids_from_link_bucket(links.get("customer"))
        if org_id in customer_ids:
            contact_ids.add(contact.id)

    return {cid for cid in contact_ids if isinstance(cid, int) and cid > 0}
