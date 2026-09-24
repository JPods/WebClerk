from django.db import models
import logging

from common.models import BaseModel
from apps.core.choices import ACTION_DIFFICULTY_LEVELS, ACTION_KANBAN_COLUMNS, ACTION_TYPE_CHOICES
from apps.core.services.record_keywords import build_keywords_for_record

console_logger = logging.getLogger('console')

class Action(BaseModel):
    # Parent-child relationship
    parent_action = models.ForeignKey('self', to_field='uuid', related_name='children', null=True, blank=True, on_delete=models.CASCADE, db_column='action_id')
    
    # Multilingual action title — field name matches db column name exactly
    # Previously named 'task' to avoid collision with model name, but that created
    # a translation cost. The schema should be transparent: action.action.en
    action = models.JSONField(default=dict, blank=True, null=True, db_column='action')
    description = models.JSONField(default=dict, blank=True, null=True)

       # Assigned users (many-to-many like, via JSON)
    assigned_to = models.JSONField(blank=True, null=True)
    contact_id  = models.BigIntegerField(default=0, db_index=True)
    
    # Supported languages for this task
    languages = models.JSONField(default=list, blank=True, null=True)

    # Project information
    project_name = models.CharField(max_length=255, blank=True, null=True)
    project_id = models.BigIntegerField(default=0, db_index=True)
    project_ida = models.CharField(max_length=255, blank=True, null=True)

    # Kanban board and workflow management
    sequence = models.PositiveIntegerField(default=0)
    kanban_column = models.CharField(max_length=50, choices=ACTION_KANBAN_COLUMNS, default='Backlog')
    action_type = models.CharField(max_length=50, choices=ACTION_TYPE_CHOICES, default='', blank=True,
        db_index=True, help_text="Type of selling action: call, email, visit, demo, etc.")
    impact = models.JSONField(default=dict, blank=True, null=True,
        help_text=(
            "Impact — not precision, but retrospection. "
            "predicted: waffly 1-5 gut feel at time of action. "
            "actual: waffly 1-5 looking back at what happened. "
            "The gap between them is the learning signal. "
            "refs: {transactions: [{model, id, ida, value}], "
            "explanation: why the gap exists}. "
            "Alice and users both contribute to defining actual."
        ))
    priority = models.PositiveIntegerField(default=1)
    difficulty = models.PositiveIntegerField(choices=ACTION_DIFFICULTY_LEVELS, default=4)
    # status inherited from BaseModel
    percent_complete = models.PositiveIntegerField(default=0)
    #set value between 0-100 based on difficulty and percent_complete
    burndown = models.SmallIntegerField(default=0)
    # Date fields with detailed meta info
    # dt_created is inherited from BaseModel/CoreModel
    dt_start = models.BigIntegerField(blank=True, null=True)
    dt_deadline = models.BigIntegerField(blank=True, null=True)
    dt_expected = models.BigIntegerField(blank=True, null=True)
    dt_completed = models.BigIntegerField(blank=True, null=True)
    dt_updated = models.BigIntegerField(default=0, db_index=True)
    #days
    duration = models.IntegerField(blank=True, null=True)
    
    # Original planned dates for baseline comparison
    dt_start_original = models.BigIntegerField(blank=True, null=True)
    dt_end_original = models.BigIntegerField(blank=True, null=True)

    # Audit info: who created / updated etc.
    created_by = models.JSONField(blank=True, null=True)
    start_by = models.JSONField(blank=True, null=True)
    deadline_by = models.JSONField(blank=True, null=True)
    expected_by = models.JSONField(blank=True, null=True)
    completed_by = models.JSONField(blank=True, null=True)
    updated_by = models.JSONField(blank=True, null=True)
    end_by = models.JSONField(blank=True, null=True)

 

    # Linkage or weighting to other systems/tasks
    linkage = models.PositiveIntegerField(default=0)

    # Additional project data (can store child names, meta, or history)
    project_metadata = models.JSONField(blank=True, null=True)

    # Structured retrospection — the learning record for this action
    # Fields: intent, points_for, points_against, harms, benefits, risk,
    #         help_procedure, alternatives, who_affected, confidence (1-10),
    #         applies_to, expires_when, known_unknowns, unknown_unknowns,
    #         grade (A-F), grade_note, tfts
    # Intent and tfts are always required. Everything else enriches when available.
    retrospection = models.JSONField(default=dict, blank=True, null=True,
        help_text="Structured learning: intent, points for/against, harms, benefits, risk, unknowns, tfts")

    class Meta:
        db_table = 'actions'
        verbose_name = "Action"
        verbose_name_plural = "Actions"

    def __str__(self):
        action_val = self.action or {}
        if isinstance(action_val, str):
            action_text = action_val
        elif isinstance(action_val, dict):
            action_text = action_val.get('en') or action_val.get('bn') or action_val.get('ar') or 'Untitled'
        else:
            action_text = str(action_val) if action_val else 'Untitled'
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
    def _normalize_roster(self):
        """Bring assigned_to to the roster shape and resolve each person.

        assigned_to = [{id, org_id, name, email, role}], first entry responsible
        (common.schemas.action_aspects.AssignedPerson). A person is resolved by
        id, then exact email, then a full name that matches exactly one contact.
        No partial-name guessing: with customers and vendors reading actions, a
        wrong match shows a record to the wrong organisation. An unresolved
        person keeps the name given and no id.
        """
        from apps.core.models import Contact
        from common.schemas.action_aspects import AssignedPerson

        value = self.assigned_to
        if not value:
            self.assigned_to = []
            return
        if isinstance(value, dict):          # legacy {en: name}
            value = [value.get('en', '')]
        if not isinstance(value, list):
            raise ValueError('assigned_to must be a list of people')

        roster = []
        for entry in value:
            person = {'name': entry} if isinstance(entry, str) else dict(entry or {})
            contact = None
            if person.get('id'):
                contact = Contact.objects.filter(id=person['id']).first()
            if contact is None and person.get('email'):
                contact = Contact.objects.filter(email__iexact=person['email'].strip()).first()
            if contact is None and person.get('name'):
                parts = person['name'].split()
                if len(parts) >= 2:
                    hits = Contact.objects.filter(
                        name_first__iexact=parts[0], name_last__iexact=' '.join(parts[1:]))[:2]
                    contact = hits[0] if len(hits) == 1 else None
            if contact is not None:
                person.update({
                    'id': contact.id,
                    'org_id': contact.customer_id or contact.vendor_id,
                    'name': ' '.join(x for x in (contact.name_first, contact.name_last) if x)
                            or person.get('name', ''),
                    'email': contact.email or '',
                    'role': person.get('role') or contact.role or '',
                })
            roster.append(AssignedPerson.model_validate(person).model_dump())
        self.assigned_to = roster

    def save(self, *args, **kwargs):
        # assigned_to is a roster; contact_id is its responsible (first) person.
        self._normalize_roster()
        if self.assigned_to and self.assigned_to[0].get('id'):
            self.contact_id = self.assigned_to[0]['id']
        
        # Duration-based date calculation
        # Duration is in days, dates are in milliseconds
        from django.utils import timezone
        one_day_ms = 24 * 60 * 60 * 1000
        
        # Helper to check if a date value is "empty" (None or 0)
        def is_empty(val):
            return val is None or val == 0
        
        # For new actions with a project, set dt_start from project.dt_kanban, dt_deadline = dt_start + 7 days
        if not self.pk and self.project_id and self.project_id > 0:
            from apps.transactions.models import Project
            project = Project.objects.filter(id=self.project_id).first()
            if project and project.dt_kanban:
                # Convert datetime to milliseconds
                kanban_ts = int(project.dt_kanban.timestamp() * 1000)
                if is_empty(self.dt_start):
                    self.dt_start = kanban_ts
                if is_empty(self.dt_deadline):
                    self.dt_deadline = self.dt_start + (7 * one_day_ms)
        
        # Only apply logic if duration is set and positive
        if self.duration and self.duration > 0:
            duration_ms = self.duration * one_day_ms
            
            if is_empty(self.dt_start) and is_empty(self.dt_deadline):
                # Both missing: set dt_start to today, dt_deadline = dt_start + duration
                now_ms = int(timezone.now().timestamp() * 1000)
                self.dt_start = now_ms
                self.dt_deadline = now_ms + duration_ms
            elif is_empty(self.dt_start) and not is_empty(self.dt_deadline):
                # dt_start missing but dt_deadline set: dt_start = dt_deadline - duration
                self.dt_start = self.dt_deadline - duration_ms
            elif not is_empty(self.dt_start):
                # dt_start is set: dt_deadline = dt_start + duration
                self.dt_deadline = self.dt_start + duration_ms
        
        # Enforce parent dependency constraint: dt_start >= max(parent.dt_deadline)
        # If this action has parents in refs.parents[], ensure we don't start before they finish
        refs = getattr(self, 'refs', {}) or {}
        if isinstance(refs, dict):
            parent_ids = refs.get('parents', [])
            if parent_ids and isinstance(parent_ids, list):
                from apps.core.models import Action as ActionModel
                latest_parent_deadline = None
                
                for parent_id in parent_ids:
                    try:
                        parent_id_int = int(parent_id)
                        parent_action = ActionModel.objects.filter(id=parent_id_int).first()
                        if parent_action:
                            # Use dt_deadline first, fall back to dt_start + duration
                            parent_end = parent_action.dt_deadline
                            if not parent_end and parent_action.dt_start and parent_action.duration:
                                parent_end = parent_action.dt_start + (parent_action.duration * one_day_ms)
                            
                            if parent_end and (latest_parent_deadline is None or parent_end > latest_parent_deadline):
                                latest_parent_deadline = parent_end
                    except (ValueError, TypeError):
                        continue
                
                # If we have a constraint, enforce dt_start >= latest_parent_deadline
                if latest_parent_deadline is not None:
                    if is_empty(self.dt_start) or self.dt_start < latest_parent_deadline:
                        self.dt_start = latest_parent_deadline
                        # Recalculate dt_deadline if duration is set
                        if self.duration and self.duration > 0:
                            self.dt_deadline = self.dt_start + (self.duration * one_day_ms)
        
        # compute changed_fields before save
        changed_fields = []
        if self.pk:
            for f in self._meta.fields:
                name = f.name
                if name in {'dt_modified', 'version'}:
                    continue
                # Use f.attname to compare raw DB column values (e.g. contact_id)
                # to avoid triggering lazy-load queries on FK fields.
                attr = f.attname
                old = self._original_state.get(attr)
                new = getattr(self, attr)
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
                    # Defensive: coerce contact_id to int when possible (e.g., '129-assignee-0' -> 129)
                    try:
                        if isinstance(contact_id, str):
                            import re
                            m = re.search(r"(\d+)", contact_id)
                            if m:
                                contact_id_int = int(m.group(1))
                            else:
                                contact_id_int = None
                        else:
                            contact_id_int = int(contact_id) if contact_id is not None else None
                    except Exception:
                        contact_id_int = None
                    if contact_id_int is not None:
                        contact = Contact.objects.filter(id=contact_id_int).first()
                        if contact:
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