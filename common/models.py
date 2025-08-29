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
from django.db import transaction
from django.db.models import F, Value
from django.db.models.expressions import Func
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

# --- Optimistic concurrency / atomic JSON support (NEW) ----------------------

class VersionConflictError(Exception):
    """Raised when an optimistic concurrency (version) check fails."""
    pass


class JSONBSet(Func):
    """Django Func wrapper for PostgreSQL jsonb_set(target, path, new_value, create_missing).

    NOTE: path is provided as a PostgreSQL text array literal string e.g. '{flags,keywords_pending}'.
    """
    function = 'jsonb_set'
    template = "%(function)s(%(expressions)s)"
    arity = 4  # target, path, new_value, create_missing
    def __init__(self, target, path, new_value, create_missing=True, **extra):
        expressions = [target, path, new_value, Value(create_missing)]
        super().__init__(*expressions, output_field=models.JSONField(), **extra)

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

    # ---------------- Optimistic Concurrency Helpers (NEW) ------------------
    def assert_version(self, expected_version: int | None):
        """Ensure current instance version matches expected_version.

        expected_version can be None to skip (caller decided no check).
        Raises VersionConflictError if mismatch.
        """
        if expected_version is None:
            return
        # refresh current version from DB to ensure accuracy
        current = type(self).objects.filter(pk=self.pk).values_list('version', flat=True).first() if self.pk else None
        if current is None:
            return  # object not yet persisted; treat as fine
        if current != expected_version:
            raise VersionConflictError(f"Version conflict: expected {expected_version} got {current}")

    # ---------------- Atomic JSON field updates (NEW) ----------------------
    @classmethod
    def atomic_json_set(cls, pk: int, field: str, path: list[str], value, create_missing: bool = True, expected_version: int | None = None):
        """Atomically set a JSON path inside metadata/refs/prefs/comments.

        Args:
            pk: primary key of row.
            field: one of 'metadata','refs','prefs','comments'.
            path: list of nested keys to set e.g. ['flags','keywords_pending'].
            value: JSON-serializable value to write.
            create_missing: pass-through to jsonb_set create_missing flag.
            expected_version: if provided, enforce optimistic concurrency.

        Returns updated row count (0 or 1) and new version (if updated) else None.
        """
        if field not in {'metadata','refs','prefs','comments'}:
            raise ValueError('field must be one of metadata, refs, prefs, comments')
        path_literal = '{' + ','.join(path) + '}'
        with transaction.atomic():
            base_qs = cls.objects.select_for_update().filter(pk=pk)
            if expected_version is not None:
                base_qs = base_qs.filter(version=expected_version)
            # Use jsonb_set; wrap new value as JSON via Value(json.dumps(...)) is not needed; Django will adapt.
            updated = base_qs.update(**{
                field: JSONBSet(F(field), Value(path_literal), Value(json.dumps(value)), True),
                'version': F('version') + 1,
                'modified_dt': int(timezone.now().timestamp() * 1000),
            })
            if expected_version is not None and updated == 0:
                # determine current version to report
                current = cls.objects.filter(pk=pk).values_list('version', flat=True).first()
                raise VersionConflictError(f"Version conflict on atomic_json_set: expected {expected_version} got {current}")
            if updated:
                new_version = cls.objects.filter(pk=pk).values_list('version', flat=True).first()
                return updated, new_version
            return updated, None

    @classmethod
    def atomic_list_append(cls, pk: int, field: str, path: list[str], element, max_length: int | None = None, expected_version: int | None = None):
        """Atomically append an element to a JSON array at given path.

        Implementation performs a SELECT FOR UPDATE, mutates in Python, and saves minimal fields,
        still giving row-level atomicity. For extremely high contention consider a pure-SQL approach.
        """
        if field not in {'metadata','refs','prefs','comments'}:
            raise ValueError('field must be one of metadata, refs, prefs, comments')
        with transaction.atomic():
            obj = cls.objects.select_for_update().only('id', field, 'version', 'modified_dt').get(pk=pk)
            if expected_version is not None and obj.version != expected_version:
                raise VersionConflictError(f"Version conflict on atomic_list_append: expected {expected_version} got {obj.version}")
            target = getattr(obj, field)
            cur = target
            for key in path[:-1]:
                cur = cur.setdefault(key, {})
            arr_key = path[-1]
            arr = cur.setdefault(arr_key, [])
            if not isinstance(arr, list):
                raise ValueError('Target JSON path is not a list')
            arr.append(element)
            if max_length is not None and len(arr) > max_length:
                # trim oldest
                del arr[0:len(arr)-max_length]
            # Save will bump version; ensure fields persisted
            obj.save(update_fields=[field, 'version', 'modified_dt'])
            return obj.version

    # Convenience wrappers for common operations
    def optimistic_save(self, expected_version: int | None = None, *args, **kwargs):
        """Perform a save with an expected_version check (application-level optimistic lock)."""
        if self.pk and expected_version is not None and self.version != expected_version:
            raise VersionConflictError(f"Version conflict on optimistic_save: expected {expected_version} got {self.version}")
        return self.save(*args, **kwargs)

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

    # --- Universal dict / Pydantic helpers (shared with Slim) -------------
    def to_universal_dict(self) -> Dict[str, Any]:
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
            'version': self.version,
        }

    def as_pydantic(self, refresh: bool = False):
        if not PydanticBaseModel:
            return self.to_universal_dict()
        if refresh or self._pydantic_cache is None:
            data = self.to_universal_dict()
            self._pydantic_cache = UniversalAPISchema(**data)  # type: ignore[arg-type]
        return self._pydantic_cache

    def pydantic_dump(self, *args, **kwargs) -> Dict[str, Any]:
        obj = self.as_pydantic()
        if hasattr(obj, 'model_dump'):
            return obj.model_dump(*args, **kwargs)  # type: ignore[attr-defined]
        return obj  # already dict


