"""
Load Q&A data from qa.json into Setting records.
Creates qa_questions Setting records for each group and a qa_counters singleton.
"""
import json
import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.core.models import Setting

LOG_FILE = "/Users/williamjames/Documents/CommerceExpert/webClerk3/load_qa.log"


class Command(BaseCommand):
    help = "Load Q&A data from qa.json into Setting records"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be loaded without loading'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing qa_questions and qa_counters settings before loading'
        )

    def setup_logging(self):
        self.logger = logging.getLogger('load_qa')
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        fh = logging.FileHandler(LOG_FILE, mode='w')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(fh)
        return self.logger

    def log(self, message, level='info'):
        if level == 'error':
            self.logger.error(message)
            self.stderr.write(self.style.ERROR(message))
        elif level == 'warning':
            self.logger.warning(message)
            self.stdout.write(self.style.WARNING(message))
        elif level == 'success':
            self.logger.info(message)
            self.stdout.write(self.style.SUCCESS(message))
        else:
            self.logger.info(message)
            self.stdout.write(message)

    def handle(self, *args, **options):
        self.setup_logging()
        
        source_file = "/Users/williamjames/Documents/CommerceExpert/webClerk3/readmes/topics/qa/qa.json"
        dry_run = options['dry_run']
        clear = options['clear']
        
        start_time = datetime.now()
        
        self.log("═" * 65)
        self.log(f"  LOAD Q&A STARTED: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"  Source: {source_file}")
        self.log(f"  Log file: {LOG_FILE}")
        self.log("═" * 65)
        self.log("")
        
        # Load JSON
        try:
            with open(source_file, 'r') as f:
                data = json.load(f)
            self.log(f"  Loaded {len(data)} groups from JSON")
        except Exception as e:
            self.log(f"  Error reading file: {e}", 'error')
            return
        
        if clear and not dry_run:
            deleted_q, _ = Setting.objects.filter(purpose='wc:qa_questions').delete()
            deleted_c, _ = Setting.objects.filter(purpose='wc:qa_counters').delete()
            if deleted_q or deleted_c:
                self.log(f"  Cleared {deleted_q} qa_questions and {deleted_c} qa_counters records")
        
        created_groups = 0
        total_questions = 0
        total_answers = 0
        max_question_id = 0
        max_answer_id = 0
        errors = 0
        
        # Process each group
        for group_name, items in data.items():
            self.log(f"")
            self.log(f"  ┌─ Group: {group_name}")
            
            # Extract setting metadata (first item with 'setting' key)
            setting_meta = None
            questions = []
            
            for item in items:
                if 'setting' in item:
                    setting_meta = item['setting']
                elif 'question' in item:
                    questions.append(item)
                    # Track max IDs
                    q_id = item.get('id', 0)
                    if q_id > max_question_id:
                        max_question_id = q_id
                    for ans in item.get('answers', []):
                        a_id = ans.get('id', 0)
                        if a_id > max_answer_id:
                            max_answer_id = a_id
            
            if not setting_meta:
                # Use defaults
                setting_meta = {
                    'purpose': 'wc:qa_questions',
                    'model_target': 'all',
                    'role': 'all',
                    'name': group_name,
                    'security_level': 1,
                    'is_active': True
                }
            
            self.log(f"  │  Questions: {len(questions)}")
            total_questions += len(questions)
            
            # Count answers
            answer_count = sum(len(q.get('answers', [])) for q in questions)
            total_answers += answer_count
            self.log(f"  │  Answers: {answer_count}")
            
            if dry_run:
                self.log(f"  └─ Would create Setting for '{group_name}'")
                created_groups += 1
                continue
            
            # Build Setting data
            setting_data = {
                'template': {
                    'allow_freeform': False,
                    'allow_multiple': False,
                    'require_image': False,
                    'image_max': 5,
                    'image_types': ['jpg', 'png', 'webp']
                },
                'questions': questions
            }
            
            try:
                with transaction.atomic():
                    setting, was_created = Setting.objects.update_or_create(
                        purpose='wc:qa_questions',
                        name=group_name,
                        defaults={
                            'role': setting_meta.get('role', 'all'),
                            'parent_model': None,  # QA applies to all models
                            'security_level': setting_meta.get('security_level', 1),
                            'is_active': setting_meta.get('is_active', True),
                            'config': setting_data
                        }
                    )
                    action = "Created" if was_created else "Updated"
                    self.log(f"  └─ {action} Setting id={setting.id}", 'success')
                    created_groups += 1
            except Exception as e:
                errors += 1
                self.log(f"  └─ Error: {str(e)[:80]}", 'error')
        
        # Create qa_counters singleton
        self.log("")
        self.log(f"  Creating qa_counters singleton...")
        self.log(f"  │  Max question_id: {max_question_id}")
        self.log(f"  │  Max answer_id: {max_answer_id}")
        
        if not dry_run:
            try:
                with transaction.atomic():
                    counters, was_created = Setting.objects.update_or_create(
                        purpose='wc:qa_counters',
                        defaults={
                            'name': 'counters',
                            'role': 'all',
                            'parent_model': None,  # Global counter
                            'security_level': 1,
                            'is_active': True,
                            'config': {
                                'question_max': max_question_id,
                                'answer_max': max_answer_id
                            }
                        }
                    )
                    action = "Created" if was_created else "Updated"
                    self.log(f"  └─ {action} qa_counters id={counters.id}", 'success')
            except Exception as e:
                errors += 1
                self.log(f"  └─ Error: {str(e)[:80]}", 'error')
        else:
            self.log(f"  └─ Would create qa_counters")
        
        # Summary
        self.log("")
        self.log("═" * 65)
        if dry_run:
            self.log(f"  DRY RUN: Would create {created_groups} groups, {total_questions} questions, {total_answers} answers")
        else:
            self.log(f"  COMPLETE: {created_groups} groups, {total_questions} questions, {total_answers} answers", 'success')
            if errors:
                self.log(f"  Errors: {errors}", 'warning')
        
        duration = (datetime.now() - start_time).total_seconds()
        self.log(f"  Duration: {duration:.1f}s")
        self.log("═" * 65)
