"""Mine WC3 readmes into Q&A Documents and Quiz Documents.

Two outputs from the same source material:

1. Support Q&A (config.purpose='support_qa') — Alice answering user questions.
   Each ## heading becomes a question, the section content becomes the answer.
   Users search these when stuck. Alice serves them via the help system.

2. Quiz questions (config.purpose='qa-alice-*') — Alice testing users.
   Key concepts become multiple-choice questions with correct answers and WHY.
   Used in training drills, onboarding, inspections, checklists.

Usage:
    python manage.py seed_qa_from_readmes
    python manage.py seed_qa_from_readmes --force     # overwrite existing
    python manage.py seed_qa_from_readmes --dry-run   # preview without writing
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand
from apps.docs.models.document import Document

WC3_ROOT = Path(__file__).resolve().parents[5]  # .../WebClerk/app/

# Readmes to mine — same list as the seed_wc3_*_docs commands
READMES = [
    # System
    ('readmes/getting-started/01-architecture-overview.md', 'system', 'WC3 Architecture'),
    ('readmes/architecture/03-wcapi-gateway.md', 'system', 'wcapi Gateway'),
    ('readmes/architecture/04-wcapi-usage.md', 'system', 'wcapi Usage'),
    ('readmes/architecture/05-model-registry.md', 'system', 'Model Registry'),
    ('readmes/architecture/06-api-conventions.md', 'system', 'API Conventions'),
    ('readmes/architecture/json-envelope-policy.md', 'system', 'JSON Envelopes'),
    ('readmes/infrastructure/settings.md', 'system', 'Settings'),
    ('readmes/tools/setting-policy.md', 'system', 'Setting Policy'),
    ('readmes/architecture/prefs-architecture.md', 'system', 'Prefs'),
    ('readmes/getting-started/onboarding.md', 'system', 'Onboarding'),
    # Commerce
    ('readmes/transactions/08-transaction-calculations.md', 'commerce', 'Transaction Calculations'),
    ('readmes/transactions/08-transaction-save.md', 'commerce', 'Transaction Save'),
    ('readmes/accounting/ledger-financial-system.md', 'commerce', 'Ledger & GL'),
    ('readmes/accounting/payment-application-design.md', 'commerce', 'Payments'),
    ('readmes/transactions/commission-operations.md', 'commerce', 'Commissions'),
    ('readmes/products/forecasting.md', 'commerce', 'Forecasting'),
    ('readmes/transactions/orgs-financial-structure.md', 'commerce', 'Org Financials'),
    ('readmes/accounting/statement-harvester.md', 'commerce', 'Statements'),
    # Operations
    ('readmes/operations/databrowser-guide.md', 'operations', 'databrowser'),
    ('readmes/operations/saved-searches.md', 'operations', 'Saved Searches'),
    ('readmes/contacts/email-operations.md', 'operations', 'Email'),
    ('readmes/sync/source-attribution.md', 'operations', 'Source Attribution'),
    ('readmes/alice/alice-coaching.md', 'operations', 'Alice Coaching'),
    ('readmes/operations/qa-question-groups.md', 'operations', 'QA Questions'),
    # Alice
    ('readmes/alice/pattern-recognition.md', 'alice', 'Pattern Recognition'),
    ('readmes/alice/data-quality.md', 'alice', 'Data Quality'),
    ('readmes/alice/observation-setup.md', 'alice', 'Observations'),
    ('readmes/alice/dedup.md', 'alice', 'Dedup'),
    ('readmes/alice/escalation.md', 'alice', 'Escalation'),
    ('readmes/alice/erosion-tracking.md', 'alice', 'Erosion Tracking'),
]


def _heading_to_question(heading: str, doc_title: str) -> str:
    """Convert a markdown heading to a natural question."""
    h = heading.strip().rstrip('?').strip()

    # Already a question
    if any(h.lower().startswith(w) for w in ('how', 'what', 'when', 'why', 'where', 'who', 'can', 'does', 'is')):
        return h + '?'

    # Common heading patterns → natural questions
    patterns = [
        (r'^overview$', f'What is {doc_title}?'),
        (r'^principle$', f'What is the principle behind {doc_title}?'),
        (r'^the (?:two )?rules?$', f'What are the rules for {doc_title}?'),
        (r'^key features', f'What are the key features of {doc_title}?'),
        (r'^architecture', f'How is {doc_title} architected?'),
        (r'^security', f'How does security work in {doc_title}?'),
        (r'^configuration', f'How do you configure {doc_title}?'),
        (r'^troubleshooting', f'How do you troubleshoot {doc_title}?'),
        (r'^setup', f'How do you set up {doc_title}?'),
        (r'^usage', f'How do you use {doc_title}?'),
        (r'^examples?$', f'What are examples of {doc_title}?'),
        (r'^the decision test$', f'How do you decide when to use {doc_title}?'),
    ]
    for pattern, question in patterns:
        if re.match(pattern, h, re.IGNORECASE):
            return question

    # Default: "What is [heading] in [doc_title]?"
    if len(h) < 60:
        return f'What is {h} in {doc_title}?'
    return f'{h}?'


def _extract_sections(content: str) -> list[dict[str, str]]:
    """Split markdown into sections by ## headings. Returns list of {heading, body}."""
    sections = []
    lines = content.split('\n')
    current_heading = ''
    current_body: list[str] = []

    for line in lines:
        if line.startswith('## '):
            if current_heading and current_body:
                body = '\n'.join(current_body).strip()
                if len(body) > 50:  # Skip tiny sections
                    sections.append({'heading': current_heading, 'body': body})
            current_heading = line[3:].strip()
            current_body = []
        elif current_heading:
            current_body.append(line)

    # Last section
    if current_heading and current_body:
        body = '\n'.join(current_body).strip()
        if len(body) > 50:
            sections.append({'heading': current_heading, 'body': body})

    return sections


