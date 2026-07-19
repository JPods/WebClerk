"""
QA Service - Manage question templates and apply them to parent records.

Question templates live in Document records where refs.keywords contains
'qa_template'. Document provides body (WHY narrative), description (summary),
and refs (cross-references to specs, standards, regulatory requirements).
Questions are stored in Document.config.questions[].

The qa_counters singleton (Setting record) tracks globally unique question
and answer IDs across all templates.

Usage:
    from apps.docs.services.qa_service import QAService

    service = QAService()

    # Create a template
    doc = service.create_question_group(
        name='JPods Daily Pre-Op Inspection',
        description='Daily vehicle safety check — ASTM F770',
        body='Required by ASTM F770. Prevents undetected mechanical wear...',
        questions=[
            {'question': 'Guideway clear?', 'answers': ['Yes', 'No']},
            {'question': 'Notes', 'allow_freeform': True},
        ],
        refs={'standards': ['ASTM F770', 'FTA 49 CFR 673']},
    )

    # Apply template to a parent record
    qa_records = service.apply_questions(
        document_name='JPods Daily Pre-Op Inspection',
        parent_model='item',
        parent_id=123,
    )

    # Save an answer
    service.save_answer(qa_id=456, answer='Yes', contact_data={'id': 1, 'attention': 'Inspector'})
"""

from typing import List, Dict, Any, Optional
import logging

from django.db import transaction as db_transaction
from django.db.models import F
from django.core.exceptions import ValidationError, ObjectDoesNotExist

from apps.core.models import Setting
from apps.docs.models import QuestionAnswer
from apps.docs.models import Document

logger = logging.getLogger(__name__)


