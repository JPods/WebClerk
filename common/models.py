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
from typing import Any, Dict, Optional, cast, Iterable
import inspect
import json  # ensure available for size checks

"""
Modular model capability system.

Goal: allow per-table composition of only the JSON envelopes / helpers needed
while preserving a consistent universal contract (core identity + timestamps + version).

Composition diagram (left -> right MRO precedence):
    class BaseModel(MetadataMixin, RefsMixin, PrefsMixin, CommentsMixin,
                    HealthMixin, KeywordsMixin, LifecycleMixin,
                    CoreModel, UniversalDictMixin, AtomicJSONMixin)

Concrete app models inherit BaseModel for the full envelope. Lighter tables
inherit CoreModel or selectively add mixins (feature mixins first, then
CoreModel, then UniversalDictMixin. Include AtomicJSONMixin only if at least
one JSON envelope field is present.

Capability discovery: model_capabilities(Model) returns sorted list of feature flags.
Each mixin sets feature_flags = {'metadata'} etc.
"""

# --- Optional Pydantic support (still optional) -----------------------------
try:
    from pydantic import BaseModel as PydanticBaseModel
except ImportError:  # pragma: no cover - optional
    PydanticBaseModel = None  # type: ignore

if PydanticBaseModel:  # pragma: no cover - structure definition
    class UniversalAPISchema(PydanticBaseModel):  # type: ignore[misc]
        id: Optional[int] = None
        uuid: Optional[str] = None
        ida: Optional[str] = None
        metadata: Dict[str, Any] | None = None
        refs: Dict[str, Any] | None = None
        prefs: Dict[str, Any] | None = None
        comments: Dict[str, Any] | None = None
        health_rating: Optional[int] = 0
        dt_created: Optional[int] = None
        dt_modified: Optional[int] = None
        version: Optional[int] = None

        class Config:
            arbitrary_types_allowed = True
else:  # pragma: no cover - fallback stub
    class UniversalAPISchema:  # type: ignore
        pass

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

### -------------------- MIXIN & CORE DEFINITIONS ------------------------- ###

