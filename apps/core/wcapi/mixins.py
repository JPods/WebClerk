from __future__ import annotations
import json
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type, Iterable, Sequence
from django.http import Http404, HttpResponseForbidden
from django.conf import settings
from functools import cached_property
from django.db.models import Q, QuerySet, Model
from rest_framework.request import Request

from .registry import get as get_cfg

def _import_callable(path: str):
    """
    Import a callable from a dotted path like 'pkg.mod.func' or 'pkg.mod:func'.
    """
    if not path:
        raise ValueError("Empty import path")
    try:
        # Try Django helper for dotted import paths
        from django.utils.module_loading import import_string  # type: ignore
        obj = import_string(path)
    except Exception:
        # Support colon syntax explicitly
        if ":" in path:
            mod, func = path.split(":", 1)
            module = import_module(mod)
            obj = getattr(module, func)
        else:
            # Fallback: split by last dot
            mod, _, attr = path.rpartition(".")
            if not mod or not attr:
                raise
            module = import_module(mod)
            obj = getattr(module, attr)
    if not callable(obj):
        raise TypeError(f"Imported object '{path}' is not callable")
    return obj

try:
    from apps.core.models import SoftDeleteLedger  # type: ignore
except Exception:
    SoftDeleteLedger = None  # type: ignore

