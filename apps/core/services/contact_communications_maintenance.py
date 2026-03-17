from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from django.db.models import Count, Q
from django.utils import timezone

from apps.communications.models import Address, Domain, Email, Phone
from apps.core.models import Contact

logger = logging.getLogger(__name__)


@dataclass
class ContactCommMaintenanceSummary:
    processed_contacts: int = 0
    updated_contacts: int = 0
    created_records: int = 0
    claimed_unowned: int = 0
    reassigned_owned: int = 0
    comm_refs_updated: int = 0
    skipped_owned_elsewhere: int = 0
    errors: int = 0
    # Dangling comm records (no contact FK at all)
    dangling_found: int = 0
    dangling_claimed: int = 0
    dangling_unlinked: int = 0
    # Alice notes emitted
    alice_notes_created: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "processed_contacts": self.processed_contacts,
            "updated_contacts": self.updated_contacts,
            "created_records": self.created_records,
            "claimed_unowned": self.claimed_unowned,
            "reassigned_owned": self.reassigned_owned,
            "comm_refs_updated": self.comm_refs_updated,
            "skipped_owned_elsewhere": self.skipped_owned_elsewhere,
            "errors": self.errors,
            "dangling_found": self.dangling_found,
            "dangling_claimed": self.dangling_claimed,
            "dangling_unlinked": self.dangling_unlinked,
            "alice_notes_created": self.alice_notes_created,
        }


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _norm_email(value: Any) -> str:
    return _norm(value).lower()


def _norm_phone(value: Any) -> str:
    raw = _norm(value)
    return "".join(ch for ch in raw if ch.isdigit() or ch == "+")


def _norm_domain(value: Any) -> str:
    return _norm(value).lower()


def _read_bucket_ids(value: Any) -> set[int]:
    out: set[int] = set()
    if isinstance(value, list):
        for item in value:
            if isinstance(item, int) and item > 0:
                out.add(item)
            elif isinstance(item, dict):
                raw = item.get("id")
                if isinstance(raw, int) and raw > 0:
                    out.add(raw)
    elif isinstance(value, int) and value > 0:
        out.add(value)
    return out


def _contact_link_snapshot(contact: Contact) -> dict[str, Any]:
    return {
        "id": contact.id,
        "name_first": contact.name_first or "",
        "name_last": contact.name_last or "",
        "display_name": contact.get_full_name() if hasattr(contact, "get_full_name") else (contact.attention or ""),
        "email": contact.email or "",
        "phone": contact.phone or "",
        "attention": contact.attention or "",
        "company": contact.company or "",
    }


def _comm_keywords(comm_obj: Any, contact: Contact) -> list[str]:
    values: list[str] = []

    # Contact-derived search tokens (requested: include first/last names)
    values.extend([
        contact.name_first or "",
        contact.name_last or "",
        contact.attention or "",
        contact.email or "",
        contact.phone or "",
        contact.company or "",
    ])

    # Communication row-derived tokens
    if isinstance(comm_obj, Email):
        values.extend([comm_obj.email or "", comm_obj.name or "", comm_obj.type or ""])
    elif isinstance(comm_obj, Phone):
        values.extend([comm_obj.number or "", comm_obj.name or "", comm_obj.format or "", comm_obj.country_code or ""])
    elif isinstance(comm_obj, Domain):
        values.extend([comm_obj.path or "", comm_obj.type or "", comm_obj.status or ""])
    elif isinstance(comm_obj, Address):
        values.extend([
            comm_obj.full or "",
            comm_obj.address1 or "",
            comm_obj.city or "",
            comm_obj.state or "",
            comm_obj.zip or "",
            comm_obj.country or "",
        ])

    # Keep existing keywords too, but normalize to lowercase and dedupe.
    refs = comm_obj.refs if isinstance(comm_obj.refs, dict) else {}
    existing = refs.get("keywords") if isinstance(refs.get("keywords"), list) else []
    values.extend([str(v) for v in existing if isinstance(v, str)])

    normalized = sorted({v.strip().lower() for v in values if isinstance(v, str) and v.strip()})
    return normalized


