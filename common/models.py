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
from django.db.models.fields.json import KeyTextTransform
import logging
import uuid
import inspect
import json
from typing import Any, Dict, Optional, Iterable, cast
from common.ignore_fields import IGNORE_FIELDS, IGNORE_WORDS

# ---------------- Size / warning thresholds ----------------
# YYY Review by 2026-03-01
MAX_METADATA_SIZE = 128000  # bytes
# larger data items should be driven into documents and linked
MAX_REFS_SIZE = 64000
MAX_PREFS_SIZE = 96000 # max prefs
MAX_CONFIG_SIZE = 64000  # config — application data; larger content → Document record
MAX_ACTIONS_SIZE = 32000  # actions JSON should remain small and query-friendly
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
            'config': MAX_CONFIG_SIZE,
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
        actions: Dict[str, Any] | None = None
        health_rating: Optional[int] = 0
        dt_created: Optional[int] = None
        dt_modified: Optional[int] = None
        version: Optional[int] = None
        is_active: Optional[bool] = None

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
        "resources": {  # planning stub
            "required": {},
            "allocated": {},
        },
    # Cross-cutting operational context (lightweight, rarely indexed)
    # Moved here to avoid schema churn and keep non-critical fields uniform across all models.
    # Canonical keys; specific apps can mirror or promote to columns when needed for performance.
    "flow": {},   # e.g., lineage hints, parent/child hops for reporting
    "source": {}, # e.g., campaign/vendor/manufacturer attribution for analytics
        "images": {
            "primary": "",      # hero image path
            "gallery": [],      # additional view paths
            "thumbnail": "",    # list/grid display path
        },
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
        # Erosion annotations — lightweight per-record value-loss tracking.
        # small_stings: minor customer-base erosions (discounts, overrides, rounding)
        # erosions: significant erosion events (margin loss, late payment, rework, bad debt)
        # Each entry: {"category": str, "amount": float, "dt": ms_epoch, "note": str, "erosion_id": int|null}
        # erosion_id is null until the record is saved; BaseModel.post_save_hook
        # then creates the Erosion row and writes the id back.
        "small_stings": [],
        "erosions": [],
        # Temporary snippets/hints for short-lived UX helpers.
        # Each entry should include clear_dt (epoch ms) so background cleanup can prune it.
        "temp": [],
        "undefined": {},
    }


def default_document_metadata() -> dict:
    """Extended metadata structure for Document model.
    
    Includes base metadata plus document-specific fields:
    - address: Physical location/geolocation where document was created
    - virus: Malware scan status and results
    - exif: Extracted EXIF data from images
    """
    base = default_metadata()
    base.update({
        # Physical address / geolocation provenance
        "address": {
            "street": "",
            "street2": "",
            "city": "",
            "state": "",
            "postal_code": "",
            "country": "",
            "geo": {
                "lat": None,        # latitude
                "lng": None,        # longitude  
                "altitude": None,   # meters above sea level
                "accuracy": None,   # GPS accuracy in meters
            },
            "source": "",  # "exif" | "manual" | "gps" | "ip_lookup" | "browser"
            "captured_at": 0,  # timestamp when location was captured
        },
        # Virus/malware scan status
        "virus": {
            "status": "pending",  # "pending" | "scanning" | "clean" | "infected" | "error" | "skipped"
            "scanner": "",         # e.g., "clamav", "virustotal", "windows_defender"
            "scanner_version": "",
            "scanned_at": 0,       # timestamp of last scan
            "threat": None,        # threat name if infected
            "quarantined": False,  # whether file was quarantined
            "details": {},         # scanner-specific details
        },
        # EXIF metadata extracted from images
        "exif": {
            "camera_make": "",
            "camera_model": "",
            "lens": "",
            "focal_length": None,
            "aperture": None,
            "shutter_speed": "",
            "iso": None,
            "flash": False,
            "orientation": 1,
            "width": None,
            "height": None,
            "datetime_original": 0,  # when photo was taken
            "datetime_digitized": 0,
            "software": "",
            "copyright": "",
            "raw": {},  # full raw EXIF data
        },
    })
    return base


def default_refs() -> dict:
    """Lightweight relationship & classification structure (keywords/tags/links...)."""
    return {
        "keywords": [],
        #setting used to build keywords
        #"self_fields": ["canonical_key"],
        #"related_keywords": {},
        "tags": [],
        "links": {"contact": [], "item": []},
        #setting record populates links from #"related_models": []

        # Parent action IDs for Gantt dependencies (finish-to-start links)
        # These specify which actions must complete before this action can start
        "parents": [],

        # Execution gating: identify upstream dependencies by model keys.
        # Example: {"action": [1,2], "work_order": [5], "work_order_line": [9,10]}
        "depends_on": {},
        "categories": [],
        "related_ids": [],
    }


