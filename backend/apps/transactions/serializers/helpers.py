"""Shared helpers for transaction serializers."""

from apps.orgs.models import OrgBase


def _name_from_refs(obj, role):
    """Read display_name from refs.links denormalized envelope.

    Falls back to FK relationship if refs data is missing.
    Never does a raw OrgBase.objects.get() query — that is an N+1 pattern.
    """
    # Primary: denormalized refs.links (zero queries)
    refs = getattr(obj, 'refs', None) or {}
    name = (refs.get('links', {}).get(role, {}).get('display_name') or '').strip()
    if name:
        return name

    # Fallback: FK relationship (uses select_related if queryset configured it)
    fk_id = getattr(obj, f'{role}_id', None)
    if fk_id:
        fk_obj = getattr(obj, role, None)
        if fk_obj is not None:
            return getattr(fk_obj, 'display_name', '') or f"Org #{fk_id}"
        return f"Org #{fk_id}"
    return None


# system fields inherited from BaseModel (read-only)
BASE_RO = [
    'id', 'uuid', 'dt_created', 'dt_modified', 'version',
    'is_deleted', 'is_archived', 'metadata', 'refs', 'prefs',
    'actions', 'comments', 'health_rating',
]