def _ensure_comm_contact_ref(comm_obj, contact: Contact, dry_run: bool) -> bool:
    refs = comm_obj.refs if isinstance(comm_obj.refs, dict) else {}
    links = refs.get("links") if isinstance(refs.get("links"), dict) else {}
    previous_bucket = links.get("contact") if isinstance(links.get("contact"), list) else []

    # FK owner is authoritative. Keep one canonical contact snapshot only.
    snapshot = _contact_link_snapshot(contact)
    canonical_bucket: list[dict[str, Any]] = [snapshot]
    links["contact"] = canonical_bucket
    refs["links"] = links

    changed = previous_bucket != canonical_bucket

    new_keywords = _comm_keywords(comm_obj, contact)
    old_keywords = refs.get("keywords") if isinstance(refs.get("keywords"), list) else []
    if old_keywords != new_keywords:
        refs["keywords"] = new_keywords
        changed = True

    if not changed:
        return False

    if not dry_run:
        now_ms = int(timezone.now().timestamp() * 1000)
        type(comm_obj).objects.filter(pk=comm_obj.pk).update(refs=refs, dt_modified=now_ms)

    return True


def _assign_contact_fk(comm_obj, contact_id: int, dry_run: bool) -> None:
    if dry_run:
        return
    now_ms = int(timezone.now().timestamp() * 1000)
    type(comm_obj).objects.filter(pk=comm_obj.pk).update(contact_id=contact_id, dt_modified=now_ms)


def _resolve_email(contact: Contact, summary: ContactCommMaintenanceSummary, dry_run: bool, allow_reassign_owned: bool):
    value = _norm_email(contact.email)
    if not value:
        return

    own = Email.objects.filter(contact_id=contact.id, email__iexact=value).order_by("-id").first()
    if own:
        return

    unowned = Email.objects.filter(contact__isnull=True, email__iexact=value).order_by("-id").first()
    if unowned:
        _assign_contact_fk(unowned, contact.id, dry_run=dry_run)
        summary.claimed_unowned += 1
        return

    owned_other = Email.objects.filter(email__iexact=value).exclude(contact_id=contact.id).order_by("-id").first()
    if owned_other:
        if allow_reassign_owned:
            _assign_contact_fk(owned_other, contact.id, dry_run=dry_run)
            summary.reassigned_owned += 1
        else:
            summary.skipped_owned_elsewhere += 1
        return

    if not dry_run:
        Email.objects.create(
            contact_id=contact.id,
            email=value,
            name="account",
            is_primary=True,
            is_verified=False,
        )
    summary.created_records += 1


def _resolve_phone(contact: Contact, summary: ContactCommMaintenanceSummary, dry_run: bool, allow_reassign_owned: bool):
    value = _norm_phone(contact.phone)
    if not value:
        return

    own = Phone.objects.filter(contact_id=contact.id).order_by("-id")
    for row in own:
        if _norm_phone(row.number) == value:
            return

    unowned = Phone.objects.filter(contact__isnull=True).order_by("-id")
    for row in unowned:
        if _norm_phone(row.number) == value:
            _assign_contact_fk(row, contact.id, dry_run=dry_run)
            summary.claimed_unowned += 1
            return

    owned_other = Phone.objects.exclude(contact_id=contact.id).order_by("-id")
    for row in owned_other:
        if _norm_phone(row.number) == value:
            if allow_reassign_owned:
                _assign_contact_fk(row, contact.id, dry_run=dry_run)
                summary.reassigned_owned += 1
            else:
                summary.skipped_owned_elsewhere += 1
            return

    if not dry_run:
        Phone.objects.create(contact_id=contact.id, number=value, name="primary")
    summary.created_records += 1


def _resolve_domain(contact: Contact, summary: ContactCommMaintenanceSummary, dry_run: bool, allow_reassign_owned: bool):
    value = _norm_domain(contact.domain)
    if not value:
        return

    own = Domain.objects.filter(contact_id=contact.id, path__iexact=value).order_by("-id").first()
    if own:
        return

    unowned = Domain.objects.filter(contact__isnull=True, path__iexact=value).order_by("-id").first()
    if unowned:
        _assign_contact_fk(unowned, contact.id, dry_run=dry_run)
        summary.claimed_unowned += 1
        return

    owned_other = Domain.objects.filter(path__iexact=value).exclude(contact_id=contact.id).order_by("-id").first()
    if owned_other:
        if allow_reassign_owned:
            _assign_contact_fk(owned_other, contact.id, dry_run=dry_run)
            summary.reassigned_owned += 1
        else:
            summary.skipped_owned_elsewhere += 1
        return

    if not dry_run:
        Domain.objects.create(contact_id=contact.id, path=value, type="website", status="active")
    summary.created_records += 1


