"""
Bootstrap View — serves company prefs to React at startup.

Builds a candidate tree from the company-profile Setting (currency, inventory,
costing, document_text, company, ...), then sends ONLY the dotted paths that the
requesting user's role is allowed to see. Versioned with a hash so React only
re-downloads when something changes.

Positive allowlist (Bill, 2026-09-16): "There should be a positive list of
fields/branches.leaves that can be sent based on the user and their role."
Nothing leaves the server unless listed for that role.

Allowlist location: company profile Setting config.bootstrap_exposure
    {"staff": ["currency.*", "company.name", ...],
     "user_customer": ["currency.*", "company.name", ...], ...}
Path forms:
    "company.name"   a single leaf (or a whole branch, if the value is a dict)
    "currency.*"     every direct child of currency (all of currency)

Role mapping (request.user is a core.Contact — AUTH_USER_MODEL):
    1. is_staff or is_superuser        -> role key "staff"
    2. otherwise every role in contact.refs.roles (e.g. "user_customer",
       "user_vendor", "user_manufacturer", "user_rep") is a role key; the user
       receives the UNION of the paths listed for those keys.
    3. a key with no entry in bootstrap_exposure contributes nothing. A user
       whose keys have no entries (or no roles at all) gets an empty payload
       plus _version — fail closed, never a silent default. A missing or
       malformed bootstrap_exposure section also sends nothing.

The version hash is computed over the FILTERED payload, so each role sees its
own version and a 304 never hands one role another role's copy.

Usage:
  GET /wcapi/_bootstrap/              → filtered payload
  GET /wcapi/_bootstrap/?v=<hash>     → 304 if unchanged
"""
import hashlib
import json

from django.http import HttpResponseNotModified
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

STAFF_ROLE_KEY = 'staff'


def bootstrap_role_keys(user) -> list:
    """Role keys used to look up config.bootstrap_exposure for this user."""
    if not user or not getattr(user, 'is_authenticated', False):
        return []
    if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
        return [STAFF_ROLE_KEY]
    roles = (getattr(user, 'refs', None) or {}).get('roles') or []
    # "staff" is granted only by the is_staff/is_superuser flags, never by a refs entry.
    return [r for r in roles if isinstance(r, str) and r != STAFF_ROLE_KEY]


def allowed_paths(exposure, role_keys) -> list:
    """Union of the dotted paths listed for the given role keys."""
    if not isinstance(exposure, dict):
        return []
    paths = []
    for key in role_keys:
        listed = exposure.get(key)
        if isinstance(listed, list):
            paths.extend(p for p in listed if isinstance(p, str) and p.strip())
    return paths


def filter_tree(tree: dict, paths) -> dict:
    """Copy only the listed dotted paths out of tree. Unlisted keys never appear."""
    out: dict = {}
    for path in paths:
        parts = path.strip().split('.')
        src, dst = tree, out
        for i, part in enumerate(parts):
            if not isinstance(src, dict):
                break
            last = i == len(parts) - 1
            if part == '*':
                if last:
                    for k, v in src.items():
                        dst[k] = json.loads(json.dumps(v))
                break  # wildcard is only supported as the final segment
            if part not in src:
                break
            if last:
                dst[part] = json.loads(json.dumps(src[part]))
            else:
                src = src[part]
                nxt = dst.get(part)
                if not isinstance(nxt, dict):
                    nxt = {}
                    dst[part] = nxt
                dst = nxt
    # Drop branches left empty because their leaves were absent.
    return {k: v for k, v in out.items() if v != {}}


class BootstrapView(APIView):
    http_method_names = ["get", "options", "head"]

    def get(self, request):
        from apps.core.models import Setting

        try:
            setting = Setting.objects.get(ida='company-profile', purpose='wc:company_profile')
        except Setting.DoesNotExist:
            return Response(
                {'status': 'error', 'message': 'Company profile not configured'},
                status=status.HTTP_404_NOT_FOUND,
            )

        prefs = setting.prefs or {}
        config = setting.config or {}

        # Candidate tree — everything that COULD be sent. The allowlist decides what is.
        candidates = {
            'currency': prefs.get('currency', {}),
            'order_defaults': prefs.get('order_defaults', {}),
            'price_levels': prefs.get('price_levels', {}),
            'inventory': prefs.get('inventory', {}),
            # System costing defaults live in config.inventory; the line editor
            # needs unit_cost_default to start a new line at the right cost.
            'costing': {
                k: (config.get('inventory') or {}).get(k)
                for k in ('costing_method', 'unit_cost_default', 'unit_cost_precision')
            },
            'commissions': prefs.get('commissions', {}),
            'collections': prefs.get('collections', {}),
            'document_text': prefs.get('document_text', {}),
            'behavior': prefs.get('behavior', {}),
            'fiscal': prefs.get('fiscal', {}),
            'company': config.get('company', {}),
            'logos': config.get('logos', {}),
            'print_defaults': config.get('print_defaults', {}),
        }

        paths = allowed_paths(config.get('bootstrap_exposure'),
                              bootstrap_role_keys(getattr(request, 'user', None)))
        payload = filter_tree(candidates, paths)

        # Version hash over the FILTERED payload — differs by role.
        version = hashlib.md5(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]
        payload['_version'] = version

        # If client sends ?v=<hash> and it matches, return 304
        client_version = request.query_params.get('v')
        if client_version and client_version == version:
            # A plain Django 304: a DRF Response here goes through the API renderer,
            # which wraps it in an envelope body a 304 may not carry, and the
            # browser drops the connection (ERR_CONTENT_LENGTH_MISMATCH).
            return HttpResponseNotModified()

        return Response({'status': 'success', 'data': payload})
