"""Uploaded documents waiting in quarantine: list them, or run the checks again.

    python manage.py quarantine             # what is waiting or refused, and why
    python manage.py quarantine --recheck   # check again what is waiting (e.g. the
                                            # virus scanner was not running at upload)
"""
from django.core.management.base import BaseCommand

from apps.docs.models import Document
from apps.docs.services.document_sanitizer import clamav_scan, sanitize_document


class Command(BaseCommand):
    help = "List uploaded documents held in quarantine, or re-run their checks"

    def add_arguments(self, parser):
        parser.add_argument("--recheck", action="store_true",
                            help="Run the checks again on documents with status 'pending'")

    def handle(self, *args, **options):
        scan, why = clamav_scan(__file__)
        self.stdout.write(f"Virus scanner: {'running' if scan != 'not_run' else 'NOT running — ' + why[0]}")
        held = Document.objects.filter(path__storage="quarantine").order_by("id")
        if options["recheck"]:
            for doc in held.filter(config__quarantine__status="pending"):
                q = sanitize_document(doc)
                self.stdout.write(f"  {doc.id} {doc.name}: {q['status']} {q['reason']}")
            held = Document.objects.filter(path__storage="quarantine").order_by("id")
        for doc in held:
            q = (doc.config or {}).get("quarantine") or {}
            self.stdout.write(f"  {doc.id} {q.get('status', '?'):9} {doc.name}: {q.get('reason', '')}")
        self.stdout.write(f"{held.count()} document(s) in quarantine")