class CoreModel(models.Model):
    """Minimal universal core (identity + timestamps + optimistic version)."""
    feature_flags = {'core'}
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    ida = models.CharField(max_length=40, blank=True, db_index=True)
    created_dt = models.BigIntegerField(default=0, db_index=True)
    modified_dt = models.BigIntegerField(default=0, db_index=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        abstract = True

    _pydantic_cache: Optional[UniversalAPISchema] = None  # cache for any composition

    def save(self, *args, **kwargs):  # core timestamp + version bump
        now_ms = int(timezone.now().timestamp() * 1000)
        if not self.pk:
            self.created_dt = now_ms
        else:
            self.version = (self.version or 0) + 1
        self.modified_dt = now_ms
        super().save(*args, **kwargs)
        self._pydantic_cache = None

    # optimistic helpers
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

    def __str__(self):  # convenience for admin/debug
        for attr in ('name', 'title', 'email', 'ida', 'uuid'):
            v = getattr(self, attr, None)
            if v:
                return str(v)
        return f"{self.__class__.__name__}#{self.pk or 'unsaved'}"


class LifecycleMixin(models.Model):
    feature_flags = {'lifecycle'}
    is_deleted = models.BooleanField(default=False, db_index=True)
    is_archived = models.BooleanField(default=False, db_index=True)

    class Meta:
        abstract = True

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


class MetadataMixin(models.Model):
    feature_flags = {'metadata'}
    metadata = models.JSONField(default=default_metadata, help_text="Universal metadata envelope")

    class Meta:
        abstract = True

    def _init_metadata_if_needed(self):
        if not isinstance(self.metadata, dict):
            self.metadata = default_metadata()
        self.metadata.setdefault('history', default_metadata()['history'])
        self.metadata.setdefault('flags', {})
        self.metadata.setdefault('versioning', {})
        self.metadata['flags'].setdefault('schema_rev', 1)

    def save(self, *args, **kwargs):  # inject history handling
        creating = not self.pk
        now_ms = int(timezone.now().timestamp() * 1000)
        self._init_metadata_if_needed()
        hist = self.metadata['history']
        hist['modified'] = {'dt': now_ms, 'contact_id': getattr(self, 'modified_by_id', 0)}
        if creating:
            hist['created'] = {'dt': now_ms, 'contact_id': getattr(self, 'created_by_id', 0)}
        super().save(*args, **kwargs)

    def get_history(self) -> dict:
        return self.metadata.get('history', {}) if isinstance(self.metadata, dict) else {}

    def get_metadata_value(self, key_path: str):
        keys = key_path.split('.')
        cur = self.metadata
        try:
            for k in keys:
                cur = cur[k]
            return cur
        except Exception:
            return None

    def set_metadata_value(self, key_path: str, value):
        keys = key_path.split('.')
        target = self.metadata
        for k in keys[:-1]:
            target = target.setdefault(k, {})
        target[keys[-1]] = value

    def get_created_timestamp(self):
        return self.get_metadata_value('history.created.dt') or 0
    def get_modified_timestamp(self):
        return self.get_metadata_value('history.modified.dt') or 0
    @property
    def dt_verified(self):
        if not self.metadata:
            return None
        verified_dt_ms = self.metadata.get('history', {}).get('verified', {}).get('dt', 0)
        if verified_dt_ms:
            return timezone.datetime.fromtimestamp(verified_dt_ms / 1000, tz=timezone.utc)


class RefsMixin(models.Model):
    feature_flags = {'refs'}
    refs = models.JSONField(default=default_refs, help_text="Keywords / tags / lightweight links")

    class Meta:
        abstract = True

    def add_keyword(self, keyword: str):
        kw_lower = keyword.lower()
        existing = [k.lower() for k in self.refs.get('keywords', [])]
        if kw_lower not in existing:
            self.refs.setdefault('keywords', []).append(kw_lower)

    def add_tag(self, tag: str):
        if tag not in self.refs.get('tags', []):
            self.refs.setdefault('tags', []).append(tag)


class PrefsMixin(models.Model):
    feature_flags = {'prefs'}
    prefs = models.JSONField(default=default_prefs, help_text="User preferences / settings")
    class Meta:
        abstract = True


class CommentsMixin(models.Model):
    feature_flags = {'comments'}
    comments = models.JSONField(default=default_comments, help_text="Threaded notes / comment fields")
    class Meta:
        abstract = True

    def add_note(self, note_type: str, text: str, by: int | str = 'system'):
        if not isinstance(self.comments, dict):
            self.comments = default_comments()
        notes = self.comments.setdefault('notes', [])
        notes.append({'type': note_type, 'text': text, 'by': by, 'dt': int(timezone.now().timestamp() * 1000)})
        self.comments[note_type] = text


class HealthMixin(models.Model):
    feature_flags = {'health'}
    health_rating = models.IntegerField(default=0, help_text="Data quality rating (0-100)")
    class Meta:
        abstract = True


class KeywordsMixin(models.Model):
    feature_flags = {'keywords'}
    class Meta:
        abstract = True

    def mark_keywords_dirty(self):
        if hasattr(self, 'metadata'):
            # type: ignore[attr-defined]
            self.metadata.setdefault('flags', {})['keywords_pending'] = True  # type: ignore[index]

    @property
    def keywords_pending(self) -> bool:
        return bool(getattr(self, 'metadata', {}).get('flags', {}).get('keywords_pending')) if hasattr(self, 'metadata') else False

    def update_keywords(self):  # requires refs + metadata if present
        if not hasattr(self, 'refs'):
            return  # type: ignore[attr-defined]
        keywords_set = set()
        for field in self._meta.fields:
            if isinstance(field, (models.CharField, models.TextField)):
                val = getattr(self, field.name, '')
                if val:
                    for raw in str(val).lower().split():
                        token = raw.strip('.,!?;:"()[]{}')
                        if len(token) > 2:
                            keywords_set.add(token)
        self.refs.setdefault('keywords', [])  # type: ignore[attr-defined]
        self.refs['keywords'] = list(keywords_set)[:50]  # type: ignore[attr-defined]
        if hasattr(self, 'metadata'):
            self.metadata.setdefault('flags', {})['keywords_pending'] = False  # type: ignore[attr-defined]
            self.metadata.setdefault('versioning', {})['keywords_refreshed_dt'] = int(timezone.now().timestamp() * 1000)  # type: ignore[attr-defined]


class AtomicJSONMixin(models.Model):
    feature_flags = {'atomic_json'}
    class Meta:
        abstract = True

    @classmethod
    def atomic_json_set(cls, pk: int, field: str, path: list[str], value, create_missing: bool = True, expected_version: int | None = None):
        if field not in {'metadata','refs','prefs','comments'}:
            raise ValueError('field must be one of metadata, refs, prefs, comments')
        if not hasattr(cls, field):
            raise ValueError(f"Model {cls.__name__} has no field '{field}' for atomic update")
        path_literal = '{' + ','.join(path) + '}'
        with transaction.atomic():
            qs = cls.objects.select_for_update().filter(pk=pk)
            if expected_version is not None:
                qs = qs.filter(version=expected_version)
            updated = qs.update(**{
                field: JSONBSet(F(field), Value(path_literal), Value(json.dumps(value)), True),
                'version': F('version') + 1,
                'modified_dt': int(timezone.now().timestamp() * 1000),
            })
            if expected_version is not None and updated == 0:
                current = cls.objects.filter(pk=pk).values_list('version', flat=True).first()
                raise VersionConflictError(f"Version conflict on atomic_json_set: expected {expected_version} got {current}")
            if updated:
                new_version = cls.objects.filter(pk=pk).values_list('version', flat=True).first()
                return updated, new_version
            return updated, None

    @classmethod
    def atomic_list_append(cls, pk: int, field: str, path: list[str], element, max_length: int | None = None, expected_version: int | None = None):
        if field not in {'metadata','refs','prefs','comments'}:
            raise ValueError('field must be one of metadata, refs, prefs, comments')
        if not hasattr(cls, field):
            raise ValueError(f"Model {cls.__name__} has no field '{field}' for atomic update")
        with transaction.atomic():
            obj = cls.objects.select_for_update().only('id', field, 'version', 'modified_dt').get(pk=pk)
            if expected_version is not None and obj.version != expected_version:  # type: ignore[attr-defined]
                raise VersionConflictError(f"Version conflict on atomic_list_append: expected {expected_version} got {obj.version}")  # type: ignore[attr-defined]
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
                del arr[0:len(arr)-max_length]
            obj.save(update_fields=[field, 'version', 'modified_dt'])
            return obj.version  # type: ignore[attr-defined]


class UniversalDictMixin(models.Model):
    feature_flags = {'universal_dict'}
    class Meta:
        abstract = True

    def to_universal_dict(self) -> Dict[str, Any]:
        base = {
            'id': self.pk,
            'uuid': str(getattr(self, 'uuid', '')) or None,
            'ida': getattr(self, 'ida', ''),
            'dt_created': getattr(self, 'created_dt', None),
            'dt_modified': getattr(self, 'modified_dt', None),
            'version': getattr(self, 'version', None),
        }
        if hasattr(self, 'metadata'):
            meta = getattr(self, 'metadata') or {}
            history = meta.get('history', {}) if isinstance(meta, dict) else {}
            base.update({
                'metadata': meta,
                'dt_created': history.get('created', {}).get('dt') or base['dt_created'],
                'dt_modified': history.get('modified', {}).get('dt') or base['dt_modified'],
            })
        for opt in ('refs', 'prefs', 'comments', 'health_rating'):
            if hasattr(self, opt):
                base[opt] = getattr(self, opt)
        return base

    def as_pydantic(self, refresh: bool = False):
        if not PydanticBaseModel:
            return self.to_universal_dict()
        if refresh or getattr(self, '_pydantic_cache', None) is None:
            self._pydantic_cache = UniversalAPISchema(**self.to_universal_dict())  # type: ignore[arg-type]
        return self._pydantic_cache

    def pydantic_dump(self, *args, **kwargs) -> Dict[str, Any]:
        obj = self.as_pydantic()
        if hasattr(obj, 'model_dump'):
            return obj.model_dump(*args, **kwargs)  # type: ignore[attr-defined]
        return cast(Dict[str, Any], obj)


### -------------------- FULL COMPOSITION CLASS --------------------------- ###

class BaseModel(MetadataMixin, RefsMixin, PrefsMixin, CommentsMixin,
                HealthMixin, KeywordsMixin, LifecycleMixin,
                CoreModel, UniversalDictMixin, AtomicJSONMixin):
    """Full capability base model (replaces previous monolithic design)."""
    class Meta:
        abstract = True
        indexes = [
            GinIndex(fields=['refs'], name='refs_gin_idx'),
            GinIndex(fields=['prefs'], name='prefs_gin_idx'),
        ]

    # Custom queryset / manager (only for full model using lifecycle + metadata)
    class FullQuerySet(models.QuerySet):
        def active(self):
            return self.filter(is_deleted=False, is_archived=False)
        def deleted(self):
            return self.filter(is_deleted=True)
        def archived(self):
            return self.filter(is_archived=True)
        def keyword_pending(self):
            return self.filter(models.Q(metadata__flags__keywords_pending=True))

    class FullManager(models.Manager):
        def get_queryset(self):
            return BaseModel.FullQuerySet(self.model, using=self._db)
        def active(self):
            return self.get_queryset().active()
        def deleted(self):
            return self.get_queryset().deleted()
        def archived(self):
            return self.get_queryset().archived()
        def keyword_pending(self):
            return self.get_queryset().keyword_pending()

    objects = FullManager()

    def save(self, *args, **kwargs):  # orchestrate save chain
        # MetadataMixin.save handles metadata history first, then CoreModel.save updates version/timestamps
        super().save(*args, **kwargs)
        # enforce size limits after save adjustments but before returning
        if hasattr(self, 'metadata'):
            def check_size(field_value, max_size, field_name):
                size = len(json.dumps(field_value).encode('utf-8'))
                if size > max_size:
                    raise ValueError(f"{field_name} exceeds maximum size of {max_size} bytes")
            check_size(self.metadata, MAX_METADATA_SIZE, 'metadata')
        if hasattr(self, 'refs'):
            check_size(self.refs, MAX_REFS_SIZE, 'refs')
        if hasattr(self, 'prefs'):
            check_size(self.prefs, MAX_PREFS_SIZE, 'prefs')
        # mark keywords dirty (KeywordsMixin) if available
        if isinstance(self, KeywordsMixin):
            self.mark_keywords_dirty()


# Slim (minimal) base export for clarity when creating lightweight models
SlimBaseModel = CoreModel  # kept for readability, points to CoreModel


### -------------------- CAPABILITY REGISTRY HELPERS --------------------- ###

def model_capabilities(model_or_instance) -> list[str]:
    cls = model_or_instance if inspect.isclass(model_or_instance) else model_or_instance.__class__
    caps: set[str] = set()
    for base in cls.mro():
        if hasattr(base, 'feature_flags'):
            flags = getattr(base, 'feature_flags')
            if isinstance(flags, Iterable):
                caps.update(flags)
    return sorted(caps)

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

# Expose version in API and require clients to send it back for optimistic concurrency (412 if mismatched – Precondition Failed).
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