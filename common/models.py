"""Common model capability layer for the Universal API.

This module defines a composable set of mixins plus core/base classes that any model can inherit to obtain a uniform, evolvable "envelope" of JSONB fields (metadata / refs / prefs / comments) along with search keywords, soft‑lifecycle flags, health rating, optimistic concurrency versioning andatomic JSON mutation helpers.

Layering overview (left = earlier in MRO resolution):

    CoreModel (identity + timestamps + version)
      ↑
    Lifecycle / Metadata / Refs / Prefs / Comments / Health / Keywords / AtomicJSON
      ↑
    UniversalDictMixin (stable outward serialization contract)
      ↑
    BaseModel (full composition: change tracking, size enforcement, helpers)

Design principles:
1. Uniform contract: Generic endpoints (list/search/get/patch) can treat every model
   the same because the universal dict surface is stable.
2. Incremental adoption: Lightweight tables may start with only CoreModel and later
   mix in additional capabilities without breaking existing code.
3. Evolvability: JSONB envelopes let us add or reshape nested data without schema
   churn; frequently queried data can still be promoted to columns later.
   In databases or systems that store data in JSON format, atomicity ensures that operations like updates, deletes, or inserts on JSON objects are executed as a single, indivisible action. This can help avoid inconsistencies in data storage.

4. Concurrency & integrity: Centralized version field + change tracking and atomic
   JSON helpers reduce race windows and expose changed_fields for optimistic UX.
5. Optional typing: If Pydantic is installed, a schema mirrors the outward shape
   for strongly typed integrations; otherwise we degrade gracefully.
   Python is not strongly typed by default, so this approach balances flexibility with type safety.

Every function / class below includes a concise docstring describing (a) purpose
and (b) how it contributes to CoreModel, BaseModel and/or the optional Pydantic layer.
"""

from __future__ import annotations

from django.db import models, transaction
from django.db.models import F, Value
from django.db.models.expressions import Func
from django.contrib.postgres.indexes import GinIndex
from django.utils import timezone
import logging
import uuid
import inspect
import json
from typing import Any, Dict, Optional, Iterable, cast

# ---------------- Size / warning thresholds ----------------
# YYY Review by 2026-03-01
MAX_METADATA_SIZE = 128000  # bytes
# larger data items should be driven into documents and linked
MAX_REFS_SIZE = 64000
MAX_PREFS_SIZE = 96000
SIZE_WARN_FRACTION = 0.75  # warn once JSON envelope passes 75% of limit
SIZE_ACTIVITY_FRACTIONS: tuple[float, ...] = (0.30, 0.60, 0.75)  # progressive telemetry thresholds
logger = logging.getLogger(__name__)

# ---------------- (Disabled) Large JSON offload prototype -----------------
# Goal: future ability to offload very large JSON subtrees (e.g. oversized comments
# or metadata sections) into an external Document store / table and replace them
# with lightweight pointers. For now we ONLY log candidates so we can tune
# thresholds before enabling.
#
# Review flag (YYY): revisit by same review date above.
OFFLOAD_LARGE_JSON_ENABLED = False            # master feature switch (disabled)
OFFLOAD_MIN_FRACTION = 0.60                   # subtree > 60% of field cap -> candidate
OFFLOAD_FIELDS: tuple[str, ...] = ("metadata", "comments")  # fields to scan when present
OFFLOAD_MAX_SCAN_DEPTH = 4                    # safeguard against deep recursion cost
OFFLOAD_LOG_PREFIX = "json_offload_telemetry" # structured log marker

def _json_size_bytes(value) -> int:
    try:
        return len(json.dumps(value, separators=(",", ":")).encode("utf-8"))
    except Exception:  # pragma: no cover - defensive
        return 0

def _find_large_subtrees(root, min_bytes: int, path: tuple[str, ...] = (), depth: int = 0, max_depth: int = OFFLOAD_MAX_SCAN_DEPTH):
    """Yield (path_tuple, size_bytes) for dict/list subtrees exceeding min_bytes.

    Non-mutating. Shallow heuristic: only descends while cumulative size still
    above min threshold and depth < max_depth to avoid excessive work.
    """
    try:
        size = _json_size_bytes(root)
    except Exception:  # pragma: no cover
        return
    if size < min_bytes:
        return
    # Emit this subtree as candidate
    yield (path, size)
    if depth >= max_depth:
        return
    # Recurse into children only if container
    if isinstance(root, dict):
        for k, v in root.items():
            if isinstance(v, (dict, list)):
                yield from _find_large_subtrees(v, min_bytes, path + (str(k),), depth + 1, max_depth)
    elif isinstance(root, list):
        # Sample first N elements (heuristic) to avoid O(n) on huge arrays
        for idx, v in enumerate(root[:10]):
            if isinstance(v, (dict, list)):
                yield from _find_large_subtrees(v, min_bytes, path + (str(idx),), depth + 1, max_depth)

