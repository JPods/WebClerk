from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Set

from common.models import LINK_DENORMALIZE_FIELDS


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _normalize_comm_entry(item: Any, *, value_keys: Sequence[str]) -> Any:
    if not isinstance(item, dict):
        return item
    if "value" not in item or item.get("value") in (None, ""):
        for key in value_keys:
            val = item.get(key)
            if val not in (None, ""):
                item["value"] = val
                break
    return item


def _normalize_address_entry(item: Any) -> Any:
    if not isinstance(item, dict):
        return item
    if not item.get("full"):
        parts = [
            item.get("address1"),
            item.get("address2"),
            item.get("city"),
            item.get("state"),
            item.get("zip"),
            item.get("country"),
        ]
        full = "\n".join([p for p in parts if isinstance(p, str) and p.strip()])
        if full:
            item["full"] = full
    return item


def _normalize_comm_list(items: Any, *, kind: str) -> Any:
    entries = _as_list(items)
    normalized: List[Any] = []
    for item in entries:
        if kind == "email":
            normalized.append(_normalize_comm_entry(item, value_keys=("value", "email", "address")))
        elif kind == "phone":
            normalized.append(_normalize_comm_entry(item, value_keys=("value", "number", "format")))
        elif kind == "domain":
            normalized.append(_normalize_comm_entry(item, value_keys=("value", "path", "domain")))
        elif kind == "address":
            normalized.append(_normalize_address_entry(item))
        else:
            normalized.append(item)
    return normalized


def _extract_contact_id(entry: Any) -> Optional[int]:
    if isinstance(entry, dict):
        contact = entry.get("contact")
        if isinstance(contact, dict):
            for key in ("id", "contact_id", "contactId"):
                cid = contact.get(key)
                if isinstance(cid, int):
                    return cid
                if isinstance(cid, str) and cid.isdigit():
                    return int(cid)
        for key in ("id", "contact_id", "contactId"):
            cid = entry.get(key)
            if isinstance(cid, int):
                return cid
            if isinstance(cid, str) and cid.isdigit():
                return int(cid)
    elif isinstance(entry, int):
        return entry
    elif isinstance(entry, str) and entry.isdigit():
        return int(entry)
    return None


def _extract_purpose(entry: Any) -> str:
    if isinstance(entry, dict):
        purpose = entry.get("purpose")
        if isinstance(purpose, str):
            return purpose
        contact = entry.get("contact")
        if isinstance(contact, dict):
            inner = contact.get("purpose")
            if isinstance(inner, str):
                return inner
    return ""


def _build_contact_payload(base: Dict[str, Any], *, contact_obj: Any = None) -> Dict[str, Any]:
    payload = dict(base or {})
    if "address" in payload:
        payload["address"] = _normalize_comm_list(payload.get("address"), kind="address")
    if "email" in payload:
        payload["email"] = _normalize_comm_list(payload.get("email"), kind="email")
    if "phone" in payload:
        payload["phone"] = _normalize_comm_list(payload.get("phone"), kind="phone")
    if "domain" in payload:
        payload["domain"] = _normalize_comm_list(payload.get("domain"), kind="domain")
    if contact_obj is not None:
        for field in LINK_DENORMALIZE_FIELDS.get("contact", []):
            if field not in payload:
                try:
                    payload[field] = getattr(contact_obj, field, None)
                except Exception:
                    pass
        if not payload.get("attention"):
            try:
                payload["attention"] = getattr(contact_obj, "attention", None) or contact_obj.get_full_name()
            except Exception:
                try:
                    payload["attention"] = getattr(contact_obj, "attention", None)
                except Exception:
                    pass

        try:
            refs = getattr(contact_obj, "refs", {}) or {}
        except Exception:
            refs = {}
        links = refs.get("links", {}) if isinstance(refs, dict) else {}
        if isinstance(links, dict):
            if not payload.get("address"):
                payload["address"] = _normalize_comm_list(links.get("location") or links.get("address") or [], kind="address")
            if not payload.get("email"):
                payload["email"] = _normalize_comm_list(links.get("email") or [], kind="email")
            if not payload.get("phone"):
                payload["phone"] = _normalize_comm_list(links.get("phone") or [], kind="phone")
            if not payload.get("domain"):
                payload["domain"] = _normalize_comm_list(links.get("domain") or [], kind="domain")
    return payload


