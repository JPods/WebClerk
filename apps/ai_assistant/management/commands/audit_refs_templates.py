from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.ai_assistant.services.alice_notes import create_note
from apps.core.services.link_defaults import MODEL_LINK_TEMPLATES
from common.denorm_registry import DENORM_REGISTRY


RECOMMENDED_FIELDS: dict[str, list[str]] = {
    "contact": ["id", "display_name", "email", "phone", "attention"],
    "email": ["id", "email", "name", "type", "is_primary", "is_verified", "opt_out"],
    "phone": ["id", "number", "name", "country_code", "format", "opt_out"],
    "address": ["id", "address1", "city", "state", "zip", "country", "full"],
    "domain": ["id", "path", "type", "status"],
}


class Command(BaseCommand):
    help = "Audit refs.links/refs.keywords templates for key models and optionally create Alice notes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--models",
            nargs="*",
            default=["contact", "email", "phone", "address", "domain"],
            help="Model keys to audit (default: contact email phone address domain)",
        )
        parser.add_argument(
            "--no-alice",
            action="store_true",
            help="Do not create alice_pending notes; print report only.",
        )

    def handle(self, *args, **options):
        models = [m.lower() for m in options["models"]]
        create_alice_notes = not options["no_alice"]

        findings: list[dict] = []
        notes_created = 0

        for model_key in models:
            recommended = RECOMMENDED_FIELDS.get(model_key, [])
            denorm_fields = DENORM_REGISTRY.get(model_key, [])
            template_cfg = MODEL_LINK_TEMPLATES.get(model_key, {})
            template = template_cfg.get("link_template", {}) if isinstance(template_cfg, dict) else {}
            keyword_fields = template_cfg.get("keyword_fields", []) if isinstance(template_cfg, dict) else []

            denorm_missing = sorted([f for f in recommended if f not in denorm_fields])
            template_missing = sorted([f for f in recommended if f not in template])

            if denorm_missing or template_missing:
                finding = {
                    "model": model_key,
                    "denorm_missing": denorm_missing,
                    "template_missing": template_missing,
                    "current_denorm_fields": denorm_fields,
                    "current_keyword_fields": keyword_fields,
                }
                findings.append(finding)

                self.stdout.write(
                    self.style.WARNING(
                        f"[gap] {model_key}: denorm_missing={denorm_missing or 'none'} "
                        f"template_missing={template_missing or 'none'}"
                    )
                )

                if create_alice_notes:
                    note = create_note(
                        "pending",
                        role="config_suggestion",
                        name=f"refs template gap for {model_key}",
                        parent_model=model_key,
                        details={
                            "suggested_action": "align denorm registry and link template",
                            **finding,
                        },
                    )
                    notes_created += 1
                    self.stdout.write(f"  alice_note_id={note.id}")
            else:
                self.stdout.write(self.style.SUCCESS(f"[ok] {model_key}"))

        if findings:
            self.stdout.write(self.style.WARNING(f"Found {len(findings)} model(s) with refs template gaps."))
        else:
            self.stdout.write(self.style.SUCCESS("No refs template gaps detected for audited models."))

        if create_alice_notes:
            log_note = create_note(
                "log",
                role="system",
                name="refs template audit run",
                parent_model="contact",
                details={
                    "audited_models": models,
                    "gap_count": len(findings),
                    "gaps": findings,
                },
            )
            self.stdout.write(self.style.SUCCESS(f"Alice log note created: {log_note.id}"))

        self.stdout.write(self.style.SUCCESS(f"Alice notes created: {notes_created}"))
