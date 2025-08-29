from rest_framework.exceptions import ValidationError
from common.models import VersionConflictError

class OptimisticPatchMixin:
    """Reusable mixin for versioned, atomic JSON PATCH operations.

    Payload contract (any model inheriting BaseModel):
      {
        "version": <int>,            # required current version
        "set": {                     # optional map of dot paths -> value
           "metadata.flags.schema_rev": 3,
           "prefs.ui.theme": "dark"
        },
        "append": {                  # optional map of list dot paths -> element to append
           "comments.notes": {"text": "hello", "type": "info"}
        }
      }

    Behavior:
      - Each successful op bumps version by 1 (atomic at row level).
      - Stale version -> VersionConflictError -> HTTP 409 handled by view.
      - If neither 'set' nor 'append' present, view should fall back to normal partial update.
    """
    version_field = 'version'

    def _split_path(self, dotted: str):
        return [p for p in dotted.split('.') if p]

    def apply_atomic_ops(self, obj, data: dict):
        expected_version = data.get(self.version_field)
        if expected_version is None:
            raise ValidationError({'version': 'This field is required for atomic patch.'})
        performed = False
        set_ops = data.get('set') or {}
        append_ops = data.get('append') or {}
        for dotted, value in set_ops.items():
            parts = self._split_path(dotted)
            if not parts:
                continue
            root = parts[0]
            if root not in {'metadata','refs','prefs','comments'}:
                raise ValidationError({dotted: 'Root must be metadata, refs, prefs, or comments'})
            obj.__class__.atomic_json_set(obj.pk, root, parts[1:], value, expected_version=expected_version)
            expected_version += 1
            performed = True
        for dotted, element in append_ops.items():
            parts = self._split_path(dotted)
            if not parts:
                continue
            root = parts[0]
            if root not in {'metadata','refs','prefs','comments'}:
                raise ValidationError({dotted: 'Root must be metadata, refs, prefs, or comments'})
            new_version = obj.__class__.atomic_list_append(obj.pk, root, parts[1:], element, expected_version=expected_version)
            expected_version = new_version
            performed = True
        if not performed:
            raise ValidationError('No atomic operations performed (provide set or append).')
        return obj.__class__.objects.get(pk=obj.pk)
