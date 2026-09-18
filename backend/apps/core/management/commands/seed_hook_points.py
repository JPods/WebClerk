"""Seed the hook-point registry and the first example hook.

The registry (Setting ``wc:hook_points``) is the list of places a hook may attach
and what it may do there. Superusers own it: seeding it is a starting point, not a
policy. Every point here is deliberately narrow.

The example hook writes one line to a log each time an invoice is saved. It is
created uncleared — it will not run until WCHQ confirms it — which is exactly what
the first hook should demonstrate.
"""
from django.core.management.base import BaseCommand

from apps.core.models import Report, Setting

POINTS = {
    # Watching: a hook that only records what happened.
    'invoice.save_post': {
        'may_set': ['metadata.review.*'],
        'may_create': ['note', 'action'],
        'may_log': ['record_saves'],
        'may_run': [],
    },
    'order.save_post': {
        'may_set': ['metadata.review.*'],
        'may_create': ['note'],
        'may_log': ['record_saves'],
        'may_run': [],
    },
    'contact.save_post': {
        'may_set': ['metadata.review.*'],
        'may_create': ['note'],
        'may_log': ['record_saves'],
        'may_run': [],
    },
    # Guarding: a hook that can stop a save. Narrow on purpose.
    'invoice.save_pre': {
        'may_set': [],
        'may_block': True,
        'may_create': [],
        'may_log': [],
        'may_run': [],
    },
    # Reporting: a hook that marks the records a report selected.
    'invoice.report_after': {
        'may_set': ['metadata.review.*'],
        'may_create': ['note', 'action'],
        'may_log': ['report_marks'],
        'may_run': ['*'],
    },
}

EXAMPLE_HOOK = {
    'point': 'invoice.save_post',
    'after': [
        {'append_log': {
            'log': 'record_saves',
            'ida': '{{record.ida}}',
            'status': '{{record.status}}',
            'by': '{{report.ida}}',
        }},
    ],
}


class Command(BaseCommand):
    help = 'Seed wc:hook_points and the example save-log hook'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Overwrite the registry if it already exists')
        parser.add_argument('--no-example', action='store_true',
                            help='Seed the registry only')

    def handle(self, *args, **options):
        setting = Setting.objects.filter(purpose='wc:hook_points').first()
        if setting and not options['force']:
            self.stdout.write('wc:hook_points exists — use --force to overwrite')
        else:
            if not setting:
                setting = Setting(name='Hook Points', purpose='wc:hook_points', scope='system')
                setting._setting_create_authorized = True
            else:
                setting._setting_update_authorized = True
            setting.config = {
                'note': 'Where report hooks may attach and what they may do there. '
                        'Superuser-owned. A point that is not listed cannot be hooked.',
                'points': POINTS,
            }
            setting.explanation = (
                'Declares every legal hook point. may_set / may_block / may_create / '
                'may_log / may_run bound what a hook may do at that point. Checked when '
                'a hook is saved and again when it runs.'
            )
            setting.save()
            self.stdout.write(self.style.SUCCESS(f'Seeded wc:hook_points ({len(POINTS)} points)'))

        if options['no_example']:
            return

        report = Report.objects.filter(ida='RPT-SAVE-LOG').first()
        if report:
            self.stdout.write('RPT-SAVE-LOG exists — left alone')
            return

        report = Report(
            ida='RPT-SAVE-LOG',
            name='Log every invoice save',
            category='function',
            model_name='invoice',
            description='Appends one line to logs/hooks/record_saves.jsonl on each invoice save.',
            explanation=(
                'The simplest possible hook: it records, it changes nothing. Submit it to '
                'WCHQ (Alice: send_review_request) and it starts running once cleared.'
            ),
            config={'hooks': EXAMPLE_HOOK},
        )
        report._hooks_authorized = True
        report.save()
        self.stdout.write(self.style.SUCCESS(
            'Seeded RPT-SAVE-LOG — uncleared. It will not run until WCHQ confirms it.'))