def _make_ida(prefix: str, text: str) -> str:
    """Generate a stable IDA from text. Max 40 chars (DB constraint)."""
    slug = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
    # Use hash suffix if slug would be truncated (ensures uniqueness)
    max_slug = 40 - len(prefix) - 1  # prefix + dash
    if len(slug) > max_slug:
        h = hashlib.md5(text.encode()).hexdigest()[:6]
        slug = slug[:max_slug - 7] + '-' + h
    return f'{prefix}-{slug}'


def _extract_quiz_questions(heading: str, body: str, doc_title: str, domain: str) -> list[dict]:
    """Extract structured quiz questions from a section.

    Looks for tables, rules, and key definitions that lend themselves
    to multiple-choice testing.
    """
    questions = []
    q_id = 0

    # Pattern 1: Tables with | column | column | → quiz on relationships
    table_rows = re.findall(r'^\|(.+)\|(.+)\|', body, re.MULTILINE)
    if len(table_rows) >= 3:
        # Use first data row as a quiz question
        # Skip header and separator rows
        data_rows = [r for r in table_rows if '---' not in r[0] and r[0].strip()]
        if len(data_rows) >= 2:
            first = data_rows[0]
            col1 = first[0].strip().strip('*').strip()
            col2 = first[1].strip().strip('*').strip()
            if col1 and col2 and len(col1) < 100:
                q_id += 1
                wrong_answers = []
                for row in data_rows[1:4]:
                    wrong = row[1].strip().strip('*').strip()
                    if wrong and wrong != col2:
                        wrong_answers.append(wrong)

                if wrong_answers:
                    questions.append({
                        'id': q_id,
                        'question': f'In {doc_title}, what does "{col1}" do?',
                        'answers': [
                            {'id': 1, 'text': col2, 'correct': True},
                        ] + [
                            {'id': i + 2, 'text': w, 'correct': False}
                            for i, w in enumerate(wrong_answers[:3])
                        ],
                        'why': f'From {doc_title} — {heading}',
                        'domain': domain,
                    })

    # Pattern 2: Bold definitions "**term** — definition" → quiz on definitions
    defs = re.findall(r'\*\*([^*]+)\*\*[:\s—–-]+(.{20,200}?)(?:\n|$)', body)
    for term, definition in defs[:3]:
        if len(term) > 5 and len(term) < 80:
            q_id += 1
            questions.append({
                'id': q_id,
                'question': f'What is {term}?',
                'answers': [
                    {'id': 1, 'text': definition.strip()[:200], 'correct': True},
                    {'id': 2, 'text': 'A system error that needs debugging', 'correct': False},
                    {'id': 3, 'text': 'An optional feature not used in production', 'correct': False},
                ],
                'why': f'From {doc_title} — {heading}: {definition.strip()[:200]}',
                'domain': domain,
            })

    # Pattern 3: "Rule N:" or numbered rules → quiz on the rule
    rules = re.findall(r'(?:Rule \d+|###?\s+Rule \d+)[:\s]+(.{20,300}?)(?:\n\n|\n#|$)', body, re.DOTALL)
    for rule_text in rules[:2]:
        clean = rule_text.strip().split('\n')[0].strip()
        if len(clean) > 20:
            q_id += 1
            questions.append({
                'id': q_id,
                'question': f'What is the rule for {heading.lower()} in {doc_title}?',
                'answers': [
                    {'id': 1, 'text': clean[:200], 'correct': True},
                    {'id': 2, 'text': 'There is no specific rule — use your judgment', 'correct': False},
                    {'id': 3, 'text': 'Ask the admin before proceeding', 'correct': False},
                ],
                'why': f'From {doc_title}: {clean[:200]}',
                'domain': domain,
            })

    return questions


