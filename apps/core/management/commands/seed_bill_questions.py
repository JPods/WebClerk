"""Seed the "Questions for Bill" pipeline.

Creates:
1. A Setting record for the databrowser saved search (actions where
   metadata.source='question_for_bill' and status='pending')
2. An AliceObservation category entry (adds 'bill_question' to choices)

The pipeline:
- Alice creates: Action with metadata.source='question_for_bill'
  when she can't answer and Claude can't answer either
- Claude creates: same Action when he identifies a question only Bill
  can answer (domain knowledge, business decision, priorities)
- Bill sees: databrowser filter at /db/action?search=questions_for_bill
  or Alice coaching panel highlights them

Usage:
    python manage.py seed_bill_questions
"""
from django.core.management.base import BaseCommand
from apps.core.models import Setting


class Command(BaseCommand):
    help = 'Seed the Questions for Bill pipeline — saved search + observation category'

    def handle(self, *args, **options):
        # 1. Saved search preset for actions that are questions for Bill
        preset_ida = 'search-action-questions-for-bill'
        _, created = Setting.objects.update_or_create(
            ida=preset_ida,
            defaults={
                'name': 'Questions for Bill',
                'purpose': 'wc:search',
                'parent_model': 'Action',
                'is_active': True,
                'config': {
                    'request_filters': {
                        'metadata__source': {
                            'field': 'metadata__source',
                            'lookup': 'exact',
                            'value': 'question_for_bill',
                        },
                        'status': {
                            'field': 'status',
                            'lookup': 'exact',
                            'value': 'pending',
                        },
                    },
                    'ordering': '-dt_created',
                    'pagination': {'limit': 50, 'offset': 0},
                    'description': (
                        'Questions that neither Alice nor Claude can answer. '
                        'Domain knowledge, business decisions, priorities — '
                        'things only Bill knows.'
                    ),
                },
            },
        )
        status = 'Created' if created else 'Updated'
        self.stdout.write(f'  {status}: saved search "{preset_ida}"')

        # 2. Add bill_question to AliceObservation category choices
        #    We add it via a Setting so alice-patterns.py and MCP servers
        #    know it's a valid category without requiring a migration.
        cat_ida = 'alice-observation-extra-categories'
        _, created = Setting.objects.update_or_create(
            ida=cat_ida,
            defaults={
                'name': 'Alice Observation Extra Categories',
                'purpose': 'config',
                'parent_model': 'alice_observation',
                'is_active': True,
                'config': {
                    'extra_categories': [
                        {
                            'key': 'bill_question',
                            'label': 'Question for Bill',
                            'description': (
                                'A question that Alice and Claude both '
                                'tried to answer but could not. Requires '
                                'Bill\'s domain knowledge or decision.'
                            ),
                        },
                        {
                            'key': 'console',
                            'label': 'Console Capture',
                            'description': 'Browser console error/warning auto-captured',
                        },
                        {
                            'key': 'escalation',
                            'label': 'Escalation',
                            'description': 'Alice escalated to Claude Code',
                        },
                    ],
                },
            },
        )
        status = 'Created' if created else 'Updated'
        self.stdout.write(f'  {status}: extra categories "{cat_ida}"')

        self.stdout.write(self.style.SUCCESS(
            '\nQuestions for Bill pipeline ready.\n'
            '\nHow to use:\n'
            '  Alice:  alice_observe(event="bill_question", model_name="action",\n'
            '            message="...", data={"tried": [...], "why_bill": "..."})\n'
            '  Claude: Create Action with metadata.source="question_for_bill"\n'
            '  Bill:   /db/action → saved search "Questions for Bill"\n'
        ))