def _resolve_address(contact: Contact, summary: ContactCommMaintenanceSummary, dry_run: bool, allow_reassign_owned: bool):
    value = _norm(contact.address_full)
    if not value:
        return

    own = Address.objects.filter(contact_id=contact.id).filter(Q(full__iexact=value) | Q(address1__iexact=value)).order_by("-id").first()
    if own:
        return

    unowned = Address.objects.filter(contact__isnull=True).filter(Q(full__iexact=value) | Q(address1__iexact=value)).order_by("-id").first()
    if unowned:
        _assign_contact_fk(unowned, contact.id, dry_run=dry_run)
        summary.claimed_unowned += 1
        return

    owned_other = Address.objects.filter(Q(full__iexact=value) | Q(address1__iexact=value)).exclude(contact_id=contact.id).order_by("-id").first()
    if owned_other:
        if allow_reassign_owned:
            _assign_contact_fk(owned_other, contact.id, dry_run=dry_run)
            summary.reassigned_owned += 1
        else:
            summary.skipped_owned_elsewhere += 1
        return

    if not dry_run:
        Address.objects.create(contact_id=contact.id, full=value, address1=value)
    summary.created_records += 1


def _claim_rows_from_contact_refs(contact: Contact, summary: ContactCommMaintenanceSummary, dry_run: bool, allow_reassign_owned: bool):
    refs = contact.refs if isinstance(contact.refs, dict) else {}
    links = refs.get("links") if isinstance(refs.get("links"), dict) else {}

    for model_cls, key in ((Email, "email"), (Phone, "phone"), (Domain, "domain"), (Address, "address")):
        ids = _read_bucket_ids(links.get(key))
        if not ids:
            continue
        for row in model_cls.objects.filter(id__in=ids):
            if row.contact_id == contact.id:
                continue
            if row.contact_id in (None, 0):
                _assign_contact_fk(row, contact.id, dry_run=dry_run)
                summary.claimed_unowned += 1
            elif allow_reassign_owned:
                _assign_contact_fk(row, contact.id, dry_run=dry_run)
                summary.reassigned_owned += 1
            else:
                summary.skipped_owned_elsewhere += 1


# ── Alice helpers ────────────────────────────────────────────────────

def _alice_note(
    category: str,
    role: str,
    name: str,
    parent_model: str | None = None,
    details: dict | None = None,
) -> bool:
    """Emit one Alice note; swallow all exceptions so maintenance is never blocked."""
    try:
        from apps.ai_assistant.services.alice_notes import create_note  # noqa: PLC0415
        create_note(category, role=role, name=name, parent_model=parent_model, details=details)
        return True
    except Exception as exc:  # pragma: no cover
        logger.warning("alice_note failed: %s", exc)
        return False


def _emit_alice_run_summary(summary: ContactCommMaintenanceSummary, dry_run: bool) -> int:
    """Emit a single alice_log[system] note summarising the maintenance run.
    Returns 1 if note created, 0 otherwise."""
    emitted = _alice_note(
        "log",
        role="system",
        name="contact_communications_maintenance run",
        parent_model="contact",
        details={
            "dry_run": dry_run,
            **summary.as_dict(),
        },
    )
    return 1 if emitted else 0


def _emit_alice_dangling_unlinked(orphans: dict[str, list[int]]) -> int:
    """Emit an alice_pending[data_quality] note when comm records can't be matched."""
    total = sum(len(v) for v in orphans.values())
    if not total:
        return 0
    emitted = _alice_note(
        "pending",
        role="data_quality",
        name=f"{total} communication record(s) cannot be linked to any contact",
        parent_model="contact",
        details={"orphan_ids_by_type": orphans, "total": total},
    )
    return 1 if emitted else 0


def _emit_alice_maintenance_errors(count: int) -> int:
    """Emit an alice_pending[action_required] note when maintenance raises exceptions."""
    if not count:
        return 0
    emitted = _alice_note(
        "pending",
        role="action_required",
        name=f"{count} error(s) during contact_communications_maintenance",
        parent_model="contact",
        details={"error_count": count},
    )
    return 1 if emitted else 0


