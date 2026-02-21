"""
QA Service - Manage question templates and apply them to parent records.

This service handles two main workflows:

1. **Creating Question Templates** (qa_questions Settings):
   - Use `create_question_group()` to create a new template with auto-assigned IDs
   - The qa_counters singleton tracks unique question/answer IDs across all templates
   - IDs are globally unique for data analysis across question groups

2. **Applying Templates to Records**:
   - Use `apply_questions()` to create QuestionAnswer records for a parent
   - `question_id` references Setting.data.questions[].id
   - `answer_id` is set when user responds, referencing Setting.data.questions[].answers[].id

Usage:
    from apps.docs.services.qa_service import QAService
    
    service = QAService()
    
    # Create a new question template
    setting = service.create_question_group(
        name='Inspection Checklist',
        questions=[
            {'question': 'Is wiring intact?', 'answers': ['Yes', 'No', 'N/A']},
            {'question': 'Voltage reading?', 'allow_freeform': True},
        ],
        parent_model='project'
    )
    
    # Apply template to a record
    qa_records = service.apply_questions(
        question_group='Inspection Checklist',
        parent_model='project',
        parent_id=123,
        user=request.user
    )
"""

from typing import List, Dict, Any, Optional
import logging

from django.db import transaction as db_transaction
from django.db.models import F
from django.core.exceptions import ValidationError, ObjectDoesNotExist

from apps.core.models import Setting
from apps.docs.models import QuestionAnswer

logger = logging.getLogger(__name__)