def _telemetry_offload_candidates(instance: "BaseModel"):
    """Log (once per save call) candidate large subtrees for future offload.

    Only active when OFFLOAD_LARGE_JSON_ENABLED is False (pure telemetry phase).
    When we decide to enable, we'll replace this with actual offload + pointer
    replacement logic (e.g. {'_doc': {'sha256': ..., 'size': N, 'id': X}}).
    """
    if OFFLOAD_LARGE_JSON_ENABLED:
        return  # real implementation to be added when enabled
    for field_name in OFFLOAD_FIELDS:
        if not hasattr(instance, field_name):
            continue
        payload = getattr(instance, field_name)
        if not isinstance(payload, (dict, list)):
            continue
        # Determine field cap for relative threshold
        cap = {
            'metadata': MAX_METADATA_SIZE,
            'refs': MAX_REFS_SIZE,
            'prefs': MAX_PREFS_SIZE,
            'comments': MAX_METADATA_SIZE,  # comments shares metadata cap unless changed
        }.get(field_name, MAX_METADATA_SIZE)
        min_bytes = int(cap * OFFLOAD_MIN_FRACTION)
        for path_tuple, size in _find_large_subtrees(payload, min_bytes):
            logger.info(
                "%s candidate field=%s path=%s size=%d cap=%d frac=%.2f model=%s id=%s",  # structured log
                OFFLOAD_LOG_PREFIX,
                field_name,
                "/".join(path_tuple) or ".",
                size,
                cap,
                size / cap if cap else 0.0,
                instance.__class__.__name__,
                getattr(instance, 'pk', None),
            )

# ---------------- Optional Pydantic schema (graceful fallback) -------------
try:  # pragma: no cover - optional dependency
    from pydantic import BaseModel as PydanticBaseModel  # type: ignore
except ImportError:  # pragma: no cover
    PydanticBaseModel = None  # type: ignore


if PydanticBaseModel:  # pragma: no cover
    class UniversalAPISchema(PydanticBaseModel):  # type: ignore[misc]
        """Typed mirror of UniversalDictMixin output.

        Contribution:
        - Supplies static typing for service / integration layers.
        - Decouples outward contract from internal model implementation.
        - Allows progressive introduction of stricter validation without forcing runtime dep.
        """
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
else:  # pragma: no cover
    class UniversalAPISchema:  # type: ignore
        """Lightweight stub used when Pydantic is absent."""
        pass


# ---------------- Optimistic concurrency primitives ------------------------
class VersionConflictError(Exception):
    """Raised when an optimistic concurrency (version) check fails."""


class JSONBSet(Func):
    """Wrapper for PostgreSQL jsonb_set(target, path, new_value, create_missing).

    Contribution: Supports atomic partial JSON updates (AtomicJSONMixin) so we don't
    rewrite entire documents for small changes, reducing contention and I/O.
    """
    function = 'jsonb_set'
    template = "%(function)s(%(expressions)s)"
    arity = 4

    def __init__(self, target, path, new_value, create_missing: bool = True, **extra):
        expressions = [target, path, new_value, Value(create_missing)]
        super().__init__(*expressions, output_field=models.JSONField(), **extra)


# ---------------- Default envelope factories -------------------------------
def default_metadata() -> dict:
    """Baseline metadata structure (history, health, flags, versioning, undefined).

    Contribution: Ensures all BaseModel descendants have a predictable set of keys so
    generic serialization, diff tracking & keyword flags operate without key errors.
    """
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
            "synced": {"dt": 0, "contact_id": 0},
        },
        "health": {
            "rating": 0,
            "completeness": 0,
            "accuracy": 0,
            "freshness": 0,
            "consistency": 0,
        },
        "undefined": {},
    }


