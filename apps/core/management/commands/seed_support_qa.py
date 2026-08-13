"""Seed the Support Q&A system.

Creates Settings for:
1. support_qa search preset — find existing answers before asking
2. support_qa schema — defines the Q&A Document structure
3. support_qa scoring — user helpfulness ratings

The lifecycle:
  User asks → search existing Q&A → match? show answer + score
  → no match? Alice tries from vector store
  → Alice answers? save as Q&A Document (source=alice)
  → Alice can't? escalate to Claude (source=claude)
  → Claude can't? escalate to Bill (source=bill)
  → answer saved → syncs to all deployments via WCHQ

Usage:
    python manage.py seed_support_qa
"""
from django.core.management.base import BaseCommand
from apps.core.models import Setting


class Command(BaseCommand):
    help = 'Seed Support Q&A system — search, score, escalate'

    def handle(self, *args, **options):
        # 1. Q&A search preset — find answers by keyword before asking
        _, created = Setting.objects.update_or_create(
            ida='search-document-support-qa',
            defaults={
                'name': 'Support Q&A',
                'purpose': 'search',
                'parent_model': 'Document',
                'is_active': True,
                'config': {
                    'request_filters': {
                        'config__purpose': {
                            'field': 'config__purpose',
                            'lookup': 'exact',
                            'value': 'support_qa',
                        },
                        'status': {
                            'field': 'status',
                            'lookup': 'exact',
                            'value': 'published',
                        },
                    },
                    'ordering': '-config__score_avg',
                    'pagination': {'limit': 50, 'offset': 0},
                    'search_fields': ['name', 'body', 'description'],
                    'description': (
                        'Search answered support questions. Highest-scored '
                        'answers appear first. Use before asking a new question.'
                    ),
                },
            },
        )
        self.stdout.write(f'  {"Created" if created else "Updated"}: search preset')

        # 2. Q&A Document schema — what fields a Q&A record carries
        _, created = Setting.objects.update_or_create(
            ida='schema-support-qa',
            defaults={
                'name': 'Support Q&A Schema',
                'purpose': 'config',
                'parent_model': 'Document',
                'is_active': True,
                'config': {
                    'purpose_value': 'support_qa',
                    'fields': {
                        'name': 'The question (as the user phrased it)',
                        'description': 'Short summary of the answer',
                        'body': 'Full answer in markdown',
                        'status': 'draft | published | needs_review',
                    },
                    'config_schema': {
                        'purpose': 'support_qa',
                        'source': 'alice | claude | bill | user',
                        'asked_by': 'contact_id or agent name',
                        'answered_by': 'contact_id or agent name',
                        'dt_asked': 'UTC ISO timestamp',
                        'dt_answered': 'UTC ISO timestamp or null',
                        'score_count': 'number of user ratings',
                        'score_sum': 'sum of all ratings (1-5)',
                        'score_avg': 'score_sum / score_count',
                        'related_idas': 'list of related Q&A Document IDAs',
                        'keywords': 'list of alternate phrasings/keywords',
                        'escalation_chain': [
                            'list of who tried to answer and could not',
                        ],
                    },
                    'refs_schema': {
                        'tags': ['support', 'qa', '<topic>'],
                    },
                    'lifecycle': (
                        'draft: question asked, no answer yet. '
                        'published: answered and scored > 0. '
                        'needs_review: score_avg < 2.0 or flagged.'
                    ),
                },
            },
        )
        self.stdout.write(f'  {"Created" if created else "Updated"}: Q&A schema')

        # 3. Unanswered Q&A search — for Bill/Claude/Alice to pick up
        _, created = Setting.objects.update_or_create(
            ida='search-document-support-qa-unanswered',
            defaults={
                'name': 'Unanswered Questions',
                'purpose': 'search',
                'parent_model': 'Document',
                'is_active': True,
                'config': {
                    'request_filters': {
                        'config__purpose': {
                            'field': 'config__purpose',
                            'lookup': 'exact',
                            'value': 'support_qa',
                        },
                        'status': {
                            'field': 'status',
                            'lookup': 'exact',
                            'value': 'draft',
                        },
                    },
                    'ordering': 'dt_created',
                    'pagination': {'limit': 50, 'offset': 0},
                    'description': (
                        'Questions waiting for answers. Oldest first. '
                        'Alice, Claude, and Bill all check this queue.'
                    ),
                },
            },
        )
        self.stdout.write(f'  {"Created" if created else "Updated"}: unanswered search')

        # 4. Low-scored answers — need improvement
        _, created = Setting.objects.update_or_create(
            ida='search-document-support-qa-low-scored',
            defaults={
                'name': 'Low-Scored Answers',
                'purpose': 'search',
                'parent_model': 'Document',
                'is_active': True,
                'config': {
                    'request_filters': {
                        'config__purpose': {
                            'field': 'config__purpose',
                            'lookup': 'exact',
                            'value': 'support_qa',
                        },
                        'status': {
                            'field': 'status',
                            'lookup': 'exact',
                            'value': 'needs_review',
                        },
                    },
                    'ordering': 'config__score_avg',
                    'pagination': {'limit': 50, 'offset': 0},
                    'description': (
                        'Answered questions with low user scores. '
                        'These need better answers or rephrasing.'
                    ),
                },
            },
        )
        self.stdout.write(f'  {"Created" if created else "Updated"}: low-scored search')

        self.stdout.write(self.style.SUCCESS(
            '\nSupport Q&A system ready.\n'
            '\nTo create a Q&A Document:\n'
            '  POST /wcapi/save/ model_name=document\n'
            '  { name: "How do I...?",\n'
            '    status: "draft",\n'
            '    config: { purpose: "support_qa", source: "user",\n'
            '              asked_by: "...", score_count: 0, score_sum: 0 } }\n'
            '\nTo score an answer:\n'
            '  POST /wcapi/manage/ action=score_support_qa\n'
            '  { document_id: N, score: 1-5 }\n'
            '\nSaved searches:\n'
            '  /db/document → "Support Q&A" (answered, by score)\n'
            '  /db/document → "Unanswered Questions" (draft, oldest first)\n'
            '  /db/document → "Low-Scored Answers" (needs_review)\n'
        ))
