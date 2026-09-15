"""Run Alice's schema audit -- check JSON envelopes against Pydantic schemas.

Usage:
    python manage.py audit_schemas                    # audit all models
    python manage.py audit_schemas --model contact    # audit one model
    python manage.py audit_schemas --limit 50         # sample more records
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run Alice's schema audit against actual data"

    def add_arguments(self, parser):
        parser.add_argument("--model", type=str, nargs="*", help="Model name(s) to audit")
        parser.add_argument("--limit", type=int, default=10, help="Records to sample per model")

    def handle(self, *args, **options):
        from apps.ai_assistant.services.watch_envelopes import audit_model_schemas

        result = audit_model_schemas(
            model_names=options.get("model"),
            limit_per_model=options["limit"],
        )

        self.stdout.write(f"Audited {result['models_audited']} models.")
        self.stdout.write(f"Logged {result['total_questions']} schema question(s).")

        if result['by_model']:
            self.stdout.write("\nQuestions by model:")
            for model, count in sorted(result['by_model'].items()):
                self.stdout.write(f"  {model:40s} {count}")