class SettingsDrivenCRUDMixin:
    """
    Centralized CRUD policies driven by Setting(purpose='view_edit') or JSON fallback.

    Behavior toggles in setting.data['__meta__']:
      - relations: embed related data in GET
      - ordering, search.fields, filters.allow, pagination.page_size/max_page_size
      - hooks: pre_save, post_save, pre_delete, post_delete (dotted callables)
      - scopes: per-role queryset builder (def fn(request, qs) -> qs)
      - soft_delete: enabled, field, false_value

    Dev fallback (no setting record found):
      - Allow all fields for all users on read/write
      - meta.policy_missing=True and meta.policy_source='dev_fallback'
    """

    SETTINGS_PURPOSE = "view_edit"
    DEFAULT_JSON_REL_PATH = "apps/core/management/commands/view_edit.json"

    # ---------- Settings loading

    def _model_key(self, model: Type[Model]) -> str:
        return getattr(model._meta, "model_name", model.__name__).lower()

    def _json_path(self) -> Path:
        p = getattr(settings, "VIEW_EDIT_JSON_PATH", None)
        if p:
            return Path(p)
        base = getattr(settings, "BASE_DIR", None)
        if base:
            return Path(base) / self.DEFAULT_JSON_REL_PATH
        return Path(self.DEFAULT_JSON_REL_PATH)

    @cached_property
    def _json_index(self) -> Dict[str, dict]:
        try:
            path = self._json_path()
            if not path.exists():
                return {}
            raw_text = path.read_text()
            # Support JSON with // comments
            lines = [ln for ln in raw_text.splitlines() if not ln.strip().startswith("//")]
            data = json.loads("\n".join(lines))
            out: Dict[str, dict] = {}
            for rec in data or []:
                if not rec or not rec.get("is_active", True):
                    continue
                if rec.get("purpose") != self.SETTINGS_PURPOSE:
                    continue
                mk = (rec.get("model_name") or "").strip().lower()
                if mk:
                    out[mk] = rec
            return out
        except Exception:
            return {}

    def _db_setting_for(self, model_key: str) -> Tuple[Optional[dict], Optional[str]]:
        try:
            from apps.core.models import Setting  # local import to avoid cycles
        except Exception:
            return None, None
        try:
            row = (
                Setting.objects.filter(is_active=True, purpose=self.SETTINGS_PURPOSE, model_name=model_key)
                .order_by("-id")
                .first()
            )
            if not row:
                return None, None
            return (
                {
                    "is_active": row.is_active,
                    "name": getattr(row, "name", model_key),
                    "purpose": row.purpose,
                    "role": getattr(row, "role", "all"),
                    "model_name": row.model_name,
                    "data": getattr(row, "data", {}) or {},
                    "comment": getattr(row, "comment", "") or "",
                },
                "db",
            )
        except Exception:
            return None, None

    def _json_setting_for(self, model_key: str) -> Tuple[Optional[dict], Optional[str]]:
        rec = self._json_index.get(model_key)
        return (rec, "json") if rec else (None, None)

    def _setting_for(self, model_key: str) -> Tuple[Optional[dict], Optional[str]]:
        rec, src = self._db_setting_for(model_key)
        if rec:
            return rec, src
        return self._json_setting_for(model_key)

    # ---------- Roles and allowlists

    def _roles_for(self, request) -> List[str]:
        roles: List[str] = []
        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            if getattr(user, "is_superuser", False):
                roles.append("SUPER")
            if getattr(user, "is_staff", False):
                roles.append("ADMIN")
            try:
                roles.extend([g.upper() for g in user.groups.values_list("name", flat=True)])
            except Exception:
                pass
            roles.append("USER")
        else:
            roles.append("PUBLIC")
        return roles

    def _resolve_role_block(self, data_map: dict, roles: List[str]) -> dict:
        for r in roles:
            blk = data_map.get(r)
            if blk:
                return blk
        return data_map.get("PUBLIC") or {}

    def _resolve_ctx_block(self, role_block: dict, ctx: Optional[str]) -> dict:
        if not ctx:
            return role_block or {}
        ctx_blk = role_block.get(ctx)
        if isinstance(ctx_blk, dict) and ("view" in ctx_blk or "edit" in ctx_blk):
            return ctx_blk
        return role_block or {}

    def _all_model_fields(self, model: Type[Model]) -> List[str]:
        try:
            names: List[str] = []
            for f in model._meta.get_fields():
                # Include concrete fields and FK/O2O; skip reverse mgrs in base list
                if getattr(f, "concrete", False) or getattr(f, "many_to_one", False) or getattr(f, "one_to_one", False):
                    names.append(f.name)
            return names
        except Exception:
            return []

    # ---------- View-name (specialty behaviors)

    def _extract_view_name(self, request, meta: dict) -> Optional[str]:
        """
        Resolve specialty view-name from request if it matches a defined profile in __meta__.views.
        """
        views = (meta.get("views") or {}) if isinstance(meta, dict) else {}
        if not isinstance(views, dict) or not views:
            return None
        candidate = request.GET.get("name") or request.headers.get("X-View-Name")
        if not candidate:
            return None
        return candidate if candidate in views else None

    def _apply_view_profile_overrides(self, base_meta: dict, view_profile: dict) -> dict:
        """
        Merge view-profile fields into meta. Shallow merge is fine for typical knobs
        (relations, ordering, search, filters, pagination, hooks, scopes).
        """
        if not isinstance(view_profile, dict):
            return base_meta
        merged = dict(base_meta or {})
        for k, v in view_profile.items():
            if k == "fields":
                # handled separately by get_view_edit_allowlists
                continue
            merged[k] = v
        return merged

    def get_view_edit_allowlists(
        self, model: Type[Model], request=None, ctx: Optional[str] = None, view_name: Optional[str] = None
    ) -> Tuple[Optional[List[str]], Optional[List[str]], dict, dict]:
        """
        Returns (view_fields, edit_fields, role_block, meta)
        meta includes: policy_source, roles_applied, and if applicable policy_missing, view_name.
        If a view_name is specified and exists in __meta__.views, its overrides are merged.
        Optionally, a profile can override fields via fields.view / fields.edit.
        """
        model_key = self._model_key(model)
        rec, source = self._setting_for(model_key)
        roles = self._roles_for(request)
        base_meta = {"policy_source": source or "dev_fallback", "roles_applied": roles}

        if not rec:
            all_fields = self._all_model_fields(model)
            meta = {**base_meta, "policy_missing": True}
            if view_name:
                meta["view_name"] = view_name
            return all_fields or None, all_fields or None, {}, meta

        data_map = rec.get("data") or {}
        role_block = self._resolve_role_block(data_map, roles)
        ctx_block = self._resolve_ctx_block(role_block, ctx)

        meta = (data_map.get("__meta__") or {}).copy()
        role_meta = role_block.get("__meta__") or {}
        if role_meta:
            meta.update(role_meta)

        # If client didn’t pass a view_name explicitly, see if one is present in request
        view_name = view_name or self._extract_view_name(request, meta)
        profile = None
        if view_name:
            profile = (meta.get("views") or {}).get(view_name)
            if profile:
                meta = self._apply_view_profile_overrides(meta, profile)
                meta["view_name"] = view_name

        # Determine fields (allow profile to override via fields.view / fields.edit)
        view_fields = (ctx_block.get("view") if isinstance(ctx_block, dict) else None) or role_block.get("view")
        edit_fields = (ctx_block.get("edit") if isinstance(ctx_block, dict) else None) or role_block.get("edit")

        if profile and isinstance(profile, dict):
            fields_override = profile.get("fields")
            if isinstance(fields_override, dict):
                view_fields = fields_override.get("view", view_fields)
                edit_fields = fields_override.get("edit", edit_fields)

            # A profile can also force a different ctx (e.g., ctx="list")
            prof_ctx = profile.get("ctx")
            if prof_ctx in ("list", "display"):
                # re-resolve ctx block with the forced ctx
                ctx_block = self._resolve_ctx_block(role_block, prof_ctx)
                view_fields = (ctx_block.get("view") if isinstance(ctx_block, dict) else None) or view_fields
                edit_fields = (ctx_block.get("edit") if isinstance(ctx_block, dict) else None) or edit_fields

        meta.update(base_meta)
        return view_fields, edit_fields, role_block, meta

    # ---------- Query building

    def base_queryset(self, model: Type[Model]) -> QuerySet:
        """
        Default queryset for the given model; override in subclasses to apply domain-specific scoping.
        """
        try:
            return model._default_manager.all()
        except Exception:
            return model.objects.all()

    def apply_filters(
        self,
        qs: QuerySet,
        request,
        model: Type[Model],
        view_fields: Optional[List[str]],
        meta: dict,
        special_view_name: Optional[str] = None,
    ) -> QuerySet:
        allowed = set((meta.get("filters") or {}).get("allow") or view_fields or [])
        params = request.GET
        filters: Dict[str, Any] = {}
        for k, v in params.items():
            if k in {"page", "page_size", "ordering", "q"}:
                continue
            # If "name" was used as a special view selector, do not treat it as a filter
            if k == "name" and special_view_name:
                continue
            if k in allowed:
                filters[k] = v
        if filters:
            try:
                qs = qs.filter(**filters)
            except Exception:
                pass
        return qs

    def apply_search(self, qs: QuerySet, request, model: Type[Model], meta: dict) -> QuerySet:
        q = (request.GET.get("q") or "").strip()
        if not q:
            return qs
        fields = (meta.get("search") or {}).get("fields") or []
        if not fields:
            return qs
        cond = Q()
        for f in fields:
            cond |= Q(**{f"{f}__icontains": q})
        try:
            return qs.filter(cond)
        except Exception:
            return qs

    def apply_ordering(self, qs: QuerySet, request, meta: dict) -> QuerySet:
        ordering = request.GET.get("ordering")
        if ordering:
            try:
                return qs.order_by(ordering)
            except Exception:
                return qs
        default_ord = meta.get("ordering")
        if default_ord:
            try:
                return qs.order_by(*default_ord)
            except Exception:
                return qs
        return qs

    def paginate(self, qs: QuerySet, request, meta: dict) -> Tuple[QuerySet, dict]:
        try:
            page = max(1, int(request.GET.get("page", "1")))
        except Exception:
            page = 1
        try:
            page_size = int(request.GET.get("page_size", "0") or 0)
        except Exception:
            page_size = 0
        pg = (meta.get("pagination") or {}) if isinstance(meta, dict) else {}
        default_size = int(pg.get("page_size") or 50)
        max_size = int(pg.get("max_page_size") or 500)
        if page_size <= 0:
            page_size = default_size
        page_size = min(page_size, max_size)
        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        page_qs = qs[start:end]
        return page_qs, {"page": page, "page_size": page_size, "total": total}

    # ---------- Writes and hooks

    def sanitize_payload_with_edit_allowlist(
        self, model: Type[Model], payload: dict, request=None, ctx: Optional[str] = None
    ) -> Tuple[dict, dict]:
        _, edit_fields, _, meta = self.get_view_edit_allowlists(model, request=request, ctx=ctx)
        if edit_fields:
            payload = {k: v for k, v in (payload or {}).items() if k in edit_fields}
        return payload, meta

    def run_hook(self, name: str, meta: dict, context: dict):
        hooks = (meta.get("hooks") or {}) if isinstance(meta, dict) else {}
        path = hooks.get(name)
        if not path:
            return
        try:
            fn = _import_callable(path)
            fn(context)
        except Exception:
            return

    def soft_delete(self, obj, meta: dict) -> bool:
        sd = (meta.get("soft_delete") or {}) if isinstance(meta, dict) else {}
        if not sd.get("enabled"):
            return False
        field = sd.get("field") or "is_active"
        false_val = sd.get("false_value", False)
        retention_days = int(sd.get("retention_days") or 60)

        changed = False
        try:
            if hasattr(obj, field):
                setattr(obj, field, false_val)
                obj.save(update_fields=[field])
                changed = True
        except Exception:
            pass

        if SoftDeleteLedger:
            try:
                SoftDeleteLedger.schedule(obj, retention_days=retention_days)
                return True
            except Exception:
                return changed
        return changed

    def apply_keyword_search(self, qs: QuerySet, request, meta: dict) -> QuerySet:
        """
        kw=word1,word2 or kw=space separated.
        If __meta__.search.keywords is configured:
          - when type=='array' and field is an ArrayField/JSON list: uses overlap
          - otherwise falls back to icontains across configured fields
        """
        raw = (request.GET.get("kw") or "").strip()
        if not raw:
            return qs
        words = [w for w in (raw.replace(",", " ").split()) if w]
        if not words:
            return qs

        search_meta = (meta.get("search") or {}) if isinstance(meta, dict) else {}
        kw_cfg = search_meta.get("keywords") or {}
        typ = (kw_cfg.get("type") or "").lower()
        field = kw_cfg.get("field")
        fields = search_meta.get("fields") or []

        try:
            if typ == "array" and field:
                # Postgres ArrayField or JSON list: overlap
                return qs.filter(**{f"{field}__overlap": words})
        except Exception:
            pass

        # Fallback: OR across text fields
        cond = Q()
        for w in words:
            for f in fields:
                cond |= Q(**{f"{f}__icontains": w})
        try:
            return qs.filter(cond)
        except Exception:
            return qs

    # ----- Open query DSL (POST)
    DEFAULT_ALLOWED_OPS = {"eq", "ne", "lt", "lte", "gt", "gte", "icontains", "contains", "in", "isnull", "startswith", "istartswith", "endswith", "iendswith"}

    def _query_policy(self, meta: dict) -> dict:
        q = (meta.get("query") or {}) if isinstance(meta, dict) else {}
        return {
            "allow_fields": set(q.get("allow_fields") or []),
            "allow_ops": set(q.get("allow_ops") or self.DEFAULT_ALLOWED_OPS),
            "allow_joins": (q.get("allow_joins") or {}),  # alias -> path
            "max_depth": int(q.get("max_depth") or 1),
            "max_rows": int(q.get("max_rows") or 500),
        }

    def _validate_field(self, f: str, policy: dict) -> bool:
        # Permit nested via allowed joins (alias.field) if the alias is allowed
        if "." in f:
            alias, _, tail = f.partition(".")
            path = (policy["allow_joins"] or {}).get(alias)
            return bool(path and tail and (not policy["allow_fields"] or tail in policy["allow_fields"]))
        return (not policy["allow_fields"]) or (f in policy["allow_fields"])

    def _lookup_for(self, f: str, op: str) -> str:
        if op == "eq": return f
        if op == "ne": return f"{f}__ne"  # handled via exclude
        if op in {"lt","lte","gt","gte","contains","icontains","startswith","istartswith","endswith","iendswith"}:
            return f"{f}__{op}"
        if op == "in": return f"{f}__in"
        if op == "isnull": return f"{f}__isnull"
        return f  # default

    def _json_body(self, request) -> dict:
        """
        Best-effort JSON body parser that works with Django HttpRequest and DRF Request.
        Returns a dict, or {} when no/invalid JSON is present.
        """
        # Prefer DRF's parsed data when available
        data = getattr(request, "data", None)
        if isinstance(data, dict):
            return data
        # Handle QueryDict (e.g., DRF form or Django request.POST)
        try:
            from django.http import QueryDict  # type: ignore
            if isinstance(data, QueryDict):
                return dict(data)
        except Exception:
            pass

        # Fallback to raw body
        raw = getattr(request, "body", b"")
        try:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
        except Exception:
            raw = ""
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    def evaluate_open_query(self, model: Type[Model], request, meta: dict) -> Tuple[QuerySet, dict]:
        """
        Accepts JSON body:
          { select?: [fields], where?: [{field, op, value}], any?: true, order_by?: ["-field"], joins?: ["alias"], limit?, offset? }
        Enforces policy from __meta__.query.
        """
        policy = self._query_policy(meta)
        try:
            body = self._json_body(request)
        except Exception:
            body = {}
        where = body.get("where") or []
        join_aliases = set(body.get("joins") or [])
        any_mode = bool(body.get("any"))
        order_by = body.get("order_by") or []
        limit = int(body.get("limit") or 0)
        offset = int(body.get("offset") or 0)

        qs = self.base_queryset(model)

        # Apply joins (only allowed aliases)
        for alias in join_aliases:
            path = (policy["allow_joins"] or {}).get(alias)
            if not path:
                continue
            # Prefer prefetch_related for reverse/m2m; select_related for FK/O2O is safe to use via select_related
            try:
                qs = qs.prefetch_related(path)
            except Exception:
                try:
                    qs = qs.select_related(path)
                except Exception:
                    pass

        # Build conditions
        AND = []
        EXCLUDE = []
        conds = where if isinstance(where, list) else []
        for c in conds:
            if not isinstance(c, dict):  continue
            f = c.get("field"); op = (c.get("op") or "eq").lower(); val = c.get("value", None)
            if not f or op not in policy["allow_ops"]:  continue
            if not self._validate_field(f, policy):      continue

            # Map alias.field to real lookup if present
            if "." in f:
                alias, _, tail = f.partition(".")
                path = (policy["allow_joins"] or {}).get(alias)
                if not path:  continue
                f = f"{path}__{tail}"

            if op == "ne":
                EXCLUDE.append({self._lookup_for(f, "eq"): val})
            else:
                AND.append({self._lookup_for(f, op): val})

        # Apply where
        try:
            if AND:
                for filt in AND:
                    qs = qs.filter(**filt)
            if EXCLUDE:
                for ex in EXCLUDE:
                    qs = qs.exclude(**ex)
        except Exception:
            pass

        # Ordering
        if isinstance(order_by, list) and order_by:
            try:
                qs = qs.order_by(*order_by)
            except Exception:
                pass

        # Caps
        if limit <= 0 or limit > policy["max_rows"]:
            limit = policy["max_rows"]
        if offset < 0:
            offset = 0
        return qs[offset: offset + limit], {"limit": limit, "offset": offset}

    # ----- Saved queries and sets (persisted in DB Setting)

    def _user_is_admin(self, request) -> bool:
        user = getattr(request, "user", None)
        return bool(user and (getattr(user, "is_superuser", False) or getattr(user, "is_staff", False)))

    def _can_access_saved_setting(self, request, setting_row) -> bool:
        """
        Enforce access to Setting rows with purpose in {'saved_query','saved_set'}.
        Rules:
          - Admins: full access.
          - scope.type == 'person': allowed if owner_id == request.user.id
          - scope.type == 'role': allowed if scope.value is in roles_applied
          - scope.type == 'job': allowed if request.GET['job'] or header X-Job matches scope.value
        """
        if self._user_is_admin(request):
            return True
        data = getattr(setting_row, "data", {}) or {}
        scope = (data.get("scope") or {}) if isinstance(data, dict) else {}
        owner_id = data.get("owner_id")
        typ = (scope.get("type") or "").lower()
        val = (scope.get("value") or "") if scope else ""
        user = getattr(request, "user", None)
        if typ == "person":
            try:
                return bool(user and getattr(user, "is_authenticated", False) and int(owner_id or 0) == int(getattr(user, "id", 0)))
            except Exception:
                return False
        if typ == "role":
            roles = self._roles_for(request)
            return val in roles
        if typ == "job":
            job = request.GET.get("job") or request.headers.get("X-Job")
            return bool(job and val and str(job) == str(val))
        # default: private owner check if present
        if owner_id:
            try:
                return bool(user and getattr(user, "is_authenticated", False) and int(owner_id) == int(getattr(user, "id", 0)))
            except Exception:
                return False
        return False

    def _load_saved_query_setting(self, request, model_slug: str, ident: str):
        """
        ident may be numeric id or name (unique per owner scope).
        """
        try:
            from apps.core.models import Setting  # local import to avoid cycles
        except Exception:
            raise Http404("saved_query storage unavailable")

        qs = Setting.objects.filter(is_active=True, purpose="saved_query", model_name=model_slug)
        if ident.isdigit():
            row = qs.filter(pk=int(ident)).first()
        else:
            row = qs.filter(name=ident).order_by("-id").first()
        if not row or not self._can_access_saved_setting(request, row):
            raise Http404("saved_query not found")
        return row

    def _load_saved_set_setting(self, request, model_slug: str, ident: str):
        try:
            from apps.core.models import Setting
        except Exception:
            raise Http404("saved_set storage unavailable")

        qs = Setting.objects.filter(is_active=True, purpose="saved_set", model_name=model_slug)
        if ident.isdigit():
            row = qs.filter(pk=int(ident)).first()
        else:
            row = qs.filter(name=ident).order_by("-id").first()
        if not row or not self._can_access_saved_setting(request, row):
            raise Http404("saved_set not found")
        return row

    def filter_by_saved_set(self, qs: QuerySet, request, model: Type[Model], meta: dict) -> QuerySet:
        """
        If request has ?set=<id|name>, restrict queryset to that saved id list.
        Soft-deleted rows are already excluded by apply_role_scope when configured.
        """
        ident = (request.GET.get("set") or "").strip()
        if not ident:
            return qs
        try:
            row = self._load_saved_set_setting(request, self._model_key(model), ident)
        except Http404:
            return qs.none()
        ids = list(((getattr(row, "data", {}) or {}).get("ids") or []))
        if not ids:
            return qs.none()
        try:
            return qs.filter(pk__in=ids)
        except Exception:
            return qs

