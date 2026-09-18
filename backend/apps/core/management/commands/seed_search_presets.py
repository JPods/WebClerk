from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.core.models.report import Report


# Saved searches live as Report records (category='search', output_type='search').
# Date-range presets are handled by the built-in date_between function.

SEARCH_PRESETS = [
    {
        'ida': 'search-assigned-period',
        'name': 'Actions: Assigned To in Period',
        'description': 'Filter actions by assignee within a date range.',
        'model_name': 'action',
        'config': {
            'request_keyword': 'assigned_to',
            'request_filters': {
                'begin': {'field': 'dt_created', 'lookup': 'gte'},
                'end': {'field': 'dt_created', 'lookup': 'lte'},
            },
            'ordering': '-dt_created',
            'pagination': {'limit': 50, 'offset': 0},
        },
    },
    {
        'ida': 'search-assigned-active',
        'name': 'Actions: Assigned Active',
        'description': 'Filter active actions by assignee.',
        'model_name': 'action',
        'config': {
            'request_keyword': 'assigned_to',
            'request_filters': {
                'is_active': {'field': 'is_active', 'lookup': 'exact'},
            },
            'ordering': '-dt_created',
            'pagination': {'limit': 50, 'offset': 0},
        },
    },
    {
        'ida': 'search-assigned-priority',
        'name': 'Actions: Active by Priority',
        'description': 'Filter active actions by assignee and priority.',
        'model_name': 'action',
        'config': {
            'request_keyword': 'assigned_to',
            'request_filters': {
                'is_active': {'field': 'is_active', 'lookup': 'exact'},
                'priority': {'field': 'priority', 'lookup': 'exact'},
            },
            'ordering': '-dt_created',
            'pagination': {'limit': 50, 'offset': 0},
        },
    },
    {
        'ida': 'search-questions-bill',
        'name': 'Questions for Bill',
        'description': 'Questions that neither Alice nor Claude can answer.',
        'model_name': 'action',
        'config': {
            'ordering': '-dt_created',
            'pagination': {'limit': 50, 'offset': 0},
            'request_filters': {
                'status': {'field': 'status', 'value': 'pending', 'lookup': 'exact'},
                'metadata__source': {'field': 'metadata__source', 'value': 'question_for_bill', 'lookup': 'exact'},
            },
        },
    },
    {
        'ida': 'search-support-qa',
        'name': 'Support Q&A',
        'description': 'Search answered support questions. Highest-scored answers first.',
        'model_name': 'document',
        'config': {
            'ordering': '-config__score_avg',
            'pagination': {'limit': 50, 'offset': 0},
            'search_fields': ['name', 'body', 'description'],
            'request_filters': {
                'status': {'field': 'status', 'value': 'published', 'lookup': 'exact'},
                'config__purpose': {'field': 'config__purpose', 'value': 'support_qa', 'lookup': 'exact'},
            },
        },
    },
    {
        'ida': 'search-low-scored',
        'name': 'Low-Scored Answers',
        'description': 'Answered questions with low user scores. Need better answers or rephrasing.',
        'model_name': 'document',
        'config': {
            'ordering': 'config__score_avg',
            'pagination': {'limit': 50, 'offset': 0},
            'request_filters': {
                'status': {'field': 'status', 'value': 'needs_review', 'lookup': 'exact'},
                'config__purpose': {'field': 'config__purpose', 'value': 'support_qa', 'lookup': 'exact'},
            },
        },
    },
    {
        'ida': 'search-unanswered',
        'name': 'Unanswered Questions',
        'description': 'Questions waiting for answers. Oldest first.',
        'model_name': 'document',
        'config': {
            'ordering': 'dt_created',
            'pagination': {'limit': 50, 'offset': 0},
            'request_filters': {
                'status': {'field': 'status', 'value': 'draft', 'lookup': 'exact'},
                'config__purpose': {'field': 'config__purpose', 'value': 'support_qa', 'lookup': 'exact'},
            },
        },
    },
]


class Command(BaseCommand):
    help = "Seed saved search presets as Report records"

    def handle(self, *args, **options):
        created = 0
        updated = 0

        for preset in SEARCH_PRESETS:
            _, was_created = Report.objects.update_or_create(
                ida=preset['ida'],
                defaults={
                    'name': preset['name'],
                    'description': preset['description'],
                    'category': 'search',
                    'output_type': 'search',
                    'model_name': preset['model_name'],
                    'config': preset['config'],
                    'is_active': True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded search presets: created={created}, updated={updated}, total={len(SEARCH_PRESETS)}"
            )
        )