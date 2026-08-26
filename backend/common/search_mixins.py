from django.db import models
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import permissions
from typing import Any, Sequence


class PrefixAndSearchView(APIView):
    """Reusable multi-term AND prefix search for simple models.

    Subclasses set:
        model (QuerySet available via model.objects)
        serializer_class
        search_fields = ['name','type']  (fields to OR within each term)
        role_set = {'staff','admin'} (optional)
        max_results = 100
    """
    permission_classes = [permissions.IsAuthenticated]
    model = None
    serializer_class = None
    search_fields: list[str] = []
    role_set: set[str] | None = None
    max_results = 100
    # Optional: explicit model name for settings lookups; defaults to model class name
    model_name: str | None = None
    # Optional: maximum security level enforced via query param; see _apply_security_filters
    security_param_names: tuple[str, ...] = ("level", "security_level")

    def _role_allowed(self, user):
        if not user.is_authenticated:
            return False
        if not self.role_set:
            return True
        return getattr(user, 'role', '') in self.role_set or getattr(user, 'is_superuser', False)

    def get_queryset(self):
        return self.model.objects.all()  # type: ignore

    def get_base_queryset(self, request):
        """Authorization-aware base queryset.

        If the model exposes authorized_qs (see AuthorizedAccessMixin), use it; otherwise
        fall back to model.objects.all(). Subclasses can override for extra joins.
        """
        model_cls = getattr(self, 'model', None)
        if model_cls is None:
            return self.get_queryset()
        authz = getattr(model_cls, 'authorized_qs', None)
        if callable(authz):
            try:
                return authz(user=request.user, action='search', base_qs=None, context={'view': self})
            except Exception:
                return self.get_queryset()
        return self.get_queryset()

    def policy_scope(self, qs, request):
        """Optional per-view policy filter hook.

        Override in subclasses to apply additional domain rules (e.g., vendor-scoped items).
        Default: identity (no changes).
        """
        return qs

    def _apply_security_filters(self, qs, request):
        """Apply optional security level constraint if the model has such a field.

        Honors ?level or ?security_level query params. If provided and the model has a
        `security_level` field, constrain to rows with security_level <= provided value.
        """
        try:
            field_names = {f.name for f in self.model._meta.fields}  # type: ignore[attr-defined]
            if 'security_level' not in field_names:
                return qs
            level_val = None
            for p in self.security_param_names:
                raw = request.GET.get(p)
                if raw is not None and raw != '':
                    try:
                        level_val = int(raw)
                        break
                    except Exception:
                        pass
            if level_val is not None:
                return qs.filter(security_level__lte=level_val)
            return qs
        except Exception:
            return qs

    def _settings_keyword_fields(self) -> list[str]:
        """Fetch keyword fields from model definition (wc:model config.search).

        Reads the search section of the wc:model Setting for this view's table
        and returns self_fields as the list of model field names to include in search.
        Falls back to legacy wc:keywords purpose.
        """
        # Resolve model for settings
        try:
            model_key = self.model_name or getattr(getattr(self, 'model', None), '__name__', None)  # type: ignore[attr-defined]
            if not model_key:
                return []
            # Lazy import to avoid cycles
            from apps.core.models.setting import Setting  # type: ignore
            # Try wc:model first
            setting = (Setting.objects
                       .filter(parent_model=model_key, purpose='wc:model', is_active=True)
                       .first())
            if setting and isinstance(setting.config, dict):
                search_cfg = setting.config.get('search', {})
                if search_cfg and search_cfg.get('self_fields'):
                    candidate_fields = search_cfg['self_fields']
                    valid: list[str] = []
                    model_cls = getattr(self, 'model', None)
                    if model_cls:
                        for fname in candidate_fields:
                            try:
                                field_obj = model_cls._meta.get_field(fname)
                                if isinstance(field_obj, (models.CharField, models.TextField)):
                                    valid.append(fname)
                            except Exception:
                                continue
                    return valid
            # Fallback: check wc:keywords record
            setting = (Setting.objects
                       .filter(parent_model=model_key, purpose='wc:keywords', is_active=True)
                       .order_by('-dt_modified')
                       .first())
            if not setting or not isinstance(setting.data, dict):
                return []
            fields_spec: Any = setting.data.get('fields') or setting.data.get('field_list') or None
            # Normalize into a list[str]
            fields_list: list[str] = []
            if isinstance(fields_spec, str):
                parts = fields_spec.split(',')
                fields_list = [s.strip() for s in parts if s and s.strip()]
            elif isinstance(fields_spec, Sequence):
                fields_list = [f for f in list(fields_spec) if isinstance(f, str) and f]
            else:
                fields_list = []
            if not fields_list:
                return []
            candidate_fields = fields_list
            # Validate against model fields to avoid FieldError at query time
            valid: list[str] = []
            model_cls = getattr(self, 'model', None)
            if not model_cls:
                return []
            for fname in candidate_fields:
                try:
                    # Will raise if unknown; we allow concrete fields only
                    field_obj = model_cls._meta.get_field(fname)  # type: ignore[attr-defined]
                    if isinstance(field_obj, (models.CharField, models.TextField)):
                        valid.append(fname)
                except Exception:
                    # Ignore unknown or non-concrete fields
                    continue
            return valid
        except Exception:
            return []

    def build_query(self, qs, terms):
        """Apply multi-term fragment search using shared search_utils.

        Delegates to ``build_fragment_query`` for consistent fragment
        parsing (including ``@`` contains modifier) across all search
        entry points.
        """
        from common.search_utils import build_fragment_query

        extra_fields = self._settings_keyword_fields()
        fields = list(dict.fromkeys([*self.search_fields, *extra_fields]))
        # Rejoin terms into comma-separated string for fragment parser
        raw_search = ", ".join(terms)
        return build_fragment_query(
            qs, raw_search, fields, self.model,
            include_refs_keywords=True,
        )

    def get(self, request):
        if not self._role_allowed(request.user):
            return Response({'detail': 'Forbidden'}, status=403)
        raw_q = (request.GET.get('q') or '').strip()
        if not raw_q:
            return Response({'results': [], 'count': 0})
        terms = [t for t in raw_q.split() if t]
        qs = self.get_base_queryset(request)
        qs = self._apply_security_filters(qs, request)
        qs = self.policy_scope(qs, request)
        qs = self.build_query(qs, terms).order_by('-dt_modified')[: self.max_results]
        data = self.serializer_class(qs, many=True, context={'request': request}).data  # type: ignore
        return Response({'results': data, 'count': len(data), 'q': raw_q, 'terms': terms})