class QAService:
    """Service for managing Document-based question templates and applying them to parent records."""

    def __init__(self):
        pass

    # -----------------------------------------------------------------
    # ID allocation (qa_counters singleton)
    # -----------------------------------------------------------------

    def get_or_create_counters(self) -> Setting:
        """Get or create the qa_counters singleton."""
        counters, created = Setting.objects.get_or_create(
            purpose='qa_counters',
            defaults={
                'name': 'counters',
                'parent_model': 'question_answer',
                'role': 'all',
                'config': {'question_max': 0, 'answer_max': 0},
                'is_active': True,
            }
        )
        if created:
            logger.info("Created qa_counters singleton")
        return counters

    @db_transaction.atomic
    def allocate_question_ids(self, count: int) -> List[int]:
        """Allocate the next N unique question IDs."""
        counters = Setting.objects.select_for_update().get(purpose='qa_counters')
        data = counters.config or {}
        current_max = data.get('question_max', 0)
        new_ids = list(range(current_max + 1, current_max + count + 1))
        data['question_max'] = current_max + count
        counters.config = data
        counters.save(update_fields=['config'])
        logger.info(f"Allocated question IDs {new_ids[0]}-{new_ids[-1]}")
        return new_ids

    @db_transaction.atomic
    def allocate_answer_ids(self, count: int) -> List[int]:
        """Allocate the next N unique answer choice IDs."""
        counters = Setting.objects.select_for_update().get(purpose='qa_counters')
        data = counters.config or {}
        current_max = data.get('answer_max', 0)
        new_ids = list(range(current_max + 1, current_max + count + 1))
        data['answer_max'] = current_max + count
        counters.config = data
        counters.save(update_fields=['config'])
        logger.info(f"Allocated answer IDs {new_ids[0]}-{new_ids[-1]}")
        return new_ids

    # -----------------------------------------------------------------
    # Template management
    # -----------------------------------------------------------------

    @db_transaction.atomic
    def create_question_group(
        self,
        name: str,
        description: str,
        body: str,
        questions: List[Dict[str, Any]],
        refs: Optional[Dict[str, Any]] = None,
        template_defaults: Optional[Dict[str, Any]] = None,
    ) -> Document:
        """Create a Document-based question template with auto-assigned IDs.

        Args:
            name: Template name (e.g., 'JPods Daily Pre-Op Inspection')
            description: One-line summary
            body: WHY this template exists (regulatory basis, what it prevents)
            questions: List of question definitions, each with:
                - question: str (required)
                - answers: List[str] (optional)
                - allow_freeform: bool (optional)
                - allow_multiple: bool (optional)
                - require_image: bool (optional)
                - category: str (optional)
            refs: Optional refs dict. 'qa_template' keyword added automatically.
                  Example: {"standards": ["ASTM F770"], "spec_refs": ["SPEC-01"]}
            template_defaults: Default options for all questions

        Returns:
            Document: The created template Document
        """
        self.get_or_create_counters()

        total_answers = sum(
            len(q.get('answers', [])) if isinstance(q.get('answers', []), list) else 0
            for q in questions
        )

        question_ids = self.allocate_question_ids(len(questions))
        answer_ids = self.allocate_answer_ids(total_answers) if total_answers > 0 else []

        answer_id_iter = iter(answer_ids)
        processed_questions = []

        for q_def, q_id in zip(questions, question_ids):
            processed_q: Dict[str, Any] = {
                'id': q_id,
                'question': q_def['question'],
            }

            raw_answers = q_def.get('answers', [])
            if raw_answers:
                processed_answers = []
                for ans in raw_answers:
                    if isinstance(ans, str):
                        processed_answers.append({
                            'id': next(answer_id_iter),
                            'answer': ans,
                        })
                    elif isinstance(ans, dict):
                        ans_copy = dict(ans)
                        if 'id' not in ans_copy:
                            ans_copy['id'] = next(answer_id_iter)
                        processed_answers.append(ans_copy)
                processed_q['answers'] = processed_answers

            for key in ['allow_freeform', 'allow_multiple', 'require_image',
                        'image_max', 'image_types', 'category']:
                if key in q_def:
                    processed_q[key] = q_def[key]

            processed_questions.append(processed_q)

        defaults = template_defaults or {}
        template = {
            'allow_freeform': defaults.get('allow_freeform', False),
            'allow_multiple': defaults.get('allow_multiple', False),
            'require_image': defaults.get('require_image', False),
            'image_max': defaults.get('image_max', 5),
            'image_types': defaults.get('image_types', ['jpg', 'png', 'webp', 'pdf']),
        }

        doc_refs = refs or {}
        keywords = doc_refs.get('keywords', [])
        if 'qa_template' not in keywords:
            keywords.append('qa_template')
        doc_refs['keywords'] = keywords

        doc = Document.objects.create(
            name=name,
            description=description,
            body=body,
            status='published',
            config={
                'template': template,
                'questions': processed_questions,
            },
            refs=doc_refs,
        )

        logger.info(f"Created question group '{name}' (doc id={doc.id}) with {len(questions)} questions")
        return doc

    def get_question_template(self, name: str) -> Document:
        """Fetch a QA template Document by name.

        Args:
            name: The document name

        Returns:
            Document: The matching template

        Raises:
            ObjectDoesNotExist: If no matching Document exists
        """
        try:
            return Document.objects.get(
                name=name,
                status='published',
                refs__keywords__contains=['qa_template'],
            )
        except Document.DoesNotExist:
            raise ObjectDoesNotExist(f"QA template '{name}' not found or not published.")

    # -----------------------------------------------------------------
    # Apply templates to parent records
    # -----------------------------------------------------------------

    @db_transaction.atomic
    def apply_questions(
        self,
        document_name: Optional[str] = None,
        parent_model: str = '',
        parent_id: int = 0,
        user=None,
        contact_data: Optional[Dict[str, Any]] = None,
        document_id: Optional[int] = None,
    ) -> List[QuestionAnswer]:
        """Apply a question template to a parent record.

        Creates QuestionAnswer records for each question in the template.
        Skips questions that already have answers for this parent.

        Args:
            document_name: Name of the template Document
            parent_model: Model name of the parent (e.g., 'item', 'project')
            parent_id: ID of the parent record
            user: Optional Django user for audit
            contact_data: Optional dict with 'id' and 'attention' for answered_by
            document_id: Optional Document ID for direct lookup

        Returns:
            List of QuestionAnswer records (both new and existing)
        """
        if not document_name and not document_id:
            raise ValidationError("document_name or document_id is required")
        if not parent_model:
            raise ValidationError("parent_model is required")
        if not parent_id:
            raise ValidationError("parent_id is required")

        if document_id:
            try:
                template_doc = Document.objects.get(
                    pk=document_id,
                    status='published',
                    refs__keywords__contains=['qa_template'],
                )
            except Document.DoesNotExist:
                raise ObjectDoesNotExist(f"QA template document id={document_id} not found or not published.")
        else:
            template_doc = self.get_question_template(document_name)

        template_data = template_doc.config or {}
        questions = template_data.get('questions', [])
        template_defaults = template_data.get('template', {})

        if not questions:
            logger.warning(f"Template '{template_doc.name}' has no questions")
            return []

        existing_qs = QuestionAnswer.objects.filter(
            parent_model=parent_model,
            parent_id=parent_id,
            document_id=template_doc.id,
        )
        existing = {qa.question_id: qa for qa in existing_qs}

        created_records: List[QuestionAnswer] = []

        for idx, q_def in enumerate(questions):
            question_id = q_def.get('id')

            if question_id in existing:
                created_records.append(existing[question_id])
                continue

            effective_options = {
                'allow_freeform': q_def.get('allow_freeform', template_defaults.get('allow_freeform', False)),
                'allow_multiple': q_def.get('allow_multiple', template_defaults.get('allow_multiple', False)),
                'require_image': q_def.get('require_image', template_defaults.get('require_image', False)),
                'image_max': q_def.get('image_max', template_defaults.get('image_max', 5)),
                'image_types': q_def.get('image_types', template_defaults.get('image_types', ['jpg', 'png', 'webp'])),
            }

            metadata = {
                'options': effective_options,
                'answers': q_def.get('answers', []),
            }

            qa_record = QuestionAnswer(
                question=q_def.get('question', ''),
                answer=None,
                document=template_doc,
                question_id=question_id,
                answer_id=None,
                parent_model=parent_model,
                parent_id=parent_id,
                status='open',
                sequence=idx + 1,
                metadata=metadata,
            )

            if contact_data:
                qa_record.set_answered_by(contact_data)

            qa_record.save()
            created_records.append(qa_record)
            logger.debug(f"Created QA record {qa_record.id} for question_id={question_id}")

        logger.info(f"Applied {len(created_records)} questions from '{template_doc.name}' to {parent_model}:{parent_id}")
        return created_records

    # -----------------------------------------------------------------
    # Answer management
    # -----------------------------------------------------------------

    def get_questions_for_parent(
        self,
        parent_model: str,
        parent_id: int,
        template_name: Optional[str] = None
    ) -> List[QuestionAnswer]:
        """Fetch all QA records for a parent, optionally filtered by template.

        Args:
            parent_model: Model name of the parent
            parent_id: ID of the parent record
            template_name: Optional template Document name to filter by

        Returns:
            List of QuestionAnswer records ordered by sequence
        """
        qs = QuestionAnswer.objects.filter(
            parent_model=parent_model,
            parent_id=parent_id
        ).order_by('sequence')

        if template_name:
            template = Document.objects.filter(
                name=template_name,
                status='published',
                refs__keywords__contains=['qa_template'],
            ).first()
            if template:
                qs = qs.filter(document_id=template.id)

        return list(qs)

    def save_answer(
        self,
        qa_id: int,
        answer: Optional[str] = None,
        answer_ids: Optional[List[int]] = None,
        contact_data: Optional[Dict[str, Any]] = None
    ) -> QuestionAnswer:
        """Save an answer for a QA record.

        Args:
            qa_id: ID of the QuestionAnswer record
            answer: Text answer (for freeform or single select)
            answer_ids: List of selected answer IDs (for multiple select)
            contact_data: Optional dict with 'id' and 'attention' for answered_by

        Returns:
            Updated QuestionAnswer record
        """
        qa = QuestionAnswer.objects.get(pk=qa_id)

        if answer is not None:
            qa.answer = answer

        if answer_ids:
            qa.metadata = qa.metadata or {}
            qa.metadata['selected_answer_ids'] = answer_ids

        if contact_data:
            qa.set_answered_by(contact_data)

        qa.status = 'answered'
        qa.save()

        return qa

    def list_available_groups(self) -> List[Dict[str, Any]]:
        """List all available question templates.

        Returns:
            List of dicts with template info: id, name, description,
            question_count, standards, spec_refs
        """
        docs = Document.objects.filter(
            status='published',
            refs__keywords__contains=['qa_template'],
        ).values('id', 'name', 'description', 'config', 'refs')

        result = []
        for d in docs:
            config = d.get('config', {}) or {}
            refs = d.get('refs', {}) or {}
            questions = config.get('questions', [])
            result.append({
                'id': d['id'],
                'name': d['name'],
                'description': d.get('description', ''),
                'question_count': len(questions),
                'standards': refs.get('standards', []),
                'spec_refs': refs.get('spec_refs', []),
            })

        return result
