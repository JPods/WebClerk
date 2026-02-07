"""
QA Service - Apply question templates to parent records.

When a user selects a question group for a parent record (e.g., a sales order),
this service:
1. Fetches the qa_questions Setting template for the group
2. Atomically increments qa_counters for new answer_ids
3. Creates QuestionAnswer records for each question
4. Returns the created records

Usage:
    from apps.docs.services.qa_service import QAService
    
    service = QAService()
    qa_records = service.apply_questions(
        question_group='Planning',
        parent_type='sales_order',
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
    
    def get_existing_answers(self, parent_type: str, parent_id: int, setting_id: int) -> Dict[int, QuestionAnswer]:
        """Fetch existing QA records for a parent+group combo.
        
        Returns:
            Dict mapping question_id to QuestionAnswer record
        """
        qs = QuestionAnswer.objects.filter(
            parent_type=parent_type,
            parent_id=parent_id,
            setting_id=setting_id
        )
        return {qa.question_id: qa for qa in qs}
    
    @db_transaction.atomic
    def apply_questions(
        self,
        question_group: str,
        parent_type: str,
        parent_id: int,
        user=None,
        contact_data: Optional[Dict[str, Any]] = None
    ) -> List[QuestionAnswer]:
        """Apply a question template to a parent record.
        
        Creates QuestionAnswer records for each question in the template.
        Skips questions that already have answers for this parent.
        
        Args:
            question_group: Name of the question group (e.g., 'Planning')
            parent_type: Model name of the parent (e.g., 'sales_order')
            parent_id: ID of the parent record
            user: Optional Django user for audit
            contact_data: Optional dict with 'id' and 'attention' for answered_by
            
        Returns:
            List of QuestionAnswer records (both new and existing)
            
        Raises:
            ObjectDoesNotExist: If question group or counters not found
            ValidationError: If required parameters missing
        """
        if not question_group:
            raise ValidationError("question_group is required")
        if not parent_type:
            raise ValidationError("parent_type is required")
        if not parent_id:
            raise ValidationError("parent_id is required")
        
        # 1. Fetch question template
        template_setting = self.get_question_template(question_group)
        template_data = template_setting.data or {}
        questions = template_data.get('questions', [])
        template_defaults = template_data.get('template', {})
        
        if not questions:
            logger.warning(f"Question group '{question_group}' has no questions")
            return []
        
        # 2. Check for existing answers
        existing = self.get_existing_answers(parent_type, parent_id, template_setting.id)
        
        # 3. Fetch and lock counters for atomic increment
        counters = Setting.objects.select_for_update().get(purpose='qa_counters')
        counters_data = counters.data or {}
        answer_max = counters_data.get('answer_max', 0)
        
        # 4. Create new QA records for questions not yet applied
        created_records = []
        new_answer_id = answer_max
        
        for idx, q_def in enumerate(questions):
            question_id = q_def.get('id')
            
            # Skip if already exists
            if question_id in existing:
                created_records.append(existing[question_id])
                continue
            
            # Increment answer_id for new record
            new_answer_id += 1
            
            # Merge template defaults with question overrides
            effective_options = {
                'allow_freeform': q_def.get('allow_freeform', template_defaults.get('allow_freeform', False)),
                'allow_multiple': q_def.get('allow_multiple', template_defaults.get('allow_multiple', False)),
                'require_image': q_def.get('require_image', template_defaults.get('require_image', False)),
                'image_max': q_def.get('image_max', template_defaults.get('image_max', 5)),
                'image_types': q_def.get('image_types', template_defaults.get('image_types', ['jpg', 'png', 'webp'])),
            }
            
            # Build metadata
            metadata = {
                'options': effective_options,
                'answers': q_def.get('answers', []),  # Store available choices
            }
            
            qa_record = QuestionAnswer(
                question=q_def.get('question', ''),
                answer=None,  # No answer yet
                setting_id=template_setting,
                question_id=question_id,
                answer_id=new_answer_id,
                parent_type=parent_type,
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
        
        # 5. Update counters if we created any new records
        if new_answer_id > answer_max:
            counters.data['answer_max'] = new_answer_id
            counters.save(update_fields=['data'])
            logger.info(f"Updated qa_counters answer_max: {answer_max} -> {new_answer_id}")
        
        logger.info(f"Applied {len(created_records)} questions from '{question_group}' to {parent_type}:{parent_id}")
        return created_records
    
    def get_questions_for_parent(
        self,
        parent_type: str,
        parent_id: int,
        question_group: Optional[str] = None
    ) -> List[QuestionAnswer]:
        """Fetch all QA records for a parent, optionally filtered by group.
        
        Args:
            parent_type: Model name of the parent
            parent_id: ID of the parent record
            question_group: Optional group name to filter by
            
        Returns:
            List of QuestionAnswer records ordered by sequence
        """
        qs = QuestionAnswer.objects.filter(
            parent_type=parent_type,
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