class SlimBaseModel(models.Model):
    """Lightweight alternative to BaseModel for ephemeral / high-churn tables.

    Includes only:
      - id (BigAuto)
      - uuid (unique tracking)
      - ida (external alt id)
      - created_dt / modified_dt (ms epoch)
      - version (optimistic concurrency integer)

    Excludes heavy JSON envelopes (metadata, refs, prefs, comments, health_rating) and GIN indexes.
    Provides a minimal save() implementing timestamp + version bump semantics.
    """
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    ida = models.CharField(max_length=40, blank=True, db_index=True)
    created_dt = models.BigIntegerField(default=0, db_index=True)
    modified_dt = models.BigIntegerField(default=0, db_index=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        now_ms = int(timezone.now().timestamp() * 1000)
        if not self.pk:
            self.created_dt = now_ms
        else:
            # bump version only on updates
            self.version = (self.version or 0) + 1
        self.modified_dt = now_ms
        super().save(*args, **kwargs)

    def assert_version(self, expected_version: int | None):
        if expected_version is None or not self.pk:
            return
        current = type(self).objects.filter(pk=self.pk).values_list('version', flat=True).first()
        if current is not None and current != expected_version:
            raise VersionConflictError(f"Version conflict: expected {expected_version} got {current}")

    def optimistic_save(self, expected_version: int | None = None, *args, **kwargs):
        if expected_version is not None and self.pk and self.version != expected_version:
            raise VersionConflictError(f"Version conflict: expected {expected_version} got {self.version}")
        return self.save(*args, **kwargs)
        return None

    # Slim model intentionally omits comments/metadata/refs; helpers skipped.

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
        """Return normalized dict; adapts to presence/absence of heavy fields.

        Works for both BaseModel (full envelope) and SlimBaseModel (minimal).
        """
        base = {
            'id': self.pk,
            'uuid': str(getattr(self, 'uuid', '')) or None,
            'ida': getattr(self, 'ida', ''),
            'dt_created': getattr(self, 'created_dt', None),
            'dt_modified': getattr(self, 'modified_dt', None),
            'version': getattr(self, 'version', None),
        }
        # Only attach enriched fields if they physically exist
        if hasattr(self, 'metadata'):
            meta = getattr(self, 'metadata') or {}
            history = meta.get('history', {}) if isinstance(meta, dict) else {}
            base.update({
                'metadata': meta,
                'refs': getattr(self, 'refs', {}) or {},
                'prefs': getattr(self, 'prefs', {}) or {},
                'comments': getattr(self, 'comments', {}) or {},
                'health_rating': getattr(self, 'health_rating', 0),
                'dt_created': history.get('created', {}).get('dt') or base['dt_created'],
                'dt_modified': history.get('modified', {}).get('dt') or base['dt_modified'],
            })
        return base

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

# Yes, it’s coherent: a light “universal envelope” giving every table consistent extensibility (refs for relationships, prefs for per‑record settings, metadata for lifecycle/state, comments for discussion). That yields flexibility without exploding the relational schema.

# Key strengths

# Uniform contract across models simplifies generic endpoints (list/search/get/patch).
# JSONB lets you evolve structure without migrations for every tweak.
# Keyword + history + flags in metadata centralize lifecycle logic.
# Refs.links provides a hub for soft relationships before (or instead of) dedicated join tables.
# Targeted improvement suggestions

# Validation & Contracts

# Add lightweight Pydantic (already scaffolded) or Django validator hooks to enforce allowed keys / shapes inside refs.prefs.metadata to prevent drift.
# Maintain a version field inside metadata.flags.schema_rev and include a migration task that can auto-upgrade old shapes.
# Indexing & Query Performance

# Consider selective GIN JSONB path indexes on the most queried nested keys (e.g., (metadata->'history'->'modified'->>'dt')::bigint) if you start filtering heavily there.
# Add a B-tree index on (is_deleted, is_archived, modified_dt) for common active/ordering scans.
# Atomic JSON Updates

# Introduce helper methods using database-level JSONB set / concat operations (F expressions / Func) to avoid race conditions and rewriting the entire JSON on frequent small updates (e.g., increment access or add a single link).
# Access & Security

# If sensitive data ever goes into metadata/comments, consider field‑level encryption or a separate secure JSON field.
# Enforce max lengths or sanitize incoming comments.notes to mitigate unbounded growth.
# Size & Growth Controls

# You already enforce max serialized size; also log (warn) when a record crosses a threshold (e.g., 50% of limit) to detect pathological growth early.
# Periodic cleanup task to trim comments.notes beyond N most recent (configurable).
# Relationships Strategy

# For high‑cardinality relations (thousands of related IDs) consider promoting them from refs.links to a proper associative table before performance degrades.
# Provide bulk sync endpoints that translate refs.links entries into normalized tables when matured.
# Keyword Refresh

# Offload update_keywords to async (Celery) and track next_refresh_due in metadata.health or versioning for scheduling.
# Add simple trigram or GIN index on an aggregated searchable text column if keyword matching becomes slow.
# Concurrency / Versioning

# Expose version in API and require clients to send it back for optimistic concurrency (409 if mismatched).
# Optionally store a small diff log (changed_fields) in metadata.versioning or a separate audit table for investigative trails.
# Comments Structure

# Add a durable id per note (UUID) for targeted updates/deletes without rewriting the whole notes list.
# Limit note size and sanitize HTML/markdown if rendering.
# Observability

# Emit structured events (model, pk, action, changed_fields) from emit_change_log to a message bus for analytics and search indexing pipelines.
# Testing Aids
# Provide factory utilities that generate default metadata/refs with overrides, ensuring tests don’t duplicate structure logic.
# Future Evolution
# If certain prefs become widely used and stable, consider promoting to first-class columns for query speed (hybrid approach).
# Maintain a registry describing which JSON paths are “supported” vs experimental to guide client usage.
# Minimal quick wins

# Add JSON path index on refs->'keywords'.
# Implement a domain-level helper for atomic link add/remove using database operations (JSONB set).
# Introduce optimistic concurrency check in save (compare version if passed in context).
# Overall verdict Design is sound for flexibility + rapid iteration; just add a thin validation and indexing layer plus atomic update helpers to keep it healthy as data volume grows. 

# Added atomic JSON update utilities and version conflict handling:

# Highlights

# Introduced VersionConflictError and JSONBSet wrapper.
# Added BaseModel.assert_version, atomic_json_set (pure SQL jsonb_set with optimistic lock), atomic_list_append (row-level lock, single version bump), and optimistic_save helper.
# Adjusted atomic_list_append to avoid double version increment.
# Created tests (test_atomic_json_updates.py) covering set, list append, and conflict; all pass (3 passed).
# Minor pydantic deprecation warning unchanged (informational).
# How to use

# Atomic field set: updated, new_version = Domain.atomic_json_set(pk, 'metadata', ['flags','schema_rev'], 2, expected_version=client_version)
# Append to notes: new_version = Domain.atomic_list_append(pk, 'comments', ['notes'], {'text':'hi'}, expected_version=client_version)
# Guarded save: obj.optimistic_save(expected_version=client_version)
# All new code builds and tests green. Let me know if you want an API endpoint layer (PATCH with version) next.

# Added generalized optimistic concurrency & atomic JSON PATCH support:

# Updates

# Extracted reusable OptimisticPatchMixin to common/mixins.py.
# Refactored DomainDetailView to import the mixin.
# Added comprehensive README section documenting payload contract, examples, error handling, extension steps, and rationale.
# Fixed markdown formatting and lint issues.
# All domain tests still pass (3 tests). Atomic JSON tests remain green.
# You can now apply the mixin to other BaseModel-derived views for consistent versioned PATCH behavior. Let me know if you want a generic base detail view or header (If-Match) support next.