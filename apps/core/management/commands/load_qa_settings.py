"""
Load Q&A questions from qa.json into Setting records.

Usage:
    python manage.py load_qa_settings
    python manage.py load_qa_settings --reset  # Delete existing and reload
"""
import json
import os
from django.core.management.base import BaseCommand
from apps.core.models import Setting


class Command(BaseCommand):
    help = 'Load Q&A questions from qa.json into Setting records'

    QA_JSON_PATH = os.path.join(
        os.path.dirname(__file__),
        '../../../..', 'readmes', 'topics', 'qa', 'qa.json'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing qa_questions and qa_counters settings before loading'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating'
        )

    def handle(self, *args, **options):
        reset = options.get('reset', False)
        dry_run = options.get('dry_run', False)

        # Load qa.json
        json_path = os.path.normpath(self.QA_JSON_PATH)
        if not os.path.exists(json_path):
            self.stderr.write(self.style.ERROR(f'qa.json not found at: {json_path}'))
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            qa_data = json.load(f)

        self.stdout.write(f'Loaded qa.json from {json_path}')
        self.stdout.write(f'Found {len(qa_data)} question groups: {", ".join(qa_data.keys())}')

        # Track max IDs for counter
        max_question_id = 0
        max_answer_id = 0

        # Reset if requested
        if reset and not dry_run:
            deleted_questions = Setting.objects.filter(purpose='qa_questions').delete()[0]
            deleted_counters = Setting.objects.filter(purpose='qa_counters').delete()[0]
            self.stdout.write(self.style.WARNING(
                f'Deleted {deleted_questions} qa_questions and {deleted_counters} qa_counters records'
            ))

        # Process each group
        for group_name, items in qa_data.items():
            # First item is the setting metadata, rest are questions
            setting_meta = None
            questions = []

            for item in items:
                if 'setting' in item:
                    setting_meta = item['setting']
                elif 'id' in item and 'question' in item:
                    questions.append(item)
                    # Track max IDs
                    if item.get('id', 0) > max_question_id:
                        max_question_id = item['id']
                    for ans in item.get('answers', []):
                        if ans.get('id', 0) > max_answer_id:
                            max_answer_id = ans['id']

            if not setting_meta:
                self.stderr.write(self.style.WARNING(
                    f'Skipping {group_name}: no setting metadata found'
                ))
                continue

            # Build the Setting data payload
            data_payload = {
                'template': {
                    'allow_freeform': False,
                    'allow_multiple': False,
                    'require_image': False,
                    'image_max': 5,
                    'image_types': ['jpg', 'png', 'webp', 'pdf'],
                },
                'questions': questions,
            }

            if dry_run:
                self.stdout.write(self.style.SUCCESS(
                    f'[DRY RUN] Would create/update qa_questions for "{group_name}" '
                    f'with {len(questions)} questions'
                ))
            else:
                # Get parent_model - use None/blank for "all"
                mt = setting_meta.get('parent_model', '')
                if mt == 'all':
                    mt = None
                
                # Create or update Setting record
                setting, created = Setting.objects.update_or_create(
                    purpose='qa_questions',
                    name=group_name,
                    defaults={
                        'parent_model': mt,
                        'role': setting_meta.get('role', 'all'),
                        'data': data_payload,
                    }
                )
                action = 'Created' if created else 'Updated'
                self.stdout.write(self.style.SUCCESS(
                    f'{action} qa_questions for "{group_name}" with {len(questions)} questions'
                ))

        # Create/update qa_counters singleton
        counters_data = {
            'question_max': max_question_id,
            'answer_max': max_answer_id,
        }

        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                f'[DRY RUN] Would create/update qa_counters: '
                f'question_max={max_question_id}, answer_max={max_answer_id}'
            ))
        else:
            counter, created = Setting.objects.update_or_create(
                purpose='qa_counters',
                defaults={
                    'name': 'counters',
                    'parent_model': 'question_answer',
                    'role': 'all',
                    'data': counters_data,
                }
            )
            action = 'Created' if created else 'Updated'
            self.stdout.write(self.style.SUCCESS(
                f'{action} qa_counters: question_max={max_question_id}, answer_max={max_answer_id}'
            ))

        self.stdout.write(self.style.SUCCESS('\nQ&A settings loaded successfully!'))
