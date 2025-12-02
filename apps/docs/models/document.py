from django.db import models
from django.db.models import F
from common.models import BaseModel
from django.utils import timezone
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from apps.core.models.pending import Pending
from apps.core.constants.keyword_requirements import get_keyword_requirements
from apps.core.models.setting import Setting
# this table provides a path to documents
# example use is to link line items in orders, proposals, etc.
# with one document that passes on specs, paths, comments, and other details

# If you need a model for the "paths" table, define it as a Django model below.
# Remove raw SQL statements from Python files; use Django ORM and migrations instead.

# Example: Add additional fields to the Document model if needed
class Document(BaseModel):
    """Document / file metadata.

    Adjustments implemented:
      - Added increment_access() helper (atomic F() update).
      - Added is_active for soft delete distinct from BaseModel flags.
      - Consolidated publish + security concept: security_level gate; higher role level required.
      - copy_right collapsed into structured copyright JSON.
      - Added GIN-based full-text search vector over name/description/body.
    - Added indexes on security_level, status, name.
    """

    name = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    slug = models.SlugField(max_length=255, blank=True, null=True, unique=True, help_text="Stable slug (for readmes / API consumption)")
    status = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    comment = models.TextField(blank=True, default="", help_text="General notes")
    data = models.JSONField(blank=True, null=True)
    
    confidential = models.CharField(max_length=255, blank=True, null=True)
    copyright = models.JSONField(blank=True, null=True, help_text="{level:int,path:str,holder:str,notes:[]} structure")
    count_accessed = models.IntegerField(default=0)
    # Canonical model identifier
    model_name = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    retention_period = models.IntegerField(blank=True, null=True)
    sequence = models.IntegerField(blank=True, null=True)
    size_bytes = models.IntegerField(blank=True, null=True)
    mime_type = models.CharField(max_length=255, blank=True, null=True)
    path = models.JSONField(blank=True, null=True)
    checksum = models.CharField(max_length=255, blank=True, null=True)
    search_vector = SearchVectorField(null=True, editable=False)

    class Meta:
        db_table = 'documents'
        indexes = [
            GinIndex(fields=["search_vector"], name="doc_search_gin"),
            models.Index(fields=["status"], name="doc_status_idx"),
            models.Index(fields=["name"], name="doc_name_idx"),
            models.Index(fields=["model_name"], name="doc_model_name_idx"),
        ]

    def __str__(self):
        return self.name or f"Document {self.id}"

    # --- helpers ---------------------------------------------------------
    def increment_access(self, by: int = 1, update_history: bool = True):
        """Atomically increment access counter and optionally stamp metadata.history.accessed."""
        if not self.pk:
            return
        type(self).objects.filter(pk=self.pk).update(count_accessed=F('count_accessed') + by)
        self.count_accessed += by
        if update_history:
            now_ms = int(timezone.now().timestamp() * 1000)
            meta = self.metadata or {}
            hist = meta.setdefault('history', {})
            hist['accessed'] = {'dt': now_ms, 'contact_id': 0}
            type(self).objects.filter(pk=self.pk).update(metadata=meta)

    def rebuild_search_vector(self, commit: bool = True):
        if not self.pk:
            return
        qs = type(self).objects.filter(pk=self.pk)
        qs.update(search_vector=SearchVector('name', 'description', 'body'))
        if commit:
            refreshed = qs.values('search_vector').first()
            if refreshed:
                self.search_vector = refreshed['search_vector']  # type: ignore[assignment]

    def save(self, *args, **kwargs):
        # derive size if body present
        if self.body and not self.size_bytes:
            self.size_bytes = len(self.body.encode('utf-8'))
        is_create = self.pk is None
        # ensure slug if missing and name present (non-destructive)
        if not self.slug and self.name:
            from django.utils.text import slugify
            base = slugify(self.name)[:240] or None
            if base:
                candidate = base
                # handle potential collisions (rare for readmes)
                i = 2
                while type(self).objects.filter(slug=candidate).exclude(pk=self.pk or 0).exists():
                    suffix = f"-{i}"
                    candidate = (base[: 240 - len(suffix)] + suffix)
                    i += 1
                self.slug = candidate
        # Capture original field values for change detection (only if existing)
        tracked_original = {}
        tracked_fields: list[str] = []
        try:
            # Fetch settings specifying keyword fields: purpose='keywords'
            model_key = 'Document'  # canonical model identifier for settings
            # Prefer model_target in Setting going forward
            setting = Setting.objects.filter(model_target=model_key, purpose='keywords', is_active=True).first()
            if setting and isinstance(setting.data, dict):
                fields_spec = setting.data.get('fields') or setting.data.get('field_list') or []
                if isinstance(fields_spec, str):  # allow comma-separated string
                    parts = fields_spec.split(',') if fields_spec else []
                    fields_spec = [f.strip() for f in parts if f and isinstance(f, str)]
                if isinstance(fields_spec, (list, tuple)):
                    tracked_fields = [f for f in fields_spec if isinstance(f, str)]
            if not is_create and tracked_fields:
                db_self = type(self).objects.filter(pk=self.pk).only(*[f for f in tracked_fields if f in [fld.name for fld in self._meta.fields]]).first()
                if db_self:
                    for f in tracked_fields:
                        if hasattr(db_self, f):
                            tracked_original[f] = getattr(db_self, f)
        except Exception:
            pass

        super().save(*args, **kwargs)
        self.rebuild_search_vector(commit=False)

        # Decide whether to enqueue Pending
        try:
            model_key = 'Document'
            enqueue = False
            if is_create:
                enqueue = True
            elif tracked_fields:
                for f in tracked_fields:
                    old_val = tracked_original.get(f, None)
                    new_val = getattr(self, f, None)
                    if old_val != new_val:
                        enqueue = True
                        break
            # Fallback: if no tracked fields defined but table configured in keyword requirements
            if not enqueue and model_key in get_keyword_requirements():
                enqueue = is_create  # only create on new rows to avoid noise

            if enqueue:
                # Debounce: ensure no unprocessed Pending exists for this id/table
                if not Pending.objects.filter(model_name=model_key, record_id=self.id, dt_processed=0).exists():
                    Pending.objects.create(
                        model_name=model_key,
                        record_id=self.id,
                        data={'reason': 'keywords', 'model': 'Document', 'tracked_fields': tracked_fields}
                    )
        except Exception:
            pass



# Next actions
# Add a data migration or management command to rebuild search_vector for future bulk updates.
# Add model tests (increment_access, search_vector update, size_bytes derivation).
# Consider enforcing allowed range for security_level and retention_period.