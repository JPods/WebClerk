from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from apps.core.models import Action, Contact


@dataclass(frozen=True)
class ContactRecord:
    contact_id: int
    attention: str
    norm: str
    tokens: set[str]


def _normalize(value: Optional[str]) -> str:
    if not value:
        return ""
    return " ".join(value.strip().lower().split())


def _build_contact_index() -> List[ContactRecord]:
    items: List[ContactRecord] = []
    for contact in Contact.objects.all().only("id", "attention", "name_first", "name_last", "email"):
        attention = contact.attention or ""
        pieces: List[str] = [attention, contact.name_first, contact.name_last]
        if contact.email:
            pieces.append(contact.email.split("@", 1)[0])
        norm = _normalize(attention)
        token_source = " ".join(filter(None, pieces))
        tokens = {_normalize(part) for part in token_source.split() if part}
        if not norm and not tokens:
            continue
        items.append(ContactRecord(contact_id=contact.id, attention=attention, norm=norm, tokens=tokens))
    return items


def _candidate_names(payload: object) -> Iterable[str]:
    if isinstance(payload, list):
        for entry in payload:
            if isinstance(entry, dict):
                for key in ("name", "attention", "full_name", "display"):
                    if isinstance(entry.get(key), str):
                        yield entry[key]
                        break
                else:
                    for value in entry.values():
                        if isinstance(value, str):
                            yield value
                            break
            elif isinstance(entry, str):
                yield entry
    elif isinstance(payload, dict):
        yield from _candidate_names([payload])
    elif isinstance(payload, str):
        yield payload


def _score_candidate(name: str, contact: ContactRecord) -> int:
    norm_name = _normalize(name)
    if not norm_name:
        return 0
    if norm_name == contact.norm:
        return 120
    if contact.norm.startswith(norm_name):
        return 90
    if norm_name in contact.norm:
        return 70
    name_tokens = set(norm_name.split())
    if name_tokens and name_tokens.issubset(contact.tokens):
        return 60 + min(len(name_tokens), 5)
    for token in name_tokens:
        if token and any(c_token.startswith(token) for c_token in contact.tokens):
            return 40
    return 0


def _find_best_contact(payload: object, contacts: List[ContactRecord]) -> Tuple[Optional[ContactRecord], bool]:
    best: Optional[ContactRecord] = None
    best_score = 0
    tie = False
    for name in _candidate_names(payload):
        for contact in contacts:
            score = _score_candidate(name, contact)
            if score > best_score:
                best = contact
                best_score = score
                tie = False
                if score >= 120:
                    return best, False
            elif score == best_score and score > 0 and best is not None and contact.contact_id != best.contact_id:
                tie = True
    if tie:
        return None, True
    if best is None or best_score == 0:
        return None, False
    return best, False


class Command(BaseCommand):
    help = "Populate action.contact_id using assigned_to names matched against contact attention"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--limit", type=int, default=None, help="Process only the first N action records")
        parser.add_argument("--dry-run", action="store_true", help="Calculate matches without writing changes")
        parser.add_argument(
            "--include-existing",
            action="store_true",
            help="Re-evaluate actions that already have a non-zero contact_id",
        )

    def handle(self, *args, **options) -> None:
        limit: Optional[int] = options["limit"]
        dry_run: bool = options["dry_run"]
        include_existing: bool = options["include_existing"]

        contacts = _build_contact_index()
        if not contacts:
            self.stdout.write(self.style.WARNING("No contacts available for matching."))
            return

        qs = Action.objects.all().only("id", "contact_id", "assigned_to")
        if not include_existing:
            qs = qs.filter(Q(contact_id__isnull=True) | Q(contact_id=0))

        processed = 0
        updated = 0
        skipped_no_match = 0
        skipped_ambiguous = 0

        iterator = qs.order_by("id").iterator(chunk_size=200)
        for action in iterator:
            if limit is not None and processed >= limit:
                break
            processed += 1

            match, ambiguous = _find_best_contact(action.assigned_to, contacts)
            if not match:
                if ambiguous:
                    skipped_ambiguous += 1
                elif action.assigned_to:
                    skipped_no_match += 1
                continue

            if action.contact_id and action.contact_id == match.contact_id:
                continue

            description = f"Action {action.id}: assigning contact_id {match.contact_id} ({match.attention})"
            if dry_run:
                self.stdout.write(f"DRY-RUN {description}")
            else:
                with transaction.atomic():
                    Action.objects.filter(pk=action.pk).update(contact_id=match.contact_id)
                self.stdout.write(self.style.SUCCESS(description))
            updated += 1

        summary = (
            f"Processed {processed} actions. "
            f"Updated {updated}. "
            f"No match {skipped_no_match}. "
            f"Ambiguous {skipped_ambiguous}."
        )
        if dry_run:
            self.stdout.write(summary)
        else:
            self.stdout.write(self.style.SUCCESS(summary))
