"""Review and clear Alice's Pydantic schema question queue.

Usage:
    python manage.py schema_questions              # list open questions
    python manage.py schema_questions --clear      # mark all as acknowledged
    python manage.py schema_questions --model item # filter by model
    python manage.py schema_questions --stats      # count by model
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Review Alice's Pydantic schema questions"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Acknowledge all open questions")
        parser.add_argument("--model", type=str, help="Filter by model name")
        parser.add_argument("--stats", action="store_true", help="Show count by model")

    def handle(self, *args, **options):
        from apps.ai_assistant.models.alice import AliceObservation

        qs = AliceObservation.objects.filter(category='schema', acknowledged=False)

        if options["model"]:
            qs = qs.filter(model_name=options["model"])

        if options["stats"]:
            from django.db.models import Count
            stats = (qs.values('model_name')
                     .annotate(count=Count('id'))
                     .order_by('-count'))
            total = 0
            for row in stats:
                self.stdout.write(f"  {row['model_name']:40s} {row['count']}")
                total += row['count']
            self.stdout.write(f"\n  Total open schema questions: {total}")
            return

        if options["clear"]:
            now_ms = int(timezone.now().timestamp() * 1000)
            count = qs.update(acknowledged=True, dt_acknowledged=now_ms)
            self.stdout.write(f"Acknowledged {count} schema question(s).")
            return

        # List open questions
        questions = qs.order_by('model_name', 'dt_created')
        if not questions.exists():
            self.stdout.write("No open schema questions.")
            return

        current_model = None
        for q in questions:
            if q.model_name != current_model:
                current_model = q.model_name
                self.stdout.write(f"\n  [{current_model}]")
            cfg = q.config or {}
            field = cfg.get('field', '')
            field_str = f" ({field})" if field else ""
            self.stdout.write(f"    #{q.pk} {q.message}{field_str}")