class Command(BaseCommand):
    help = 'Mine WC3 readmes into Q&A Documents (help) and Quiz Documents (training)'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Overwrite existing records')
        parser.add_argument('--dry-run', action='store_true', help='Preview without writing')

    def handle(self, *args, **options):
        force = options['force']
        dry_run = options['dry_run']
        qa_created = qa_updated = qa_skipped = 0
        quiz_created = quiz_updated = 0
        total_quiz_questions = 0

        for git_path, domain, doc_title in READMES:
            full_path = WC3_ROOT / git_path
            if not full_path.exists():
                self.stdout.write(self.style.WARNING(f'  Missing: {git_path}'))
                continue

            content = full_path.read_text(encoding='utf-8')
            sections = _extract_sections(content)

            if not sections:
                continue

            self.stdout.write(f'\n  {doc_title} ({git_path}): {len(sections)} sections')

            # ── Free-form Q&A from each section ──
            for section in sections:
                question = _heading_to_question(section['heading'], doc_title)
                ida = _make_ida('QA', f'{doc_title}-{section["heading"]}')

                if dry_run:
                    self.stdout.write(f'    Q: {question}')
                    self.stdout.write(f'    A: {section["body"][:80]}...')
                    qa_created += 1
                    continue

                existing = Document.objects.filter(ida=ida).first()
                if existing and not force:
                    qa_skipped += 1
                    continue

                defaults = {
                    'name': question[:255],
                    'description': f'{doc_title} — {section["heading"]}'[:255],
                    'body': section['body'],
                    'status': 'published',
                    'mime_type': 'text/markdown',
                    'size_bytes': len(section['body'].encode('utf-8')),
                    'path': {'git_path': git_path, 'heading': section['heading']},
                    'config': {
                        'purpose': 'support_qa',
                        'source': 'readme_mining',
                        'domain': domain,
                        'doc_title': doc_title,
                        'score_count': 0,
                        'score_sum': 0,
                        'score_avg': 0,
                        'escalation_chain': [],
                        'keywords': [],
                    },
                    'refs': {
                        'tags': ['support', 'qa', domain, doc_title.lower().replace(' ', '-')],
                    },
                }

                _, was_created = Document.objects.update_or_create(
                    ida=ida, defaults=defaults,
                )
                if was_created:
                    qa_created += 1
                else:
                    qa_updated += 1

            # ── Quiz questions from key concepts ──
            all_quiz_questions = []
            for section in sections:
                quiz_qs = _extract_quiz_questions(
                    section['heading'], section['body'], doc_title, domain
                )
                all_quiz_questions.extend(quiz_qs)

            if all_quiz_questions:
                quiz_ida = _make_ida('QUIZ', doc_title)
                total_quiz_questions += len(all_quiz_questions)

                if dry_run:
                    for q in all_quiz_questions:
                        self.stdout.write(f'    QUIZ: {q["question"]}')
                    quiz_created += 1
                    continue

                # Renumber question IDs sequentially
                for i, q in enumerate(all_quiz_questions, 1):
                    q['id'] = i
                    for j, a in enumerate(q['answers'], 1):
                        a['id'] = j

                existing = Document.objects.filter(ida=quiz_ida).first()
                if existing and not force:
                    continue

                defaults = {
                    'name': f'Quiz: {doc_title}',
                    'description': f'{len(all_quiz_questions)} questions about {doc_title}',
                    'body': f'Training quiz for {doc_title}. {len(all_quiz_questions)} questions.',
                    'status': 'published',
                    'config': {
                        'purpose': f'qa-alice-{domain}',
                        'questions': all_quiz_questions,
                        'domain': domain,
                        'doc_title': doc_title,
                        'difficulty': 'beginner',
                    },
                    'refs': {
                        'tags': ['quiz', 'training', domain],
                        'keywords': ['qa_template'],
                    },
                }

                _, was_created = Document.objects.update_or_create(
                    ida=quiz_ida, defaults=defaults,
                )
                if was_created:
                    quiz_created += 1
                else:
                    quiz_updated += 1

        prefix = '[DRY RUN] ' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'\n{prefix}Q&A: {qa_created} created, {qa_updated} updated, {qa_skipped} skipped'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'{prefix}Quiz: {quiz_created} documents, {total_quiz_questions} questions total'
        ))