class RegistryQuerysetMixin:
    model_key: str

    def get_registry_config(self):
        cfg = get_cfg(self.model_key)
        if not cfg:
            raise RuntimeError(f"wcapi registry missing config for '{self.model_key}'")
        return cfg

    def get_queryset(self) -> QuerySet:
        cfg = self.get_registry_config()
        if cfg.queryset is not None:
            return cfg.queryset.all()
        return cfg.model._default_manager.all()  # type: ignore[attr-defined]

class QSearchMixin(RegistryQuerysetMixin):
    def apply_q_search(self, qs: QuerySet, request: Request, extra_fields: Optional[Sequence[str]] = None) -> QuerySet:
        raw_q = (request.GET.get("q") or "").strip()
        if not raw_q:
            return qs
        cfg = self.get_registry_config()
        fields = list(cfg.search_fields or [])
        if extra_fields:
            fields.extend(extra_fields)
        if not fields:
            return qs
        terms = [t for t in raw_q.split() if t]
        for term in terms:
            or_q = Q()
            for f in fields:
                or_q |= Q(**{f"{f}__icontains": term})
            qs = qs.filter(or_q)
        return qs

class DevFallbackMetaMixin:
    def add_dev_fallback_meta(self, meta: dict) -> dict:
        if self.get_registry_config().dev_fallback:
            meta.setdefault("policy_missing", True)
            meta.setdefault("policy_source", "dev_fallback")
        return meta