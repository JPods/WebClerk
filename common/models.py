# PURPOSE: Base model with Universal API metadata system for ALL models
# UNIVERSAL API: Provides foundation metadata structure that makes Universal API work
# REPLACES: Individual metadata handling scattered across different models
# TEAM NOTE: Every model inherits from BaseModel to get Universal API compatibility
# ARCHITECTURE: Implements the 4D-style metadata system (history, health, refs, prefs)
# METADATA STRUCTURE: 
#   - history.dt.created/modified (timestamps)
#   - health.rating (data quality scores)
#   - refs.keywords (searchable keywords)
#   - prefs (user preferences)
# FEATURES:
#   - Automatic timestamp management
#   - Keyword generation from all fields
#   - Undefined field capture
#   - JSON metadata storage
# TABLES: Base class inherited by all models (contacts, addresses, phones, emails, etc.)

# All timestamps are saved as GMT/UTC (Universal API standard)

from django.db import models
import uuid
from django.utils import timezone
from django.contrib.postgres.indexes import GinIndex
from typing import Any, Dict, Optional, Union
import json  # ensure available for size checks

# --- Optional Pydantic support (small step) ---------------------------------
try:  # Do not hard-depend; keeps migration surface minimal
    from pydantic import BaseModel as PydanticBaseModel
except ImportError:  # Pydantic not installed yet
    PydanticBaseModel = None  # type: ignore

if PydanticBaseModel:
    class UniversalAPISchema(PydanticBaseModel):  # type: ignore[misc]
        """Lightweight Pydantic representation of BaseModel core fields.

        CHANGE: Introduced for serialization / validation without altering
        existing Django inheritance tree. Only core universal fields are
        included; domain models can extend this later.
        """
        id: Optional[int] = None
        uuid: Optional[str] = None
        ida: str | None = None
        metadata: Dict[str, Any]
        refs: Dict[str, Any]
        prefs: Dict[str, Any]
        comments: Dict[str, Any]
        health_rating: int = 0
        dt_created: Optional[int] = None
        dt_modified: Optional[int] = None

        class Config:
            arbitrary_types_allowed = True
else:
    # Fallback stub so type checkers know the name; runtime methods guard usage
    class UniversalAPISchema:  # type: ignore
        pass
from django.contrib.postgres.indexes import GinIndex

MAX_METADATA_SIZE = 320000  # bytes
MAX_REFS_SIZE = 320000      # bytes
MAX_PREFS_SIZE = 320000     # bytes

# functions must be defined before they are used

def default_metadata():
    now_ms = int(timezone.now().timestamp() * 1000)
    return {
        "security": "",
        "publish": "",
        "priority": "",
        "version": "1.0",
        "access": {"view": [], "edit": []},
        "history": {
            "created": {"dt": now_ms, "contact_id": 0},
            "modified": {"dt": now_ms, "contact_id": 0},
            "accessed": {"dt": now_ms, "contact_id": 0},
            "verified": {"dt": 0, "contact_id": 0},
            "synced": {"dt": 0, "contact_id": 0}
        },
        "health": {
            "rating": 0,
            "completeness": 0,
            "accuracy": 0,
            "freshness": 0,
            "consistency": 0
        },
        "undefined": {}
    }

def default_refs():
    return {
        "keywords": [],
        "tags": [],
        #QQQ add linkages
        "links": {"contacts": []},
        "categories": [],
        "related_ids": []
    }

def default_prefs():
    return {"userdefined": ""}

def default_data():
    return {}

def default_comments():
    """Structured default for comments (CHANGE)."""
    return {
        'public': '',
        'process': '',
        'partner': '',
        'notes': []  # threaded note list pattern
    }