class QAService:
    """Service for applying question templates to parent records."""
    
    def __init__(self):
        pass
    
    def get_counters_singleton(self) -> Setting:
        """Fetch the qa_counters singleton Setting record.
        
        Returns:
            Setting: The qa_counters singleton
            
        Raises:
            ObjectDoesNotExist: If no qa_counters record exists
        """
        try:
            return Setting.objects.get(purpose='qa_counters')
        except Setting.DoesNotExist:
            raise ObjectDoesNotExist("qa_counters singleton not found. Run load_qa_settings command.")
    
    def get_or_create_counters(self) -> Setting:
        """Get or create the qa_counters singleton.
        
        Returns:
            Setting: The qa_counters singleton (created if missing)
        """
        counters, created = Setting.objects.get_or_create(
            purpose='qa_counters',
            defaults={
                'name': 'counters',
                'parent_model': 'question_answer',
                'role': 'all',
                'data': {'question_max': 0, 'answer_max': 0},
                'is_active': True,
            }
        )
        if created:
            logger.info("Created qa_counters singleton")
        return counters
    
    @db_transaction.atomic
    def allocate_question_ids(self, count: int) -> List[int]:
        """Allocate the next N unique question IDs.
        
        Args:
            count: Number of IDs to allocate
            
        Returns:
            List of unique question IDs
        """
        counters = Setting.objects.select_for_update().get(purpose='qa_counters')
        data = counters.data or {}
        current_max = data.get('question_max', 0)
        
        new_ids = list(range(current_max + 1, current_max + count + 1))
        
        data['question_max'] = current_max + count
        counters.data = data
        counters.save(update_fields=['data'])
        
        logger.info(f"Allocated question IDs {new_ids[0]}-{new_ids[-1]}")
        return new_ids
    
    @db_transaction.atomic
    def allocate_answer_ids(self, count: int) -> List[int]:
        """Allocate the next N unique answer choice IDs.
        
        Args:
            count: Number of IDs to allocate
            
        Returns:
            List of unique answer IDs
        """
        counters = Setting.objects.select_for_update().get(purpose='qa_counters')
        data = counters.data or {}
        current_max = data.get('answer_max', 0)
        
        new_ids = list(range(current_max + 1, current_max + count + 1))
        
        data['answer_max'] = current_max + count
        counters.data = data
        counters.save(update_fields=['data'])
        
        logger.info(f"Allocated answer IDs {new_ids[0]}-{new_ids[-1]}")
        return new_ids

    @db_transaction.atomic
    def create_question_group(
        self,
        name: str,
        questions: List[Dict[str, Any]],
        parent_model: Optional[str] = None,
        role: str = 'all',
        template_defaults: Optional[Dict[str, Any]] = None
    ) -> Setting:
        """Create a new question group (qa_questions Setting) with auto-assigned IDs.
        
        Questions and their answer choices are assigned globally unique IDs
        from the qa_counters singleton.
        
        Args:
            name: Name of the question group (e.g., 'Inspection Checklist')
            questions: List of question definitions, each with:
                - question: str (required) - The question text
                - answers: List[str] (optional) - Answer choice texts
                - allow_freeform: bool (optional)
                - allow_multiple: bool (optional)
                - require_image: bool (optional)
            parent_model: Target model (e.g., 'order', 'project') or None for all
            role: User role restriction (default 'all')
            template_defaults: Default options for all questions
            
        Returns:
            Setting: The created qa_questions Setting
            
        Example:
            setting = service.create_question_group(
                name='Installation QA',
                questions=[
                    {'question': 'Wiring OK?', 'answers': ['Yes', 'No', 'N/A']},
                    {'question': 'Notes', 'allow_freeform': True},
                ],
                parent_model='project'
            )
        """
        # Ensure counters exist
        self.get_or_create_counters()
        
        # Count total answer choices needed
        total_answers = sum(
            len(q.get('answers', [])) if isinstance(q.get('answers', []), list) else 0
            for q in questions
        )
        
        # Allocate IDs
        question_ids = self.allocate_question_ids(len(questions))
        answer_ids = self.allocate_answer_ids(total_answers) if total_answers > 0 else []
        
        # Build question definitions with assigned IDs
        answer_id_iter = iter(answer_ids)
        processed_questions = []
        
        for q_def, q_id in zip(questions, question_ids):
            processed_q = {
                'id': q_id,
                'question': q_def['question'],
            }
            
            # Process answer choices
            raw_answers = q_def.get('answers', [])
            if raw_answers:
                processed_answers = []
                for ans in raw_answers:
                    if isinstance(ans, str):
                        # Simple string answer - assign ID
                        processed_answers.append({
                            'id': next(answer_id_iter),
                            'answer': ans,
                        })
                    elif isinstance(ans, dict):
                        # Already a dict - assign ID if missing
                        ans_copy = dict(ans)
                        if 'id' not in ans_copy:
                            ans_copy['id'] = next(answer_id_iter)
                        processed_answers.append(ans_copy)
                processed_q['answers'] = processed_answers
            
            # Copy optional overrides
            for key in ['allow_freeform', 'allow_multiple', 'require_image', 'image_max', 'image_types']:
                if key in q_def:
                    processed_q[key] = q_def[key]
            
            processed_questions.append(processed_q)
        
        # Build template defaults
        defaults = template_defaults or {}
        template = {
            'allow_freeform': defaults.get('allow_freeform', False),
            'allow_multiple': defaults.get('allow_multiple', False),
            'require_image': defaults.get('require_image', False),
            'image_max': defaults.get('image_max', 5),
            'image_types': defaults.get('image_types', ['jpg', 'png', 'webp', 'pdf']),
        }
        
        # Create Setting record
        setting = Setting.objects.create(
            purpose='qa_questions',
            name=name,
            parent_model=parent_model,
            role=role,
            data={
                'template': template,
                'questions': processed_questions,
            },
            is_active=True,
        )
        
        logger.info(f"Created question group '{name}' with {len(questions)} questions")
        return setting
    
    def get_question_template(self, group_name: str) -> Setting:
        """Fetch the qa_questions Setting for a given group.
        
        Args:
            group_name: The name of the question group (e.g., 'Planning')
            
        Returns:
            Setting: The qa_questions Setting record
            
        Raises:
            ObjectDoesNotExist: If no matching qa_questions record exists
        """
        try:
            return Setting.objects.get(
                purpose='qa_questions',
                name=group_name,
                is_active=True
            )
        except Setting.DoesNotExist:
            raise ObjectDoesNotExist(f"Question group '{group_name}' not found or inactive.")
    
    def get_existing_answers(self, parent_model: str, parent_id: int, setting_id: int) -> Dict[int, QuestionAnswer]:
        """Fetch existing QA records for a parent+group combo.
        
        Returns:
            Dict mapping question_id to QuestionAnswer record
        """
        qs = QuestionAnswer.objects.filter(
            parent_model=parent_model,
            parent_id=parent_id,
            setting_id=setting_id
        )
        return {qa.question_id: qa for qa in qs}
    
    @db_transaction.atomic
    def apply_questions(
        self,
        question_group: Optional[str],
        parent_model: str,
        parent_id: int,
        user=None,
        contact_data: Optional[Dict[str, Any]] = None,
        setting_id: Optional[int] = None
    ) -> List[QuestionAnswer]:
        """Apply a question template to a parent record.
        
        Creates QuestionAnswer records for each question in the template.
        Skips questions that already have answers for this parent.
        
        Args:
            question_group: Name of the question group (e.g., 'Planning')
            parent_model: Model name of the parent (e.g., 'order', 'customer')
            parent_id: ID of the parent record
            user: Optional Django user for audit
            contact_data: Optional dict with 'id' and 'attention' for answered_by
            setting_id: Optional Setting ID for direct lookup (preferred over name)
            
        Returns:
            List of QuestionAnswer records (both new and existing)
            
        Raises:
            ObjectDoesNotExist: If question group or counters not found
            ValidationError: If required parameters missing
        """
        if not question_group and not setting_id:
            raise ValidationError("question_group or setting_id is required")
        if not parent_model:
            raise ValidationError("parent_model is required")
        if not parent_id:
            raise ValidationError("parent_id is required")
        
        # 1. Fetch question template (prefer setting_id if provided)
        if setting_id:
            try:
                template_setting = Setting.objects.get(pk=setting_id, purpose='qa_questions', is_active=True)
            except Setting.DoesNotExist:
                raise ObjectDoesNotExist(f"Question group with setting_id={setting_id} not found or inactive.")
        else:
            template_setting = self.get_question_template(question_group)
        template_data = template_setting.data or {}
        questions = template_data.get('questions', [])
        template_defaults = template_data.get('template', {})
        
        if not questions:
            logger.warning(f"Question group '{template_setting.name}' has no questions")
            return []
        
        # 2. Check for existing answers
        existing = self.get_existing_answers(parent_model, parent_id, template_setting.id)
        
        # 3. Create new QA records for questions not yet applied
        created_records = []
        
        for idx, q_def in enumerate(questions):
            question_id = q_def.get('id')
            
            # Skip if already exists
            if question_id in existing:
                created_records.append(existing[question_id])
                continue
            
            # Merge template defaults with question overrides
            effective_options = {
                'allow_freeform': q_def.get('allow_freeform', template_defaults.get('allow_freeform', False)),
                'allow_multiple': q_def.get('allow_multiple', template_defaults.get('allow_multiple', False)),
                'require_image': q_def.get('require_image', template_defaults.get('require_image', False)),
                'image_max': q_def.get('image_max', template_defaults.get('image_max', 5)),
                'image_types': q_def.get('image_types', template_defaults.get('image_types', ['jpg', 'png', 'webp'])),
            }
            
            # Build metadata - copy available answer choices from Setting for data analysis
            metadata = {
                'options': effective_options,
                'answers': q_def.get('answers', []),  # Store available choices from Setting
            }
            
            qa_record = QuestionAnswer(
                question=q_def.get('question', ''),
                answer=None,  # No answer yet - set when user responds
                setting=template_setting,
                question_id=question_id,  # ID of question from Setting.data.questions[]
                answer_id=None,  # ID of selected answer from Setting - set when user responds
                parent_model=parent_model,
                parent_id=parent_id,
                status='open',
                sequence=idx + 1,
                metadata=metadata,
            )
            
            # Set answered_by if contact provided
            if contact_data:
                qa_record.set_answered_by(contact_data)
            
            qa_record.save()
            created_records.append(qa_record)
            logger.debug(f"Created QA record {qa_record.id} for question_id={question_id}")
        
        logger.info(f"Applied {len(created_records)} questions from '{template_setting.name}' to {parent_model}:{parent_id}")
        return created_records
    
    def get_questions_for_parent(
        self,
        parent_model: str,
        parent_id: int,
        question_group: Optional[str] = None
    ) -> List[QuestionAnswer]:
        """Fetch all QA records for a parent, optionally filtered by group.
        
        Args:
            parent_model: Model name of the parent
            parent_id: ID of the parent record
            question_group: Optional group name to filter by
            
        Returns:
            List of QuestionAnswer records ordered by sequence
        """
        qs = QuestionAnswer.objects.filter(
            parent_model=parent_model,
            parent_id=parent_id
        ).order_by('sequence')
        
        if question_group:
            template = Setting.objects.filter(
                purpose='qa_questions',
                name=question_group,
                is_active=True
            ).first()
            if template:
                qs = qs.filter(setting_id=template.id)
        
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
            # Store multiple selections in metadata
            qa.metadata = qa.metadata or {}
            qa.metadata['selected_answer_ids'] = answer_ids
        
        if contact_data:
            qa.set_answered_by(contact_data)
        
        qa.status = 'answered'
        qa.save()
        
        return qa
    
    def list_available_groups(self) -> List[Dict[str, Any]]:
        """List all available question groups.
        
        Returns:
            List of dicts with group info: name, question_count, template options
        """
        groups = Setting.objects.filter(
            purpose='qa_questions',
            is_active=True
        ).values('id', 'name', 'data')
        
        result = []
        for g in groups:
            data = g.get('data', {}) or {}
            questions = data.get('questions', [])
            template = data.get('template', {})
            result.append({
                'id': g['id'],
                'name': g['name'],
                'question_count': len(questions),
                'template': template,
            })
        
        return result