# Denormalization fields for links — single source of truth lives in common.denorm_registry.
# This dict is populated from the registry so legacy callers keep working.
from common.denorm_registry import DENORM_REGISTRY as _DENORM_REGISTRY  # noqa: E402
LINK_DENORMALIZE_FIELDS = {k: list(v) for k, v in _DENORM_REGISTRY.items()}


def default_prefs() -> dict:
        """User / system preference seed; intentionally sparse to stay evolvable.

        Shape: prefs.userdefined is a dict mapping unique keys to values, e.g.,
            {"foo": "bar"}
        """
        return {"userdefined": {}}


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
    - Forms required baseline (id / uuid / ida / dt_created / dt_modified / version).
    - Provides simple save() version bump; BaseModel later adds conditional diff logic.
    - Exposes optimistic helpers assert_version / optimistic_save for thin models.
    """

    feature_flags = {"core"}
    #unique per data system.
    id = models.BigAutoField(primary_key=True)
    # exchanged between data systems (if any). Nullable for safe backfill; generated in save() when missing.
    uuid = models.UUIDField(editable=False, unique=True, null=True, blank=True)
    #soft id from external system (if any)
    ida = models.CharField(max_length=40, blank=True, db_index=True)
    dt_created = models.BigIntegerField(default=0, db_index=True)
    dt_modified = models.BigIntegerField(default=0, db_index=True)
    version = models.PositiveIntegerField(default=1)
    # Unified active flag (subclasses can override default or help_text). Not all models currently
    # declare this; adding here allows a consistent queryset helper. If a concrete model already
    # defines is_active, its field overrides this definition (no duplicate schema field in migration).
    is_active = models.BooleanField(default=True, db_index=True, help_text="Record is logically active")
    security_level = models.IntegerField(default=0, blank=True, db_index=True, help_text="Security level or classification")
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Application data container — form fields, type-specific content, user-managed data. "
                  "Separate from metadata (system behavior) by design."
    )
    # Legacy suffix style (dt_created / dt_modified) fully removed; ALWAYS use dt_created / dt_modified.

    class Meta:
        abstract = True

    _pydantic_cache: Optional[UniversalAPISchema] = None

    def save(self, *args, **kwargs):
        now_ms = int(timezone.now().timestamp() * 1000)
        if not self.pk:
            # New record
            self.dt_created = now_ms
            # Assign uuid on creation if not set
            if not self.uuid:
                self.uuid = uuid.uuid4()
        else:
            # Existing record — uuid is immutable after creation
            if self.uuid:
                try:
                    orig_uuid = type(self).objects.filter(pk=self.pk).values_list('uuid', flat=True).first()
                    if orig_uuid and self.uuid != orig_uuid:
                        raise ValueError(f"uuid is immutable: cannot change {orig_uuid} to {self.uuid}")
                except type(self).DoesNotExist:
                    pass
            self.version = (self.version or 0) + 1
        self.dt_modified = now_ms
        super().save(*args, **kwargs)
        # Ensure ida is never null — default to string of id
        try:
            if hasattr(self, 'ida') and (not getattr(self, 'ida')) and self.pk:
                from common.ida import generate_ida
                # Training mode: use qq prefix if marker set by save_view
                training_prefix = getattr(self, '_training_prefix', None)
                if training_prefix:
                    ida_value = f"qq{generate_ida(self.pk)}"
                else:
                    ida_value = generate_ida(self.pk)
                type(self).objects.filter(pk=self.pk, ida="").update(ida=ida_value)
                self.ida = ida_value
        except Exception:  # pragma: no cover - never block save
            logger.debug("ida autogeneration failed", exc_info=True)
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
        for attr in ("display_name", "name", "title", "email", "ida", "uuid"):
            v = getattr(self, attr, None)
            if v:
                return str(v)
        return f"{self.__class__.__name__}#{self.pk or 'unsaved'}"

    # Removed historical alias properties for dt_created/dt_modified; dt_created/dt_modified are the canonical fields.


class LifecycleMixin(models.Model):
    """Soft-delete / archive / lock flags (reversible lifecycle state)."""

    feature_flags = {"lifecycle"}
    is_deleted = models.BooleanField(default=False, db_index=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    is_locked = models.BooleanField(default=False, db_index=True, help_text="Record is locked and cannot be edited (admin override required)")

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

    def lock(self):
        """Lock the record to prevent edits (admin can unlock)."""
        self.is_locked = True
        self.save()

    def unlock(self):
        """Unlock the record to allow edits (admin action)."""
        self.is_locked = False
        self.save()


class ConfigMixin(models.Model):
    """Application data container — separate from metadata by design.

    metadata = how the record BEHAVES (workflow state, flags, history, schema)
    config   = what the record CONTAINS (form data, type-specific fields, user content)

    Why two fields:
    - metadata has system scaffolding (_init_metadata_if_needed) that auto-populates
      history, flags, versioning, flow, source, resources, small_stings, erosions.
      Mixing application data into metadata risks collisions and makes it hard to
      know what's system-managed vs user-managed.
    - config is a clean JSON dict with no auto-scaffolding. The application owns it
      entirely. Alice reads it to understand the record. The .tsx page writes it
      from form fields. No system code touches it unless the application asks.

    Examples:
    - Action (quality_type=ncr): config holds item_name, actual_condition, disposition
    - Action (quality_type=car): config holds root_cause, proposed_action, verification
    - Item: config holds vendor-specific specs, certifications, handling instructions
    - Contact: config holds role-specific fields per business type
    - Document: config holds template variables, print options, audience tags

    This field lives on BaseModel so every model has it from day one.
    No per-model migrations. No "does this model have config?" questions.

    Gordy Israelson's nuclear quality discipline digitized: the form data for every
    NCR, CAR, deviation, and document change request lives here. The workflow state
    stays in metadata. Clean separation. No collisions.
    """

    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Application data container — form fields, type-specific content, user-managed data. "
                  "Separate from metadata (system behavior) by design."
    )

    class Meta:
        abstract = True


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
        # Ensure cross-cutting context containers exist (read/write without KeyError)
        self.metadata.setdefault("flow", {})
        self.metadata.setdefault("source", {})
    # Note: actionable next-step data now lives in ActionsMixin.actions JSON
    # to keep semantics clear and indexing straightforward.

        # Ensure resources planning scaffold exists
        res = self.metadata.setdefault("resources", {})
        if isinstance(res, dict):
            res.setdefault("required", {})
            res.setdefault("allocated", {})
        # Ensure erosion annotation arrays exist
        self.metadata.setdefault("small_stings", [])
        self.metadata.setdefault("erosions", [])
        self.metadata.setdefault("temp", [])
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

    # convenience accessors for common context blocks ---------------------
    def get_flow(self) -> dict:
        return self.metadata.get("flow", {}) if isinstance(self.metadata, dict) else {}

    def set_flow(self, value: dict):
        if not isinstance(self.metadata, dict):
            self.metadata = default_metadata()
        self.metadata["flow"] = value or {}

    def get_source(self) -> dict:
        return self.metadata.get("source", {}) if isinstance(self.metadata, dict) else {}

    def set_source(self, value: dict):
        if not isinstance(self.metadata, dict):
            self.metadata = default_metadata()
        self.metadata["source"] = value or {}

    # metadata.temp helpers --------------------------------------------------
    def get_temp_entries(self) -> list[dict]:
        if not isinstance(self.metadata, dict):
            return []
        entries = self.metadata.get("temp", [])
        if not isinstance(entries, list):
            return []
        return [e for e in entries if isinstance(e, dict)]

    def add_temp_entry(
        self,
        kind: str,
        snippet: str,
        *,
        clear_dt: int | None = None,
        ttl_days: int = 30,
        source: str = "alice",
        extra: dict | None = None,
    ) -> dict:
        """Append a temporary metadata snippet with required clear-by timestamp.

        clear_dt is epoch milliseconds. If omitted, ttl_days from now is used.
        """
        now_ms = int(timezone.now().timestamp() * 1000)
        if clear_dt is None:
            clear_dt = now_ms + (max(ttl_days, 1) * 24 * 60 * 60 * 1000)

        if not isinstance(self.metadata, dict):
            self.metadata = default_metadata()
        self._init_metadata_if_needed()

        entry = {
            "id": str(uuid.uuid4()),
            "kind": kind or "hint",
            "snippet": snippet or "",
            "source": source or "alice",
            "dt_created": now_ms,
            "clear_dt": int(clear_dt),
        }
        if isinstance(extra, dict) and extra:
            entry["extra"] = extra

        temp_list = self.metadata.setdefault("temp", [])
        if not isinstance(temp_list, list):
            temp_list = []
            self.metadata["temp"] = temp_list
        temp_list.append(entry)
        return entry

    def clear_expired_temp_entries(self, now_ms: int | None = None) -> int:
        """Remove expired metadata.temp entries in-memory and return count removed."""
        if not isinstance(self.metadata, dict):
            return 0
        temp = self.metadata.get("temp", [])
        if not isinstance(temp, list):
            self.metadata["temp"] = []
            return 0

        if now_ms is None:
            now_ms = int(timezone.now().timestamp() * 1000)

        kept: list[dict] = []
        removed = 0
        for entry in temp:
            if not isinstance(entry, dict):
                removed += 1
                continue
            clear_dt = entry.get("clear_dt")
            try:
                clear_dt_int = int(clear_dt)
            except (TypeError, ValueError):
                # Invalid entries are considered expired to avoid permanent clutter.
                removed += 1
                continue
            if clear_dt_int <= now_ms:
                removed += 1
                continue
            kept.append(entry)

        if removed:
            self.metadata["temp"] = kept
        return removed

 


    def get_created_timestamp(self):
        return self.get_metadata_value("history.created.dt") or 0

    def get_modified_timestamp(self):
        return self.get_metadata_value("history.modified.dt") or 0

    @property
    def dt_verified(self):  # optional convenience accessor
        if not self.metadata:
            return None
        dt_verified_ms = self.metadata.get("history", {}).get("verified", {}).get("dt", 0)
        if dt_verified_ms:
            return timezone.datetime.fromtimestamp(dt_verified_ms / 1000, tz=timezone.utc)


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

    def denormalize_links(self) -> dict:
        """Return refs.links with denormalized objects instead of just IDs.

        For each model in links, fetches the related objects and includes
        the specified fields from LINK_DENORMALIZE_FIELDS.
        """
        links = self.refs.get("links", {}) if isinstance(self.refs, dict) else {}
        if not isinstance(links, dict):
            return {}

        denormalized = {}
        for model_name, items in links.items():
            if not isinstance(items, list):
                denormalized[model_name] = items
                continue

            # Check if already denormalized (first item is dict)
            if items and isinstance(items[0], dict):
                denormalized[model_name] = items
                continue

            # It's a list of IDs, denormalize
            ids = items
            fields = LINK_DENORMALIZE_FIELDS.get(model_name.lower(), ["id"])
            if not ids:
                denormalized[model_name] = []
                continue

            # Get the model class
            try:
                from django.apps import apps
                model_class = apps.get_model(model_name)
            except Exception:
                # If model not found, convert to dicts with just id
                denormalized[model_name] = [{"id": id_} for id_ in ids]
                continue

            # Fetch objects
            objects = model_class.objects.filter(id__in=ids).values(*fields)
            obj_dict = {obj["id"]: obj for obj in objects}

            # Build denormalized list in original order
            denormalized[model_name] = [obj_dict.get(id_, {"id": id_}) for id_ in ids]

        return denormalized

    def ensure_links_denormalized(self):
        """Ensure refs.links are denormalized, updating in place if needed."""
        if not isinstance(self.refs, dict):
            return
        links = self.refs.get("links")
        if isinstance(links, dict):
            self.refs["links"] = self.denormalize_links()


class PrefsMixin(models.Model):
    """Per-record preference / settings envelope (experiment friendly)."""

    feature_flags = {"prefs"}
    prefs = models.JSONField(default=default_prefs, help_text="User preferences / settings")

    class Meta:
        abstract = True

class ActionsMixin(models.Model):

    """Actionable flags & next-step metadata (frequently searched).

    Semantics:
    - Keep frequently queried fields near the root of actions for easy indexing, e.g.:
        {
          "required": true,
          "status": "pending|done|blocked",
          "who": 123,          # contact_id or username
          "when": 1737052800000, # ms epoch for due/next
          "what": "call vendor",
          "kind": "followup|review|ship|approve",
          "extra": { ... }     # free-form per domain
        }
    - Empty object {} means no action required.
    - Prefer small payloads (<32KB) for performance.
    """

    feature_flags = {"actions"}
    actions = models.JSONField(default=dict, blank=True, help_text="Next action metadata (searchable)")

    class Meta:
        abstract = True

    # convenience accessors
    def get_action(self) -> dict:
        return self.actions or {}

    def set_action(self, value: dict | None):
        self.actions = value or {}

class CommentsMixin(models.Model):
    """Structured comments & append-only notes list (audit assistance)."""

    feature_flags = {"comments"}
    comments = models.JSONField(default=default_comments, help_text="Threaded notes / comment fields")

    class Meta:
        abstract = True

    # ---- Internal helpers -------------------------------------------------
    def _ensure_comment_root(self):  # pragma: no cover trivial
        if not isinstance(self.comments, dict):
            self.comments = {}
        # QQQ general is about the records
        self.comments.setdefault('general', {})
        self.comments.setdefault('records', {})
        for ch in ('public', 'process', 'foreign'):
            self.comments['general'].setdefault(ch, [])

    @staticmethod
    def _clip_comment_text(txt: str) -> str:
        if not isinstance(txt, str):
            txt = str(txt)
        return txt[:255]

    def _get_linkage_id(self) -> int | None:
        """Return linkage id if present in refs.links.linkage[0].

        Handles both raw int format [1] and denormalized dict format [{"id": 1}].
        """
        if not hasattr(self, 'refs'):
            return None
        refs = getattr(self, 'refs') or {}
        if not isinstance(refs, dict):
            return None
        links = refs.get('links') or {}
        if not isinstance(links, dict):
            return None
        linkage_list = links.get('linkage') or []
        if isinstance(linkage_list, list) and linkage_list:
            first = linkage_list[0]
            if isinstance(first, dict):
                return first.get('id')
            return first
        return None

    # ---- Public API -------------------------------------------------------
    def add_comment(self,
                    channel: str,
                    text: str,
                    by: str | int = 'system',
                    model: str | None = None,
                    record_id: int | None = None,
                    scope: str = 'auto',
                    source: str | None = None,
                    use_linkage: bool = True) -> dict:
        """Add a comment to this record or its linkage hub if present.

        channel: public|process|foreign (defaults to public if invalid)
        scope: 'general' | 'record' | 'auto'. 'auto' chooses 'record' when model & record_id provided.
        If use_linkage and a linkage id is attached, comment is routed to linkage record
        (centralized cross-table feed). Fallback: local comments JSON.
        Returns stored comment entry.
        """
        channel = channel if channel in ('public', 'process', 'foreign') else 'public'
        clipped = self._clip_comment_text(text)
        linkage_id = self._get_linkage_id() if use_linkage else None
        if linkage_id:
            try:
                from apps.docs.models.linkage_entry import LinkageEntry  # local import to avoid cycles
                linkage = LinkageEntry.objects.filter(pk=linkage_id).first()
                if linkage:
                    return linkage.add_comment(channel=channel, text=clipped, by=str(by), model=model, record_id=record_id, scope=scope, source=source)
            except Exception:  # pragma: no cover
                pass
        # Fallback local storage
        self._ensure_comment_root()
        target_container = None
        if scope == 'general' or (scope == 'auto' and not (model and record_id)):
            target_container = self.comments['general']
        else:
            rec_key = f"{model}/{record_id}" if model and record_id else None
            if rec_key is None:
                target_container = self.comments['general']
            else:
                rec_bucket = self.comments['records'].setdefault(rec_key, {})
                for ch in ('public', 'process', 'foreign'):
                    rec_bucket.setdefault(ch, [])
                target_container = rec_bucket
        entry = {
            'ts': timezone.now().isoformat().replace('+00:00', 'Z'),
            'by': by,
            'text': clipped,
        }
        if source:
            entry['source'] = source
        target_container[channel].append(entry)  # type: ignore[index]
        self.save(update_fields=['comments', 'dt_modified', 'version'])  # type: ignore[attr-defined]
        return entry

    # Backwards compatibility wrapper
    def add_note(self, note_type: str, text: str, by: int | str = "system"):
        return self.add_comment(channel=note_type, text=text, by=by, scope='general')

    def aggregated_comments(self) -> dict:
        """Return linkage aggregated comments if linkage present, else local."""
        linkage_id = self._get_linkage_id()
        if linkage_id:
            try:
                from apps.docs.models.linkage_entry import LinkageEntry
                linkage = LinkageEntry.objects.filter(pk=linkage_id).first()
                if linkage:
                    return linkage.aggregated_comment_summary()
            except Exception:  # pragma: no cover
                pass
        # ensure local structure for callers
        self._ensure_comment_root()
        return self.comments


class HealthMixin(models.Model):
    """Aggregated data quality score (single numeric rating for now)."""

    feature_flags = {"health"}
    health_rating = models.IntegerField(default=0, help_text="Data quality rating (0-100)")

    class Meta:
        abstract = True

# QQQ 
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

    def _extract_strings_recursive(self, value: Any) -> list[str]:
        """Recursively extract all string values from a value, handling arrays and objects."""
        strings = []
        if isinstance(value, str):
            # Try to parse as JSON first
            try:
                parsed = json.loads(value)
                strings.extend(self._extract_strings_recursive(parsed))
            except (json.JSONDecodeError, TypeError):
                # Not JSON, treat as regular string
                strings.append(value)
        elif isinstance(value, (list, tuple)):
            for item in value:
                strings.extend(self._extract_strings_recursive(item))
        elif isinstance(value, dict):
            for v in value.values():
                strings.extend(self._extract_strings_recursive(v))
        elif value is not None:
            # Convert other types to string
            strings.append(str(value))
        return strings

    def update_keywords(self):  # requires refs + metadata if present
        try:
            if not hasattr(self, "refs"):
                logging.getLogger(__name__).warning('No refs field found for %s', self.__class__.__name__)
                return
            
            # Clear previous keywords list to ensure fresh generation
            self.refs.setdefault("keywords", [])
            self.refs["keywords"] = []
            
            logging.getLogger(__name__).info('Starting keyword generation for %s id=%s', self.__class__.__name__, getattr(self, 'id', None))
            
            # Import the keyword service function
            from apps.core.services.keywords import build_keywords_for_record
            
            # Get model name for the keyword service
            model_name = self.__class__.__name__.lower()
            
            # Generate keywords using the configuration-based system
            keywords_list = build_keywords_for_record(model_name, self.id)
            
            # Update refs with new keywords
            self.refs["keywords"] = keywords_list
            
            logging.getLogger(__name__).info('Keyword generation completed for %s id=%s. Generated %d keywords: %s',
                                           self.__class__.__name__, getattr(self, 'id', None),
                                           len(keywords_list), keywords_list[:10])  # Log first 10 keywords
            
            if hasattr(self, "metadata"):
                self.metadata.setdefault("flags", {})["keywords_pending"] = False  # type: ignore[attr-defined]
                self.metadata.setdefault("versioning", {})["keywords_dt_refreshed"] = int(timezone.now().timestamp() * 1000)  # type: ignore[attr-defined]
            
            logging.getLogger(__name__).info('update_keywords completed successfully for %s id=%s',
                                           self.__class__.__name__, getattr(self, 'id', None))
        except Exception as e:
            logging.getLogger(__name__).exception('Exception in update_keywords for %s id=%s: %s',
                                                self.__class__.__name__, getattr(self, 'id', None), str(e))


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
        if field not in {"metadata", "refs", "prefs", "comments", "actions"}:
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
                    "dt_modified": int(timezone.now().timestamp() * 1000),
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
        if field not in {"metadata", "refs", "prefs", "comments", "actions"}:
            raise ValueError("field must be one of metadata, refs, prefs, comments")
        if not hasattr(cls, field):
            raise ValueError(f"Model {cls.__name__} has no field '{field}' for atomic update")
        with transaction.atomic():
            obj = cls.objects.select_for_update().only("id", field, "version", "dt_modified").get(pk=pk)
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
            obj.save(update_fields=[field, "version", "dt_modified"])
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
            self.refresh_from_db(fields=[field, "version", "dt_modified"])
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
        """Append an element to a JSON array path atomically.

        Convenience instance wrapper around classmethod atomic_list_append
        retaining backwards compatibility with older method name expected by tests.
        """
        new_version = type(self).atomic_list_append(
            self.pk, field, path, element, max_length=max_length, expected_version=expected_version  # type: ignore[arg-type]
        )
        # Refresh only the mutated json + version for local consistency
        self.refresh_from_db(fields=[field, "version", "dt_modified"])
        if hasattr(self, "_pydantic_cache"):
            self._pydantic_cache = None  # type: ignore[attr-defined]
        return new_version


class AuthorizedAccessMixin(models.Model):
    """Pluggable authorization scope helper (stub).

    Purpose:
    - Provide a uniform, overridable entry point for per-record access scoping
      beyond coarse IsAuthenticated checks.
    - Avoid scattering ad-hoc filters across viewsets; centralize logic near
      the data model but keep defaults permissive.

    Key design points:
    - No database fields here (pure behavior) -> safe to add retroactively.
    - Subclasses can override classmethod `authorized_qs` OR define a lightweight
      `authz_scope` method for fine‑grained filtering.
    - Supports patterns like:
        * Sales rep only sees Orgs where they are assigned rep.
        * Vendor user only sees Items for which they are designated supplier.
        * Contact limited to inventory in their site (site_code matching user.profile.site_code).
    - Uses heuristics to look for common field names unless overridden.

    Extension hooks:
    - Define class attribute AUTHZ_FIELD_CANDIDATES = ["assigned_contact_id", "owner_id", ...]
      to have the default filter attempt equality with user.contact.id.
    - Implement @classmethod authz_scope(cls, qs, user, action: str, context: dict | None) -> QuerySet
      to supply custom filtering (return qs unmodified for full access).
    - Instance method `is_authorized(user, action)` can be overridden for per-object checks.

    Usage in views (pseudo):
        qs = Model.authorized_qs(request.user, action='read')

    NOTE: This is a *stub*; by default it returns the base queryset (no restriction)
    except for unauthenticated users (empty). Enable stricter defaults later by
    toggling a project setting and tightening the fallback behavior.
    """

    # Optional toggle: if future setting wants implicit deny unless explicit scope.
    AUTHZ_DEFAULT_DENY_UNAUTHENTICATED = True
    AUTHZ_FIELD_CANDIDATES: list[str] = []  # subclasses extend as needed

    class Meta:
        abstract = True

    @classmethod
    def _base_authz_queryset(cls, base_qs=None):  # tiny helper to allow injection in tests
        return base_qs if base_qs is not None else cls.objects.all()  # type: ignore[attr-defined]

    @classmethod
    def authorized_qs(
        cls,
        user,
        action: str = "read",
        base_qs=None,
        context: dict | None = None,
    ):
        qs = cls._base_authz_queryset(base_qs)
        # Anonymous handling
        if not getattr(user, "is_authenticated", False):
            if cls.AUTHZ_DEFAULT_DENY_UNAUTHENTICATED:
                return qs.none()
            return qs
        # Superusers (or staff toggle) -> full access
        if getattr(user, "is_superuser", False):
            return qs
        # Custom override hook
        if hasattr(cls, "authz_scope"):
            try:
                return cls.authz_scope(qs, user, action, context)  # type: ignore[misc]
            except Exception:  # pragma: no cover - defensive
                return qs
        # Heuristic candidate filtering (only if we have a contact id available)
        contact_id = getattr(getattr(user, "contact", None), "id", None)
        if contact_id and cls.AUTHZ_FIELD_CANDIDATES:
            from django.db.models import Q  # local import to avoid early import cycles
            cond = Q()
            for field_name in cls.AUTHZ_FIELD_CANDIDATES:
                if field_name in {f.name for f in cls._meta.fields}:  # type: ignore[attr-defined]
                    cond |= Q(**{field_name: contact_id})
            if cond:  # only apply if at least one field exists
                return qs.filter(cond)
        return qs  # default pass‑through

    def is_authorized(self, user, action: str = "read") -> bool:  # instance level hook
        if not getattr(user, "is_authenticated", False):
            return False
        if getattr(user, "is_superuser", False):
            return True
        return True  # default allow; override for object-level denial


class UniversalDictMixin(models.Model):
    """Stable outward serialization (universal dict) + optional Pydantic conversion."""

    feature_flags = {"universal_dict"}

    class Meta:
        abstract = True

    def to_universal_dict(self) -> Dict[str, Any]:
        u = getattr(self, "uuid", None)
        base = {
            "id": self.pk,
            "uuid": (str(u) if u else None),
            "ida": getattr(self, "ida", ""),
            "dt_created": getattr(self, "dt_created", None),
            "dt_modified": getattr(self, "dt_modified", None),
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
        if hasattr(self, "actions"):
            base["actions"] = getattr(self, "actions")
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
    ActionsMixin,
    CoreModel,
    MetadataMixin,

    RefsMixin,
    KeywordsMixin, # QQQ

    PrefsMixin,
    CommentsMixin,

    HealthMixin,
    LifecycleMixin,  # QQQ should be these combined

    UniversalDictMixin,  # QQQ is that already covered by CoreModel?
    AtomicJSONMixin,  # QQQ where this used and why
):
    """Full capability base: adds JSON envelopes, search keywords, lifecycle & atomic ops.

    Additional responsibilities over CoreModel:
    - changed_fields tracking persisted inside metadata.versioning.changed_fields
    - size enforcement & warning logs per JSON envelope
    - touch() helper (update dt_modified only) avoiding a version bump
    - keyword dirtiness marking on save (for async refresh flows)
    """

    class Meta:  # type: ignore[override]
        abstract = True
        indexes = [
            GinIndex(fields=["refs"]),
            GinIndex(fields=["prefs"]),
            GinIndex(fields=["actions"]),
            models.Index(KeyTextTransform('status', 'actions'), name='idx_actions_status'),
            models.Index(KeyTextTransform('required', 'actions'), name='idx_actions_required'),
            models.Index(KeyTextTransform('who', 'actions'), name='idx_actions_who'),
            models.Index(KeyTextTransform('when', 'actions'), name='idx_actions_when'),
        ]

    # QuerySet / Manager providing convenience filters for lifecycle + keyword flag
    class FullQuerySet(models.QuerySet):
        def active(self):
            return self.filter(is_active=True, is_deleted=False, is_archived=False)

        def inactive(self):
            return self.filter(models.Q(is_active=False) | models.Q(is_deleted=True) | models.Q(is_archived=True))

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

        def inactive(self):
            return self.get_queryset().inactive()

        def deleted(self):
            return self.get_queryset().deleted()

        def archived(self):
            return self.get_queryset().archived()

        def keyword_pending(self):
            return self.get_queryset().keyword_pending()

    objects = FullManager()

    def is_effectively_active(self) -> bool:
        return getattr(self, "is_active", True) and not getattr(self, "is_deleted", False) and not getattr(self, "is_archived", False)

    # --- change tracking --------------------------------------------------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._capture_original_state()

    def _capture_original_state(self):
        self._original_state: Dict[str, Any] = {}
        for f in self._meta.fields:  # type: ignore[attr-defined]
            try:
                # Use f.attname (e.g. 'contact_id') for FK fields to avoid
                # triggering lazy-load queries on the related object.
                self._original_state[f.attname] = getattr(self, f.attname)
            except Exception:  # pragma: no cover
                pass
    # Note: formerly captured a separate _original_dt_created to enforce immutability.
    # That legacy guard is removed; dt_created may now be adjusted explicitly if needed.

    def _compute_changed_fields(self) -> list[str]:
        changed: list[str] = []
        if not getattr(self, "_original_state", None):
            return changed
        auto_exclude = {"dt_modified", "version"}
        for f in self._meta.fields:  # type: ignore[attr-defined]
            name = f.name
            if name in auto_exclude:
                continue
            # Use f.attname to compare raw DB column values (e.g. contact_id)
            # to avoid triggering lazy-load queries on FK fields.
            attr = f.attname
            old = self._original_state.get(attr)
            new = getattr(self, attr)
            if old != new:
                changed.append(name)
        return changed

    # Lightweight helper to record the client's original submission payload.
    # Stores a bounded snapshot under prefs.submission.as_submitted: {data, dt, by}
    def record_submission_snapshot(self, data: Dict[str, Any], actor_id: int | None = None, max_bytes: int = 16384):
        try:
            payload = data or {}
            # Bound the size to avoid bloating prefs; if too large, keep shallow keys only
            raw = json.dumps(payload, separators=(",", ":"))
            if len(raw.encode("utf-8")) > max_bytes:
                if isinstance(payload, dict):
                    trimmed = {k: payload.get(k) for k in list(payload.keys())[:50]}
                else:
                    trimmed = payload
                payload = {"_trimmed": True, "_note": f">={max_bytes}B", "data": trimmed}
            prefs = getattr(self, "prefs", {}) or {}
            sub = prefs.setdefault("submission", {})
            sub["as_submitted"] = {
                "data": payload,
                "dt": int(timezone.now().timestamp() * 1000),
                "by": actor_id or 0,
            }
            self.prefs = prefs  # type: ignore[assignment]
        except Exception:  # pragma: no cover - defensive
            pass

    def save(self, *args, **kwargs):  # orchestrate save chain
        expected_version = kwargs.pop("expected_version", None)
        if expected_version is not None and self.pk:
            current = type(self).objects.filter(pk=self.pk).values_list("version", flat=True).first()
            if current is not None and current != expected_version:
                raise VersionConflictError(
                    f"Version conflict: expected {expected_version} got {current}"
                )
    # (Removed) dt_created immutability guard: legacy enforcement deleted for flexibility.

        # attach changed_fields for updates
        if self.pk and isinstance(getattr(self, "metadata", None), dict):
            changed_fields = self._compute_changed_fields()
            if changed_fields:
                ver = self.metadata.setdefault("versioning", {})  # type: ignore[attr-defined]
                ver["changed_fields"] = changed_fields

        # Ensure links are denormalized
        if isinstance(self, RefsMixin):
            self.ensure_links_denormalized()

        super().save(*args, **kwargs)
        self._capture_original_state()  # refresh snapshot

        # size enforcement
        def check_size(field_value, max_size, field_name):
            try:
                size = len(json.dumps(field_value, separators=(",", ":")).encode("utf-8"))
            except Exception:
                return
            if size > max_size:
                raise ValueError(f"{field_name} exceeds maximum size of {max_size} bytes")
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

        if hasattr(self, "metadata"):
            check_size(self.metadata, MAX_METADATA_SIZE, "metadata")  # type: ignore[attr-defined]
        if hasattr(self, "refs"):
            check_size(self.refs, MAX_REFS_SIZE, "refs")  # type: ignore[attr-defined]
        if hasattr(self, "prefs"):
            check_size(self.prefs, MAX_PREFS_SIZE, "prefs")  # type: ignore[attr-defined]
        if hasattr(self, "config"):
            check_size(self.config, MAX_CONFIG_SIZE, "config")  # type: ignore[attr-defined]
        if hasattr(self, "actions"):
            check_size(self.actions, MAX_ACTIONS_SIZE, "actions")  # type: ignore[attr-defined]

        if isinstance(self, KeywordsMixin):
            self.mark_keywords_dirty()

        try:  # Telemetry for future large JSON offload (no mutation while disabled)
            _telemetry_offload_candidates(self)
        except Exception:  # pragma: no cover - never block save
            logger.debug("offload telemetry failed", exc_info=True)

    def touch(self, update_fields: list[str] | None = None):  # dt_modified without version bump
        if not self.pk:
            return
        now_ms = int(timezone.now().timestamp() * 1000)
        update_map: Dict[str, Any] = {"dt_modified": now_ms}
        if update_fields:
            for field in update_fields:
                if field in {"version", "dt_created"}:
                    continue
                update_map[field] = getattr(self, field)
        type(self).objects.filter(pk=self.pk).update(**update_map)
        self.dt_modified = now_ms  # type: ignore[attr-defined]
        self._capture_original_state()

    # ── Post-save hook (universal) ────────────────────────────────────
    def post_save_hook(self, data: Dict[str, Any], is_update: bool = False, context: dict | None = None):
        """Standard post-save hook for all BaseModel descendants.

        Responsibilities:
        - Sync pending metadata erosion annotations → Erosion records.

        Subclasses that override should call ``super().post_save_hook(data, is_update, context)``
        to preserve universal behaviour.

        Returns a message string or None.
        """
        messages: list[str] = []
        # ── Erosion annotation sync ──────────────────────────────────
        try:
            meta = getattr(self, 'metadata', None)
            if isinstance(meta, dict):
                stings = meta.get('small_stings')
                erosions = meta.get('erosions')
                has_pending = False
                for lst in (stings, erosions):
                    if isinstance(lst, list):
                        for entry in lst:
                            if isinstance(entry, dict) and not entry.get('erosion_id'):
                                has_pending = True
                                break
                    if has_pending:
                        break
                if has_pending:
                    from apps.accounts.services.erosion import sync_metadata_erosions
                    count = sync_metadata_erosions(self)
                    if count:
                        messages.append(f'{count} erosion record(s) created')
        except Exception:
            logger.exception('post_save_hook: erosion sync failed for %s #%s',
                             self.__class__.__name__, self.pk)

        return '; '.join(messages) if messages else None


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