class BaseModel(models.Model):
    """
    Base model that provides Universal API metadata structure.
    All models in the system inherit from this to get Universal API compatibility.
    Implements the 4D-style metadata system with modern Django features.
    """
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    ida = models.CharField(max_length=40, blank=True, db_index=True, help_text="Alternate ID for external systems (indexed)")  # CHANGE: add index for lookups
    # CHANGE: denormalized timestamps (UTC ms) for fast ordering / indexing
    created_dt = models.BigIntegerField(default=0, db_index=True, help_text="Denormalized created timestamp (ms UTC)")
    modified_dt = models.BigIntegerField(default=0, db_index=True, help_text="Denormalized modified timestamp (ms UTC)")
    # CHANGE: lifecycle flags
    is_deleted = models.BooleanField(default=False, db_index=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    # CHANGE: optimistic concurrency token
    version = models.PositiveIntegerField(default=1, help_text="Incremented on each successful save")
    metadata = models.JSONField(default=default_metadata, help_text="Universal API metadata structure")
    refs = models.JSONField(default=default_refs, help_text="References: keywords, tags, categories")
    prefs = models.JSONField(default=default_prefs, help_text="User preferences and settings")
    comments = models.JSONField(default=default_comments, help_text="User comments and notes")  # CHANGE: proper structured default
    health_rating = models.IntegerField(default=0, help_text="Data quality rating (0-100)")

    # --- custom queryset / manager for lifecycle filtering -----------------
    class BaseModelQuerySet(models.QuerySet):
        def active(self):
            return self.filter(is_deleted=False, is_archived=False)
        def deleted(self):
            return self.filter(is_deleted=True)
        def archived(self):
            return self.filter(is_archived=True)
        def keyword_pending(self):
            return self.filter(models.Q(metadata__flags__keywords_pending=True))

    class BaseModelManager(models.Manager):
        def get_queryset(self):
            return BaseModel.BaseModelQuerySet(self.model, using=self._db)
        def active(self):
            return self.get_queryset().active()
        def deleted(self):
            return self.get_queryset().deleted()
        def archived(self):
            return self.get_queryset().archived()
        def keyword_pending(self):
            return self.get_queryset().keyword_pending()

    objects = BaseModelManager()

    class Meta:
        abstract = True
        indexes = [
            GinIndex(fields=['refs'], name='refs_gin_idx'),
            GinIndex(fields=['prefs'], name='prefs_gin_idx'),
        ]

    # Pydantic cache (instance-level). Not stored in DB. (CHANGE)
    _pydantic_cache: Optional[UniversalAPISchema] = None  # type: ignore

    def save(self, *args, **kwargs):
        now_timestamp = int(timezone.now().timestamp() * 1000)  # UTC milliseconds
        # CHANGE: defensive guard for metadata/history integrity
        if not isinstance(self.metadata, dict):
            self.metadata = default_metadata()
        self.metadata.setdefault('history', default_metadata()['history'])
        self.metadata.setdefault('flags', {})
        self.metadata.setdefault('versioning', {})
        # CHANGE: schema revision flag support
        self.metadata['flags'].setdefault('schema_rev', 1)

        self.metadata['history']['modified'] = {
            'dt': now_timestamp,
            'contact_id': getattr(self, 'modified_by_id', 0)
        }
        if not self.pk:
            self.metadata['history']['created'] = {
                'dt': now_timestamp,
                'contact_id': getattr(self, 'created_by_id', 0)
            }
            # initialize denormalized created timestamp
            self.created_dt = now_timestamp
        # always update modified denormalized
        self.modified_dt = now_timestamp
        # bump version (optimistic concurrency) - if existing row
        if self.pk:
            self.version = (self.version or 0) + 1

        # CHANGE: mark keywords for async refresh instead of computing every save
        self.mark_keywords_dirty()
        # CHANGE: auto rebuild keywords if missing list to maintain consistency
        if 'keywords' not in (self.refs or {}):
            self.refs['keywords'] = []

        def check_size(field_value, max_size, field_name):
            size = len(json.dumps(field_value).encode('utf-8'))
            if size > max_size:
                raise ValueError(f"{field_name} exceeds maximum size of {max_size} bytes")
        check_size(self.metadata, MAX_METADATA_SIZE, "metadata")
        check_size(self.refs, MAX_REFS_SIZE, "refs")
        check_size(self.prefs, MAX_PREFS_SIZE, "prefs")
        super().save(*args, **kwargs)
        # CHANGE: invalidate pydantic cache after persistence
        self._pydantic_cache = None

    def update_keywords(self):
        """Compute and store keyword list; clear pending flag.

        Intended to be called by an async maintenance task / cron when
        metadata.flags.keywords_pending is True. (CHANGE)
        """
        keywords_set = set()
        for field in self._meta.fields:
            if isinstance(field, (models.CharField, models.TextField)):
                val = getattr(self, field.name, '')
                if val:
                    for raw in str(val).lower().split():
                        token = raw.strip('.,!?;:"()[]{}')
                        if len(token) > 2:
                            keywords_set.add(token)
        self.refs['keywords'] = list(keywords_set)[:50]
        # Clear flag
        self.metadata.setdefault('flags', {})['keywords_pending'] = False
        # Record versioning info of keyword refresh (CHANGE)
        self.metadata.setdefault('versioning', {})['keywords_refreshed_dt'] = int(timezone.now().timestamp() * 1000)

    # --- keyword pending helpers (CHANGE) ---------------------------------
    def mark_keywords_dirty(self):
        self.metadata.setdefault('flags', {})['keywords_pending'] = True

    @property
    def keywords_pending(self) -> bool:
        return bool(self.metadata.get('flags', {}).get('keywords_pending'))

    # --- typed accessors (CHANGE) -----------------------------------------
    def get_history(self) -> dict:
        return self.metadata.get('history', {}) if isinstance(self.metadata, dict) else {}

    def add_note(self, note_type: str, text: str, by: int | str = 'system'):
        if not isinstance(self.comments, dict):
            self.comments = default_comments()
        notes = self.comments.setdefault('notes', [])
        notes.append({'type': note_type, 'text': text, 'by': by, 'dt': int(timezone.now().timestamp() * 1000)})
        self.comments[note_type] = text
        # don't save automatically to allow batching

    # --- soft delete / archive helpers (CHANGE) ---------------------------
    def soft_delete(self):
        self.is_deleted = True
        self.save()

    def restore(self):
        self.is_deleted = False
        self.save()

    def archive(self):
        self.is_archived = True
        self.save()

    def unarchive(self):
        self.is_archived = False
        self.save()

    # --- change log emission stub (CHANGE) --------------------------------
    def emit_change_log(self, changed_fields: list[str] | None = None):
        """Placeholder: route to Celery / signal for auditing."""
        # Integration point: send to message bus
        return {
            'model': self.__class__.__name__,
            'pk': self.pk,
            'version': self.version,
            'changed': changed_fields or [],
            'dt': int(timezone.now().timestamp() * 1000)
        }

    def get_metadata_value(self, key_path):
        keys = key_path.split('.')
        value = self.metadata
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return None

    def set_metadata_value(self, key_path, value):
        keys = key_path.split('.')
        target = self.metadata
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        target[keys[-1]] = value

    def add_keyword(self, keyword):
        if keyword.lower() not in [k.lower() for k in self.refs['keywords']]:
            self.refs['keywords'].append(keyword.lower())

    def add_tag(self, tag):
        if tag not in self.refs['tags']:
            self.refs['tags'].append(tag)

    def get_created_timestamp(self):
        return self.get_metadata_value('history.created.dt') or 0

    def get_modified_timestamp(self):
        return self.get_metadata_value('history.modified.dt') or 0

    @property
    def dt_verified(self):
        """Get verified timestamp from metadata.history.verified.dt (as GMT/UTC)."""
        if not self.metadata:
            return None
        verified_dt_ms = self.metadata.get('history', {}).get('verified', {}).get('dt', 0)
        if verified_dt_ms:
            return timezone.datetime.fromtimestamp(verified_dt_ms / 1000, tz=timezone.utc)
        return None

    def set_comments(self, partner=None, process=None, public=None):
        """
        Populate the comments JSONB with .partner, .process, .public keys.
        """
        if not isinstance(self.comments, dict):
            self.comments = {}
        if partner is not None:
            self.comments['partner'] = partner
        if process is not None:
            self.comments['process'] = process
        if public is not None:
            self.comments['public'] = public
        self.save()

    def __str__(self):
        name = getattr(self, 'name', None)
        if name:
            return str(name)
        title = getattr(self, 'title', None)
        if title:
            return str(title)
        email = getattr(self, 'email', None)
        if email:
            return str(email)

    # --- Pydantic helper methods (small, additive) --------------------------
    def to_universal_dict(self) -> Dict[str, Any]:
        """Return a normalized dict of universal fields (no ORM objects).

        Small step: provides consistent structure whether or not Pydantic
        is installed; can feed API responses or schema generation.
        """
        meta = self.metadata or {}
        history = meta.get('history', {}) if isinstance(meta, dict) else {}
        return {
            'id': self.pk,
            'uuid': str(self.uuid) if getattr(self, 'uuid', None) else None,
            'ida': self.ida,
            'metadata': meta,
            'refs': self.refs or {},
            'prefs': self.prefs or {},
            'comments': self.comments or {},
            'health_rating': self.health_rating,
            'dt_created': history.get('created', {}).get('dt'),
            'dt_modified': history.get('modified', {}).get('dt'),
        }

    def as_pydantic(self, refresh: bool = False):
        """Return a UniversalAPISchema instance if Pydantic is available.

        If Pydantic isn't installed, returns the plain universal dict.
        Use refresh=True to rebuild cache after in-memory modifications.
        """
        if not PydanticBaseModel:
            return self.to_universal_dict()
        if refresh or self._pydantic_cache is None:
            data = self.to_universal_dict()
            # Build schema (ignore extra keys handled by Pydantic if extended later)
            self._pydantic_cache = UniversalAPISchema(**data)  # type: ignore[arg-type]
        return self._pydantic_cache

    def pydantic_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Convenience: dict export using Pydantic if present else universal dict.

        Mirrors Pydantic's .model_dump() signature loosely for future parity.
        """
        obj = self.as_pydantic()
        if hasattr(obj, 'model_dump'):
            return obj.model_dump(*args, **kwargs)  # type: ignore[attr-defined]
        # Fallback already dict
        return obj  # type: ignore[return-value]
        return f"{self.__class__.__name__} #{self.pk}"