def _normalize_contact_entries(entries: Any, *, contact_map: Optional[Dict[int, Any]] = None) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for entry in _as_list(entries):
        if isinstance(entry, dict):
            purpose = _extract_purpose(entry)
            contact_base = entry.get("contact") if isinstance(entry.get("contact"), dict) else {}
            if not isinstance(contact_base, dict):
                contact_base = {}
            for key in ("attention", "email", "phone", "domain", "address"):
                if key in entry and key not in contact_base:
                    contact_base[key] = entry.get(key)
            contact_id = _extract_contact_id(entry)
            if contact_id is not None and "id" not in contact_base:
                contact_base["id"] = contact_id
            contact_obj = contact_map.get(contact_id) if contact_map and contact_id is not None else None
            contact_payload = _build_contact_payload(contact_base, contact_obj=contact_obj)
            normalized.append({"purpose": purpose, "contact": contact_payload})
        else:
            contact_id = _extract_contact_id(entry)
            if contact_id is None:
                continue
            contact_obj = contact_map.get(contact_id) if contact_map else None
            contact_payload = _build_contact_payload({"id": contact_id}, contact_obj=contact_obj)
            normalized.append({"purpose": "", "contact": contact_payload})
    return normalized


def normalize_refs_for_save(refs: Any) -> Any:
    if not isinstance(refs, dict):
        return refs

    links = refs.get("links")
    if not isinstance(links, dict):
        links = {}
        refs["links"] = links

    contacts_in = links.get("contact")
    if not isinstance(contacts_in, list):
        return refs

    normalized = _normalize_contact_entries(contacts_in)
    links["contact"] = normalized

    existing_links = links.get("contact") or []
    existing_map: Dict[int, Dict[str, Any]] = {}
    for item in _as_list(existing_links):
        if isinstance(item, dict):
            cid = _extract_contact_id(item)
            if cid is not None:
                existing_map[cid] = dict(item)
        else:
            cid = _extract_contact_id(item)
            if cid is not None:
                existing_map[cid] = {"id": cid}

    for entry in normalized:
        contact_payload = entry.get("contact") or {}
        cid = _extract_contact_id(contact_payload)
        if cid is None:
            continue
        base = existing_map.get(cid, {"id": cid})
        purpose = entry.get("purpose")
        if purpose:
            base["purpose"] = purpose
        attention = contact_payload.get("attention")
        if attention and "attention" not in base:
            base["attention"] = attention
        existing_map[cid] = base

    links["contact"] = list(existing_map.values())
    return refs


def normalize_refs_for_response(refs: Any) -> Any:
    if not isinstance(refs, dict):
        return refs

    links = refs.get("links")
    if not isinstance(links, dict):
        links = {}
        refs["links"] = links

    contacts_in = links.get("contact")
    if not isinstance(contacts_in, list):
        return refs

    contact_ids: Set[int] = set()
    for entry in _as_list(contacts_in):
        cid = _extract_contact_id(entry)
        if cid is not None:
            contact_ids.add(cid)

    contact_map: Dict[int, Any] = {}
    if contact_ids:
        try:
            from apps.core.models import Contact

            qs = Contact.objects.filter(pk__in=contact_ids)
            contact_map = {c.pk: c for c in qs}
        except Exception:
            contact_map = {}

    normalized = _normalize_contact_entries(contacts_in, contact_map=contact_map)

    links["contact"] = normalized
    return refs