def _check_duplicate_comm_values(emit_alice: bool, summary: ContactCommMaintenanceSummary) -> None:
    """Detect comm values shared across multiple contacts and flag to Alice."""
    checks: list[tuple[Any, str, str, str]] = [
        (Email, "email", "email", "email"),
        (Domain, "path", "domain", "domain"),
    ]
    for model_cls, value_field, bucket_name, model_name in checks:
        dupes = (
            model_cls.objects
            .filter(contact__isnull=False)
            .values(value_field)
            .annotate(cnt=Count("id"))
            .filter(cnt__gt=1)
            .order_by("-cnt")[:10]
        )
        for row in dupes:
            if emit_alice:
                val = row[value_field]
                emitted = _alice_note(
                    "pending",
                    role="data_quality",
                    name=f"Duplicate {bucket_name} value assigned to multiple contacts: {val}",
                    parent_model="contact",
                    details={
                        "comm_type": bucket_name,
                        "value": val,
                        "linked_count": row["cnt"],
                        "pattern": "duplicate_comm_value",
                    },
                )
                if emitted:
                    summary.alice_notes_created += 1

    # Phone duplicates require normalisation, so compare by exact number field
    phone_dupes = (
        Phone.objects
        .filter(contact__isnull=False)
        .values("number")
        .annotate(cnt=Count("id"))
        .filter(cnt__gt=1)
        .order_by("-cnt")[:10]
    )
    for row in phone_dupes:
        if emit_alice:
            emitted = _alice_note(
                "pending",
                role="data_quality",
                name=f"Duplicate phone value assigned to multiple contacts: {row['number']}",
                parent_model="contact",
                details={
                    "comm_type": "phone",
                    "value": row["number"],
                    "linked_count": row["cnt"],
                    "pattern": "duplicate_comm_value",
                },
            )
            if emitted:
                summary.alice_notes_created += 1


# ── Dangling communication repair ────────────────────────────────────

def _link_dangling_to_contact(
    comm_obj: Any,
    contact: Contact,
    dry_run: bool,
) -> None:
    now_ms = int(timezone.now().timestamp() * 1000)
    if not dry_run:
        type(comm_obj).objects.filter(pk=comm_obj.pk).update(
            contact_id=contact.id,
            dt_modified=now_ms,
        )
        _ensure_comm_contact_ref(comm_obj, contact, dry_run=False)


def repair_dangling_communications(
    *,
    summary: ContactCommMaintenanceSummary,
    dry_run: bool = False,
    emit_alice: bool = True,
) -> None:
    """Find Email/Phone/Domain/Address rows with no contact FK and attempt to match
    them to a Contact by value.  Unmatched rows are reported as Alice data_quality
    pending notes so they can be reviewed and resolved manually.
    """
    orphans: dict[str, list[int]] = {
        "email": [],
        "phone": [],
        "domain": [],
        "address": [],
    }

    # ─ Email ─
    for row in Email.objects.filter(contact__isnull=True):
        summary.dangling_found += 1
        norm = _norm_email(row.email)
        if not norm:
            orphans["email"].append(row.id)
            summary.dangling_unlinked += 1
            continue
        contacts = list(
            Contact.objects.filter(email__iexact=norm, is_deleted=False)
            .order_by("id")[:2]
        )
        if len(contacts) == 1:
            _link_dangling_to_contact(row, contacts[0], dry_run)
            summary.dangling_claimed += 1
        else:
            orphans["email"].append(row.id)
            summary.dangling_unlinked += 1

    # ─ Phone ─
    for row in Phone.objects.filter(contact__isnull=True):
        summary.dangling_found += 1
        norm = _norm_phone(row.number)
        if not norm:
            orphans["phone"].append(row.id)
            summary.dangling_unlinked += 1
            continue
        matched: Contact | None = None
        for contact in Contact.objects.filter(is_deleted=False).iterator(chunk_size=200):
            if _norm_phone(contact.phone) == norm:
                if matched is None:
                    matched = contact
                else:
                    matched = None  # ambiguous — two contacts, skip
                    break
        if matched:
            _link_dangling_to_contact(row, matched, dry_run)
            summary.dangling_claimed += 1
        else:
            orphans["phone"].append(row.id)
            summary.dangling_unlinked += 1

    # ─ Domain ─
    for row in Domain.objects.filter(contact__isnull=True):
        summary.dangling_found += 1
        norm = _norm_domain(row.path)
        if not norm:
            orphans["domain"].append(row.id)
            summary.dangling_unlinked += 1
            continue
        contacts = list(
            Contact.objects.filter(domain__iexact=norm, is_deleted=False)
            .order_by("id")[:2]
        )
        if len(contacts) == 1:
            _link_dangling_to_contact(row, contacts[0], dry_run)
            summary.dangling_claimed += 1
        else:
            orphans["domain"].append(row.id)
            summary.dangling_unlinked += 1

    # ─ Address ─
    for row in Address.objects.filter(contact__isnull=True):
        summary.dangling_found += 1
        norm = _norm(row.full) or _norm(row.address1)
        if not norm:
            orphans["address"].append(row.id)
            summary.dangling_unlinked += 1
            continue
        contacts = list(
            Contact.objects.filter(
                Q(address_full__iexact=norm),
                is_deleted=False,
            )
            .order_by("id")[:2]
        )
        if len(contacts) == 1:
            _link_dangling_to_contact(row, contacts[0], dry_run)
            summary.dangling_claimed += 1
        else:
            orphans["address"].append(row.id)
            summary.dangling_unlinked += 1

    # ─ Report unlinked orphans to Alice ─
    if emit_alice and summary.dangling_unlinked:
        if _emit_alice_dangling_unlinked(orphans):
            summary.alice_notes_created += 1


