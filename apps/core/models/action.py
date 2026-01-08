from django.db import models

from common.models import BaseModel
from apps.core.choices import ACTION_DIFFICULTY_LEVELS, ACTION_KANBAN_COLUMNS
from apps.core.services.keywords import build_keywords_for_record

class Action(BaseModel):
    # Parent-child relationship
    action_id = models.ForeignKey('self', to_field='uuid', related_name='children', null=True, blank=True, on_delete=models.CASCADE)
    
    # Multilingual titles and descriptions
    action = models.JSONField(default=dict, blank=True, null=True)
    description = models.JSONField(default=dict, blank=True, null=True)
    
    # Supported languages for this task
    languages = models.JSONField(default=list, blank=True, null=True)

    # Project information
    project_name = models.CharField(max_length=255, blank=True, null=True)
    project_id = models.BigIntegerField(default=0, db_index=True)

    # Kanban board and workflow management
    sequence = models.PositiveIntegerField(default=0)
    kanban_column = models.CharField(max_length=50, choices=ACTION_KANBAN_COLUMNS, default='Backlog')
    priority = models.PositiveIntegerField(default=1)
    difficulty = models.PositiveIntegerField(choices=ACTION_DIFFICULTY_LEVELS, default=10)
    status = models.CharField(max_length=100, blank=True, null=True)
    percent_complete = models.PositiveIntegerField(default=0)
    #set value between 0-100 based on difficulty and percent_complete
    burndown = models.SmallIntegerField(default=0)
    # Date fields with detailed meta info
    dt_created = models.BigIntegerField(default=0, db_index=True)
    dt_updated = models.BigIntegerField(default=0, db_index=True)
    dt_expected = models.BigIntegerField(blank=True, null=True)
    dt_due = models.BigIntegerField(blank=True, null=True)
    dt_completed = models.BigIntegerField(blank=True, null=True)
    dt_start = models.BigIntegerField(blank=True, null=True)
    dt_end = models.BigIntegerField(blank=True, null=True)
    #days
    duration = models.IntegerField(blank=True, null=True)

    # Audit info: who created / updated etc.
    created_by = models.JSONField(blank=True, null=True)
    updated_by = models.JSONField(blank=True, null=True)
    expected_by = models.JSONField(blank=True, null=True)
    due_by = models.JSONField(blank=True, null=True)
    completed_by = models.JSONField(blank=True, null=True)
    start_by = models.JSONField(blank=True, null=True)
    end_by = models.JSONField(blank=True, null=True)

    # Assigned users (many-to-many like, via JSON)
    assigned_to = models.JSONField(blank=True, null=True)

    # Linkage or weighting to other systems/tasks
    linkage = models.PositiveIntegerField(default=0)

    # Additional project data (can store child names, meta, or history)
    project_metadata = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = 'actions'
        verbose_name = "Action"
        verbose_name_plural = "Actions"

    def __str__(self):
        action_dict = self.action or {}
        action_text = action_dict.get('en') or action_dict.get('bn') or action_dict.get('ar') or 'Untitled'
        return f"{action_text} ({self.kanban_column})"

    def update_keywords(self):
        """Update keywords for this action record."""   
        # Clear previous keywords and generate new ones
        refs = getattr(self, 'refs', {}) or {}
        if not isinstance(refs, dict):
            refs = {}
        refs['keywords'] = []
        self.refs = refs
        
        # Use the actual model name from class name
        model_name = self.__class__.__name__.lower()
        keywords = build_keywords_for_record(model_name, self.id)
        
        # Store keywords in refs.keywords
        refs['keywords'] = keywords
        self.refs = refs
        
        # Note: Save is handled by the calling thread in save_view.py
    def save(self, *args, **kwargs):
        # compute changed_fields before save
        changed_fields = []
        if self.pk:
            for f in self._meta.fields:
                name = f.name
                if name in {'dt_modified', 'version'}:
                    continue
                old = self._original_state.get(name)
                new = getattr(self, name)
                if old != new:
                    changed_fields.append(name)
        # set the _by based on changed_fields
        from django.utils import timezone
        now_ms = int(timezone.now().timestamp() * 1000)
        contact_id = None
        contact_email = None
        if self.assigned_to and isinstance(self.assigned_to, list) and self.assigned_to:
            first_assigned = self.assigned_to[0]
            if isinstance(first_assigned, dict):
                contact_id = first_assigned.get('id')
                contact_email = first_assigned.get('email')
            else:
                contact_id = first_assigned
            if contact_id and not contact_email:
                try:
                    from apps.core.models import Contact
                    contact = Contact.objects.get(id=contact_id)
                    contact_email = contact.email
                except Contact.DoesNotExist:
                    pass
        if not contact_id:
            contact_id = 1
            contact_email = 'system@example.com'
        for field in changed_fields:
            if field == 'dt_due':
                due_by = self.due_by or []
                due_by.append({'id': contact_id, 'email': contact_email, 'dt': now_ms})
                self.due_by = due_by
            elif field == 'dt_end':
                end_by = self.end_by or []
                end_by.append({'id': contact_id, 'email': contact_email, 'dt': now_ms})
                self.end_by = end_by
        if changed_fields:
            updated_by = self.updated_by or []
            updated_by.append({'id': contact_id, 'email': contact_email, 'dt': now_ms})
            self.updated_by = updated_by
        if not self.pk:
            created_by = self.created_by or []
            created_by.append({'id': contact_id, 'email': contact_email, 'dt': now_ms})
            self.created_by = created_by
        super().save(*args, **kwargs)