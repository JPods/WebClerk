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

       # Assigned users (many-to-many like, via JSON)
    assigned_to = models.JSONField(blank=True, null=True)
    contact_id  = models.BigIntegerField(default=0, db_index=True)
    
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
    dt_start = models.BigIntegerField(blank=True, null=True)
    dt_deadline = models.BigIntegerField(blank=True, null=True)
    dt_expected = models.BigIntegerField(blank=True, null=True)
    dt_completed = models.BigIntegerField(blank=True, null=True)
    dt_updated = models.BigIntegerField(default=0, db_index=True)
    #days
    duration = models.IntegerField(blank=True, null=True)

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

    class Meta:
        db_table = 'actions'
        verbose_name = "Action"
        verbose_name_plural = "Actions"

    def __str__(self):
        action_dict = self.action or {}
        action_text = action_dict.get('en') or action_dict.get('bn') or action_dict.get('ar') or 'Untitled'
        return f"{action_text} ({self.kanban_column})"

    def pre_save_hook(self, data, is_update=False, context=None):
        """Normalize common alias fields from clients into canonical columns.

        - action_<lang> / description_<lang> -> action / description JSON
        - progress -> percent_complete
        - kanban_column_id -> kanban_column (title-cased)
        - merges derived languages into languages list
        """
        if not isinstance(data, dict):
            return None

        def _extract_value(raw):
            if isinstance(raw, dict) and 'value' in raw:
                return raw.get('value')
            return raw

        title_by_lang = {}
        desc_by_lang = {}
        derived_langs: set[str] = set()

        for key in list(data.keys()):
            if not isinstance(key, str):
                continue
            if key.startswith('action_'):
                lang = key.split('_', 1)[1] or 'en'
                val = _extract_value(data.pop(key))
                if val not in (None, ''):
                    title_by_lang[lang] = val
                    derived_langs.add(lang)
            elif key.startswith('description_'):
                lang = key.split('_', 1)[1] or 'en'
                val = _extract_value(data.pop(key))
                if val not in (None, ''):
                    desc_by_lang[lang] = val
                    derived_langs.add(lang)

        if title_by_lang:
            current_action: dict = {}
            raw_action = data.get('action')
            if isinstance(raw_action, dict) and 'value' in raw_action and isinstance(raw_action.get('value'), dict):
                current_action = raw_action.get('value') or {}
            elif isinstance(self.action, dict):
                current_action = self.action or {}
            merged_action = {**current_action, **title_by_lang}
            data['action'] = {'mode': 'update', 'value': merged_action}

        if desc_by_lang:
            current_desc: dict = {}
            raw_desc = data.get('description')
            if isinstance(raw_desc, dict) and 'value' in raw_desc and isinstance(raw_desc.get('value'), dict):
                current_desc = raw_desc.get('value') or {}
            elif isinstance(self.description, dict):
                current_desc = self.description or {}
            merged_desc = {**current_desc, **desc_by_lang}
            data['description'] = {'mode': 'update', 'value': merged_desc}

        progress_raw = data.pop('progress', None)
        progress_val = _extract_value(progress_raw)
        try:
            progress_int = int(progress_val) if progress_val not in (None, '') else None
        except (TypeError, ValueError):
            progress_int = None
        if progress_int is not None and 'percent_complete' not in data:
            data['percent_complete'] = {'mode': 'update', 'value': progress_int}

        column_raw = data.pop('kanban_column_id', None)
        column_val = _extract_value(column_raw)
        if column_val and 'kanban_column' not in data:
            col_str = str(column_val)
            if col_str.startswith('column-'):
                col_str = col_str[len('column-'):]
            normalized = col_str.replace('-', ' ').strip().title()
            if normalized:
                data['kanban_column'] = {'mode': 'update', 'value': normalized}

        languages_field = data.get('languages')
        existing_langs: set[str] = set()
        if isinstance(languages_field, dict) and isinstance(languages_field.get('value'), list):
            existing_langs = {str(l).strip() for l in languages_field.get('value') if str(l).strip()}
        elif isinstance(languages_field, list):
            existing_langs = {str(l).strip() for l in languages_field if str(l).strip()}
        elif isinstance(self.languages, list):
            existing_langs = {str(l).strip() for l in self.languages if str(l).strip()}

        merged_langs = sorted((existing_langs | derived_langs) - {''})
        if derived_langs:
            data['languages'] = {'mode': 'update', 'value': merged_langs or ['en']}

        return None

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
    def _resolve_contact_from_assigned_to(self):
        """
        Resolve contact_id from assigned_to entries.
        Returns (contact_id, contact_email) tuple.
        First tries to match by id/contact_id in assigned_to, then by name against Contact.attention.
        """
        from apps.core.models import Contact
        
        if not self.assigned_to or not isinstance(self.assigned_to, list) or not self.assigned_to:
            return None, None
        
        first_assigned = self.assigned_to[0]
        if not isinstance(first_assigned, dict):
            # If it's just an id
            try:
                cid = int(first_assigned)
                contact = Contact.objects.filter(id=cid).first()
                if contact:
                    return contact.id, contact.email
            except (ValueError, TypeError):
                pass
            return None, None
        
        # Try to get id from dict
        assigned_id = first_assigned.get('id') or first_assigned.get('contact_id')
        if assigned_id:
            try:
                cid = int(assigned_id)
                contact = Contact.objects.filter(id=cid).first()
                if contact:
                    return contact.id, contact.email
            except (ValueError, TypeError):
                pass
        
        # Try to match by name against attention field
        name = first_assigned.get('name', '').strip()
        if name:
            name_lower = name.lower()
            # Exact match first
            contact = Contact.objects.filter(attention__iexact=name).first()
            if contact:
                return contact.id, contact.email
            # Try partial match (first name or last name)
            for c in Contact.objects.exclude(attention='').exclude(attention__isnull=True):
                attn_lower = (c.attention or '').lower()
                if attn_lower == name_lower:
                    return c.id, c.email
                # Check if name is part of attention (e.g., "Bill" matches "Bill James")
                if name_lower in attn_lower.split() or attn_lower.startswith(name_lower):
                    return c.id, c.email
        
        return None, None

    def save(self, *args, **kwargs):
        # Auto-populate contact_id from assigned_to if not already set or if assigned_to changed
        if self.assigned_to and (not self.contact_id or self.contact_id == 0):
            resolved_id, _ = self._resolve_contact_from_assigned_to()
            if resolved_id:
                self.contact_id = resolved_id
        
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
        
        # If assigned_to changed, re-resolve contact_id
        if 'assigned_to' in changed_fields and self.assigned_to:
            resolved_id, _ = self._resolve_contact_from_assigned_to()
            if resolved_id:
                self.contact_id = resolved_id
        
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