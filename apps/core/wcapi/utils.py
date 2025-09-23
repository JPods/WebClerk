import json
from typing import Any, Dict, List, Union, cast
from django.apps import apps as django_apps

def parse_json_body(request) -> Union[Dict[str, Any], List[Any]]:
    try:
        if hasattr(request, "data"):
            if isinstance(request.data, dict):
                return cast(Dict[str, Any], request.data) or {}
            if isinstance(request.data, list):
                return cast(List[Any], request.data) or {}
    except Exception:
        pass
    try:
        raw = (request.body or b"").decode() or ""
        if raw.strip():
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return cast(Dict[str, Any], parsed)
            if isinstance(parsed, list):
                return cast(List[Any], parsed)
        return {}
    except Exception:
        pass
    try:
        return cast(Dict[str, Any], dict(request.POST.items()))
    except Exception:
        return {}

def coerce_query_payload(body: Dict[str, Any]) -> Dict[str, Any]:
    body = dict(body or {})
    for key in ("dsl", "scope"):
        v = body.get(key)
        if isinstance(v, str):
            try:
                body[key] = json.loads(v)
            except Exception:
                body[key] = {}
    if not isinstance(body.get("dsl"), dict):
        body["dsl"] = {}
    if not isinstance(body.get("scope"), dict):
        body["scope"] = {}
    labels = body.get("labels")
    if isinstance(labels, str):
        try:
            labels = json.loads(labels)
        except Exception:
            labels = [labels]
    if not isinstance(labels, list):
        labels = []
    body["labels"] = labels
    body["name"] = (body.get("name") or "").strip()
    comment = body.get("comment")
    body["comment"] = "" if comment is None else str(comment)
    return body

def resolve_model_slug(slug: str):
    # Prefer the router’s resolution
    try:
        from apps.core.wcapi.views import RESTModelRouterView
        return RESTModelRouterView()._model_class(slug)
    except Exception:
        pass
    # Fallback via app registry by model_name
    slug_l = (slug or "").lower().strip()
    for model in django_apps.get_models():
        try:
            if getattr(model._meta, "model_name", "").lower() == slug_l:
                return model
        except Exception:
            continue
    raise LookupError(f"Unknown model slug: {slug}")