def default_refs() -> dict:
    """Lightweight relationship & classification structure (keywords/tags/links...)."""
    return {
        "keywords": [],
        "tags": [],
        "links": {"contacts": []},
        "categories": [],
        "related_ids": [],
    }


def default_prefs() -> dict:
    """User / system preference seed; intentionally sparse to stay evolvable."""
    return {"userdefined": ""}


def default_data() -> dict:  # reserved placeholder (not currently used)
    return {}


def default_comments() -> dict:
    """Structured comment / notes container.

    Contribution: Supports both quick single-field comment slots and an append-only
    notes list enabling audit / history without separate table (until needed).
    """
    return {
        "public": "",
        "process": "",
        "partner": "",
        "notes": [],
    }


# ---------------- Core + Mixins -------------------------------------------
class CoreModel(models.Model):
    """Identity + coarse timestamps + optimistic version (minimal contract).

    Contribution:
    - Forms required baseline (id / uuid / ida / created_dt / modified_dt / version).
    - Provides simple save() version bump; BaseModel later adds conditional diff logic.
    - Exposes optimistic helpers assert_version / optimistic_save for thin models.
    """

    feature_flags = {"core"}
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    ida = models.CharField(max_length=40, blank=True, db_index=True)
    created_dt = models.BigIntegerField(default=0, db_index=True)
    modified_dt = models.BigIntegerField(default=0, db_index=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        abstract = True

    _pydantic_cache: Optional[UniversalAPISchema] = None

    def save(self, *args, **kwargs):  # timestamp + version bump
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
        current = type(self).objects.filter(pk=self.pk).values_list("version", flat=True).first()
        if current is not None and current != expected_version:
            raise VersionConflictError(f"Version conflict: expected {expected_version} got {current}")

    def optimistic_save(self, expected_version: int | None = None, *args, **kwargs):
        if expected_version is not None and self.pk and self.version != expected_version:
            raise VersionConflictError(f"Version conflict: expected {expected_version} got {self.version}")
        return self.save(*args, **kwargs)

    def __str__(self):  # convenience for admin / debugging
        for attr in ("name", "title", "email", "ida", "uuid"):
            v = getattr(self, attr, None)
            if v:
                return str(v)
        return f"{self.__class__.__name__}#{self.pk or 'unsaved'}"

    # alias properties (future-proof naming) --------------------------------
    @property
    def dt_created(self):
        return self.created_dt

    @property
    def dt_modified(self):
        return self.modified_dt


class LifecycleMixin(models.Model):
    """Soft-delete / archive flags (reversible lifecycle state)."""

    feature_flags = {"lifecycle"}
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
    """Historized + flag / versioning capable metadata envelope."""

    feature_flags = {"metadata"}
    metadata = models.JSONField(default=default_metadata, help_text="Universal metadata envelope")

    class Meta:
        abstract = True

    def _init_metadata_if_needed(self):
        if not isinstance(self.metadata, dict):
            self.metadata = default_metadata()
        self.metadata.setdefault("history", default_metadata()["history"])
        self.metadata.setdefault("flags", {})
        self.metadata.setdefault("versioning", {})
        self.metadata["flags"].setdefault("schema_rev", 1)

    def save(self, *args, **kwargs):  # inject history
        creating = not self.pk
        now_ms = int(timezone.now().timestamp() * 1000)
        self._init_metadata_if_needed()
        hist = self.metadata["history"]
        hist["modified"] = {"dt": now_ms, "contact_id": getattr(self, "modified_by_id", 0)}
        if creating:
            hist["created"] = {"dt": now_ms, "contact_id": getattr(self, "created_by_id", 0)}
        super().save(*args, **kwargs)

    # helper accessors -----------------------------------------------------
    def get_history(self) -> dict:
        return self.metadata.get("history", {}) if isinstance(self.metadata, dict) else {}

    def get_metadata_value(self, key_path: str):
        keys = key_path.split(".")
        cur = self.metadata
        try:
            for k in keys:
                cur = cur[k]
            return cur
        except Exception:  # pragma: no cover - defensive
            return None

    def set_metadata_value(self, key_path: str, value):
        keys = key_path.split(".")
        target = self.metadata
        for k in keys[:-1]:
            target = target.setdefault(k, {})
        target[keys[-1]] = value

    def get_created_timestamp(self):
        return self.get_metadata_value("history.created.dt") or 0

    def get_modified_timestamp(self):
        return self.get_metadata_value("history.modified.dt") or 0

    @property
    def dt_verified(self):  # optional convenience accessor
        if not self.metadata:
            return None
        verified_dt_ms = self.metadata.get("history", {}).get("verified", {}).get("dt", 0)
        if verified_dt_ms:
            return timezone.datetime.fromtimestamp(verified_dt_ms / 1000, tz=timezone.utc)


class RefsMixin(models.Model):
    """Lightweight relationships & classification (keywords / tags / links)."""

    feature_flags = {"refs"}
    refs = models.JSONField(default=default_refs, help_text="Keywords / tags / lightweight links")

    class Meta:
        abstract = True

    def add_keyword(self, keyword: str):
        kw_lower = keyword.lower()
        existing = [k.lower() for k in self.refs.get("keywords", [])]
        if kw_lower not in existing:
            self.refs.setdefault("keywords", []).append(kw_lower)

    def add_tag(self, tag: str):
        if tag not in self.refs.get("tags", []):
            self.refs.setdefault("tags", []).append(tag)


class PrefsMixin(models.Model):
    """Per-record preference / settings envelope (experiment friendly)."""

    feature_flags = {"prefs"}
    prefs = models.JSONField(default=default_prefs, help_text="User preferences / settings")

    class Meta:
        abstract = True


class CommentsMixin(models.Model):
    """Structured comments & append-only notes list (audit assistance)."""

    feature_flags = {"comments"}
    comments = models.JSONField(default=default_comments, help_text="Threaded notes / comment fields")

    class Meta:
        abstract = True

    def add_note(self, note_type: str, text: str, by: int | str = "system"):
        if not isinstance(self.comments, dict):
            self.comments = default_comments()
        notes = self.comments.setdefault("notes", [])
        notes.append({
            "type": note_type,
            "text": text,
            "by": by,
            "dt": int(timezone.now().timestamp() * 1000),
        })
        # mirror last value for quick access
        self.comments[note_type] = text


class HealthMixin(models.Model):
    """Aggregated data quality score (single numeric rating for now)."""

    feature_flags = {"health"}
    health_rating = models.IntegerField(default=0, help_text="Data quality rating (0-100)")

    class Meta:
        abstract = True


class KeywordsMixin(models.Model):
    """Derives a capped keyword set from model text fields into refs.keywords."""

    feature_flags = {"keywords"}

    class Meta:
        abstract = True

    def mark_keywords_dirty(self):
        if hasattr(self, "metadata"):
            self.metadata.setdefault("flags", {})["keywords_pending"] = True  # type: ignore[attr-defined]

    @property
    def keywords_pending(self) -> bool:
        return bool(getattr(self, "metadata", {}).get("flags", {}).get("keywords_pending")) if hasattr(self, "metadata") else False

    def update_keywords(self):  # requires refs + metadata if present
        if not hasattr(self, "refs"):
            return
        keywords_set: set[str] = set()
        for field in self._meta.fields:  # type: ignore[attr-defined]
            if isinstance(field, (models.CharField, models.TextField)):
                val = getattr(self, field.name, "")
                if val:
                    for raw in str(val).lower().split():
                        token = raw.strip('.,!?;:"()[]{}')
                        if len(token) > 2:
                            keywords_set.add(token)
        self.refs.setdefault("keywords", [])  # type: ignore[attr-defined]
        self.refs["keywords"] = list(keywords_set)[:50]  # type: ignore[attr-defined]
        if hasattr(self, "metadata"):
            self.metadata.setdefault("flags", {})["keywords_pending"] = False  # type: ignore[attr-defined]
            self.metadata.setdefault("versioning", {})["keywords_refreshed_dt"] = int(timezone.now().timestamp() * 1000)  # type: ignore[attr-defined]


class AtomicJSONMixin(models.Model):
    """Atomic JSON patch helpers (partial jsonb updates + single version bump)."""

    feature_flags = {"atomic_json"}

    class Meta:
        abstract = True

    @classmethod
    def atomic_json_set(
        cls,
        pk: int,
        field: str,
        path: list[str],
        value,
        create_missing: bool = True,
        expected_version: int | None = None,
    ):
        if field not in {"metadata", "refs", "prefs", "comments"}:
            raise ValueError("field must be one of metadata, refs, prefs, comments")
        if not hasattr(cls, field):
            raise ValueError(f"Model {cls.__name__} has no field '{field}' for atomic update")
        path_literal = "{" + ",".join(path) + "}"
        with transaction.atomic():
            qs = cls.objects.select_for_update().filter(pk=pk)
            if expected_version is not None:
                qs = qs.filter(version=expected_version)
            updated = qs.update(
                **{
                    field: JSONBSet(F(field), Value(path_literal), Value(json.dumps(value)), True),
                    "version": F("version") + 1,
                    "modified_dt": int(timezone.now().timestamp() * 1000),
                }
            )
            if expected_version is not None and updated == 0:
                current = cls.objects.filter(pk=pk).values_list("version", flat=True).first()
                raise VersionConflictError(
                    f"Version conflict on atomic_json_set: expected {expected_version} got {current}"
                )
            if updated:
                new_version = cls.objects.filter(pk=pk).values_list("version", flat=True).first()
                return updated, new_version
            return updated, None

    @classmethod
    def atomic_list_append(
        cls,
        pk: int,
        field: str,
        path: list[str],
        element,
        max_length: int | None = None,
        expected_version: int | None = None,
    ):
        if field not in {"metadata", "refs", "prefs", "comments"}:
            raise ValueError("field must be one of metadata, refs, prefs, comments")
        if not hasattr(cls, field):
            raise ValueError(f"Model {cls.__name__} has no field '{field}' for atomic update")
        with transaction.atomic():
            obj = cls.objects.select_for_update().only("id", field, "version", "modified_dt").get(pk=pk)
            if expected_version is not None and obj.version != expected_version:  # type: ignore[attr-defined]
                raise VersionConflictError(
                    f"Version conflict on atomic_list_append: expected {expected_version} got {obj.version}"  # type: ignore[attr-defined]
                )
            target = getattr(obj, field)
            cur = target
            for key in path[:-1]:
                cur = cur.setdefault(key, {})
            arr_key = path[-1]
            arr = cur.setdefault(arr_key, [])
            if not isinstance(arr, list):
                raise ValueError("Target JSON path is not a list")
            arr.append(element)
            if max_length is not None and len(arr) > max_length:
                del arr[0 : len(arr) - max_length]
            obj.save(update_fields=[field, "version", "modified_dt"])
            return obj.version  # type: ignore[attr-defined]

    # Instance convenience wrappers ----------------------------------------
    def atomic_set(
        self,
        field: str,
        path: list[str],
        value,
        create_missing: bool = True,
        expected_version: int | None = None,
    ):
        updated, new_version = type(self).atomic_json_set(
            self.pk, field, path, value, create_missing, expected_version=expected_version  # type: ignore[arg-type]
        )
        if updated:
            self.refresh_from_db(fields=[field, "version", "modified_dt"])
            if hasattr(self, "_pydantic_cache"):
                self._pydantic_cache = None  # type: ignore[attr-defined]
        return new_version

    def atomic_append(
        self,
        field: str,
        path: list[str],
        element,
        max_length: int | None = None,
        expected_version: int | None = None,
    ):
        new_version = type(self).atomic_list_append(
            self.pk, field, path, element, max_length=max_length, expected_version=expected_version  # type: ignore[arg-type]
        )
        self.refresh_from_db(fields=[field, "version", "modified_dt"])
        if hasattr(self, "_pydantic_cache"):
            self._pydantic_cache = None  # type: ignore[attr-defined]
        return new_version


class UniversalDictMixin(models.Model):
    """Stable outward serialization (universal dict) + optional Pydantic conversion."""

    feature_flags = {"universal_dict"}

    class Meta:
        abstract = True

    def to_universal_dict(self) -> Dict[str, Any]:
        base = {
            "id": self.pk,
            "uuid": str(getattr(self, "uuid", "")) or None,
            "ida": getattr(self, "ida", ""),
            "dt_created": getattr(self, "created_dt", None),
            "dt_modified": getattr(self, "modified_dt", None),
            "version": getattr(self, "version", None),
        }
        if hasattr(self, "metadata"):
            meta = getattr(self, "metadata") or {}
            history = meta.get("history", {}) if isinstance(meta, dict) else {}
            base.update(
                {
                    "metadata": meta,
                    "dt_created": history.get("created", {}).get("dt") or base["dt_created"],
                    "dt_modified": history.get("modified", {}).get("dt") or base["dt_modified"],
                }
            )
            changed = meta.get("versioning", {}).get("changed_fields") if isinstance(meta, dict) else None
            if changed:
                base["changed_fields"] = changed
        for opt in ("refs", "prefs", "comments", "health_rating"):
            if hasattr(self, opt):
                base[opt] = getattr(self, opt)
        return base

    def as_pydantic(self, refresh: bool = False):
        if not PydanticBaseModel:
            return self.to_universal_dict()
        if refresh or getattr(self, "_pydantic_cache", None) is None:
            self._pydantic_cache = UniversalAPISchema(**self.to_universal_dict())  # type: ignore[arg-type]
        return self._pydantic_cache

    def pydantic_dump(self, *args, **kwargs) -> Dict[str, Any]:
        obj = self.as_pydantic()
        if hasattr(obj, "model_dump"):
            return obj.model_dump(*args, **kwargs)  # type: ignore[attr-defined]
        return cast(Dict[str, Any], obj)

    # --- Universal API hooks (generalized) ---------------------------------
    def pre_save_hook(self, data: Dict[str, Any]):  # invoked by save endpoint before obj.save()
        """Optional early mutation/validation hook.

        Return a string (error message) to abort save with HTTP 400, or None to continue.
        Override in concrete models for domain-specific checks (lightweight; avoid heavy DB queries).
        """
        return None

    def api_validate_payload(self, data: Dict[str, Any], is_update: bool):  # consumed when UNIVERSAL_API_VALIDATE enabled
        """Default validation hook for all BaseModel descendants.

        Returns (ok: bool, errors: list[str]). Override to enforce schema rules.
        By default always returns success (no validation performed).

        Suggested override signature:
            def api_validate_payload(self, data, is_update):
                errors = []
                # add field checks -> errors.append('field: issue')
                return (not errors, errors)
        """
        return True, []

    def post_save_hook(self, data: Dict[str, Any]):  # invoked by save endpoint immediately after obj.save()
        """Optional post-persist hook for synchronous side-effects.

        Return a string (warning/info) to append to response messages list. Errors should be rare; raise only for critical rollback scenarios.
        Override in models needing immediate follow-up (e.g., propagate denormalized counters). Heavy work should be deferred to async task queue.
        """
        return None


# ---------------- Full composition ----------------------------------------
class BaseModel(
    CoreModel,
    MetadataMixin,
    RefsMixin,
    PrefsMixin,
    CommentsMixin,
    HealthMixin,
    KeywordsMixin,
    LifecycleMixin,
    UniversalDictMixin,
    AtomicJSONMixin,
):
    """Full capability base: adds JSON envelopes, search keywords, lifecycle & atomic ops.

    Additional responsibilities over CoreModel:
    - changed_fields tracking persisted inside metadata.versioning.changed_fields
    - size enforcement & warning logs per JSON envelope
    - touch() helper (update modified_dt only) avoiding a version bump
    - keyword dirtiness marking on save (for async refresh flows)
    """

    class Meta:
        abstract = True
        indexes = [
            GinIndex(fields=["refs"], name="refs_gin_idx"),
            GinIndex(fields=["prefs"], name="prefs_gin_idx"),
        ]

    # QuerySet / Manager providing convenience filters for lifecycle + keyword flag
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
        def get_queryset(self):  # type: ignore[override]
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

    # --- change tracking --------------------------------------------------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._capture_original_state()

    def _capture_original_state(self):
        self._original_state: Dict[str, Any] = {}
        for f in self._meta.fields:  # type: ignore[attr-defined]
            try:
                self._original_state[f.name] = getattr(self, f.name)
            except Exception:  # pragma: no cover
                pass
        self._original_created_dt = self._original_state.get("created_dt")

    def _compute_changed_fields(self) -> list[str]:
        changed: list[str] = []
        if not getattr(self, "_original_state", None):
            return changed
        auto_exclude = {"modified_dt", "version"}
        for f in self._meta.fields:  # type: ignore[attr-defined]
            name = f.name
            if name in auto_exclude:
                continue
            old = self._original_state.get(name)
            new = getattr(self, name)
            if old != new:
                changed.append(name)
        return changed

    def save(self, *args, **kwargs):  # orchestrate save chain
        expected_version = kwargs.pop("expected_version", None)
        if expected_version is not None and self.pk:
            current = type(self).objects.filter(pk=self.pk).values_list("version", flat=True).first()
            if current is not None and current != expected_version:
                raise VersionConflictError(
                    f"Version conflict: expected {expected_version} got {current}"
                )
        # created_dt immutability guard
        if self.pk and hasattr(self, "_original_created_dt") and self.created_dt != self._original_created_dt:  # type: ignore[attr-defined]
            self.created_dt = self._original_created_dt  # type: ignore[attr-defined]
        # attach changed_fields for updates
        if self.pk and isinstance(getattr(self, "metadata", None), dict):
            changed_fields = self._compute_changed_fields()
            if changed_fields:
                ver = self.metadata.setdefault("versioning", {})  # type: ignore[attr-defined]
                ver["changed_fields"] = changed_fields
        super().save(*args, **kwargs)
        # refresh snapshot
        self._capture_original_state()

        # size enforcement
        def check_size(field_value, max_size, field_name):
            """Log progressive size thresholds and enforce hard cap.

            Threshold telemetry (30/60/75%) logged once per field per object as it
            crosses each boundary; last logged fraction persisted in metadata.versioning.size_activity.
            75% is elevated to warning (legacy behavior kept); earlier thresholds are info.
            """
            try:
                size = len(json.dumps(field_value, separators=(",", ":")).encode("utf-8"))
            except Exception:
                return
            if size > max_size:
                raise ValueError(f"{field_name} exceeds maximum size of {max_size} bytes")
            # Determine previously logged fraction (if metadata available)
            last_frac = 0.0
            meta_container = None
            if hasattr(self, "metadata") and isinstance(getattr(self, "metadata"), dict):  # type: ignore[attr-defined]
                meta_container = self.metadata.setdefault("versioning", {}).setdefault("size_activity", {})  # type: ignore[attr-defined]
                last_frac = float(meta_container.get(field_name, 0.0)) if isinstance(meta_container.get(field_name, 0.0), (int, float, str)) else 0.0
            for frac in SIZE_ACTIVITY_FRACTIONS:
                threshold_bytes = max_size * frac
                if size >= threshold_bytes and frac > last_frac:
                    log_args = (
                        f"{field_name} size {size}B ({(size / max_size) * 100:.1f}% of {max_size}) crossed {int(frac*100)}% threshold for {self.__class__.__name__} id={self.pk}",
                    )
                    if frac >= SIZE_WARN_FRACTION:
                        logger.warning(*log_args)
                    else:
                        logger.info(*log_args)
                    if meta_container is not None:
                        meta_container[field_name] = frac
            # (Optional) could persist updated metadata only if modified; rely on normal save path for now.

        if hasattr(self, "metadata"):
            check_size(self.metadata, MAX_METADATA_SIZE, "metadata")  # type: ignore[attr-defined]
        if hasattr(self, "refs"):
            check_size(self.refs, MAX_REFS_SIZE, "refs")  # type: ignore[attr-defined]
        if hasattr(self, "prefs"):
            check_size(self.prefs, MAX_PREFS_SIZE, "prefs")  # type: ignore[attr-defined]

        if isinstance(self, KeywordsMixin):
            self.mark_keywords_dirty()

        # Telemetry for future large JSON offload (no mutation while disabled)
        try:
            _telemetry_offload_candidates(self)
        except Exception:  # pragma: no cover - never block save
            logger.debug("offload telemetry failed", exc_info=True)

    def touch(self, update_fields: list[str] | None = None):  # modified_dt without version bump
        if not self.pk:
            return
        now_ms = int(timezone.now().timestamp() * 1000)
        update_map = {"modified_dt": now_ms}
        if update_fields:
            for field in update_fields:
                if field in {"version", "created_dt"}:
                    continue
                update_map[field] = getattr(self, field)
        type(self).objects.filter(pk=self.pk).update(**update_map)
        self.modified_dt = now_ms  # type: ignore[attr-defined]
        self._capture_original_state()


# Slim alias (for clarity when declaring lightweight models)
SlimBaseModel = CoreModel


# ---------------- Capability discovery helper -----------------------------
def model_capabilities(model_or_instance) -> list[str]:
    cls = model_or_instance if inspect.isclass(model_or_instance) else model_or_instance.__class__
    caps: set[str] = set()
    for base in cls.mro():
        if hasattr(base, "feature_flags"):
            flags = getattr(base, "feature_flags")
            if isinstance(flags, Iterable):
                caps.update(flags)
    return sorted(caps)