def maintain_contact_communications(
    *,
    contact_id: int | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    allow_reassign_owned: bool = False,
    repair_dangling: bool = True,
    emit_alice: bool = True,
) -> dict[str, int]:
    """Repair/create contact communication links across FK and refs in both directions."""
    summary = ContactCommMaintenanceSummary()

    qs = Contact.objects.filter(is_deleted=False).order_by("id")
    if contact_id:
        qs = qs.filter(pk=contact_id)

    if limit and limit > 0:
        qs = qs[:limit]

    for contact in qs.iterator():
        summary.processed_contacts += 1
        try:
            before = {
                "email_id": contact.email_id,
                "phone_id": contact.phone_id,
                "domain_id": contact.domain_id,
                "address_id": contact.address_id,
            }

            _resolve_email(contact, summary, dry_run=dry_run, allow_reassign_owned=allow_reassign_owned)
            _resolve_phone(contact, summary, dry_run=dry_run, allow_reassign_owned=allow_reassign_owned)
            _resolve_domain(contact, summary, dry_run=dry_run, allow_reassign_owned=allow_reassign_owned)
            _resolve_address(contact, summary, dry_run=dry_run, allow_reassign_owned=allow_reassign_owned)
            _claim_rows_from_contact_refs(contact, summary, dry_run=dry_run, allow_reassign_owned=allow_reassign_owned)

            if not dry_run:
                # Rebuild contact refs.links buckets and primary *_id scalar links from FK-owned comm rows.
                contact.refresh_from_db()
                contact._sync_primary_communication_links()
                contact.refresh_from_db()

                for row in Email.objects.filter(contact_id=contact.id).only("id", "refs"):
                    if _ensure_comm_contact_ref(row, contact, dry_run=False):
                        summary.comm_refs_updated += 1
                for row in Phone.objects.filter(contact_id=contact.id).only("id", "refs"):
                    if _ensure_comm_contact_ref(row, contact, dry_run=False):
                        summary.comm_refs_updated += 1
                for row in Domain.objects.filter(contact_id=contact.id).only("id", "refs"):
                    if _ensure_comm_contact_ref(row, contact, dry_run=False):
                        summary.comm_refs_updated += 1
                for row in Address.objects.filter(contact_id=contact.id).only("id", "refs"):
                    if _ensure_comm_contact_ref(row, contact, dry_run=False):
                        summary.comm_refs_updated += 1

                after = {
                    "email_id": contact.email_id,
                    "phone_id": contact.phone_id,
                    "domain_id": contact.domain_id,
                    "address_id": contact.address_id,
                }
                if after != before:
                    summary.updated_contacts += 1
            else:
                # Dry-run: flag as potentially updated when scalar comm data exists.
                if _norm(contact.email) or _norm(contact.phone) or _norm(contact.domain) or _norm(contact.address_full):
                    summary.updated_contacts += 1
        except Exception:
            summary.errors += 1

    # ── Phase 2: dangling comm records with no contact FK ────────────
    if repair_dangling:
        repair_dangling_communications(
            summary=summary,
            dry_run=dry_run,
            emit_alice=emit_alice,
        )

    # ── Phase 3: Alice pattern-watch ─────────────────────────────────
    if emit_alice:
        _check_duplicate_comm_values(emit_alice=True, summary=summary)
        if _emit_alice_maintenance_errors(summary.errors):
            summary.alice_notes_created += 1
        if _emit_alice_run_summary(summary, dry_run):
            summary.alice_notes_created += 1

    return summary.as_dict()
