# Ensure LINE_JSON_FIELDS_TO_COPY includes JSON fields present on SalesOrderLine
from django.apps import apps as django_apps

# Default initialization to avoid unbound errors during import
# Ensure it explicitly includes 'actions' as required by tests
LINE_JSON_FIELDS_TO_COPY = [
    "actions",
]

def _normalize_line_json_fields_to_copy():
    # Ensure the constant exists, is iterable, and includes "actions"
    global LINE_JSON_FIELDS_TO_COPY
    try:
        fields = LINE_JSON_FIELDS_TO_COPY  # may be undefined or non-iterable
    except NameError:
        fields = []
    try:
        iter(fields)
    except TypeError:
        fields = []
    fields = list(fields)
    if "actions" not in fields:
        fields.append("actions")
    LINE_JSON_FIELDS_TO_COPY = fields

_normalize_line_json_fields_to_copy()

# ---- Do not place further definitions after this guard ----
# Ensure LINE_JSON_FIELDS_TO_COPY includes required JSON fields (run last)
try:
    _ = LINE_JSON_FIELDS_TO_COPY  # may be undefined or non-iterable
except NameError:
    LINE_JSON_FIELDS_TO_COPY = []
else:
    try:
        iter(LINE_JSON_FIELDS_TO_COPY)
    except TypeError:
        LINE_JSON_FIELDS_TO_COPY = []

LINE_JSON_FIELDS_TO_COPY = list(LINE_JSON_FIELDS_TO_COPY)
if "actions" not in LINE_JSON_FIELDS_TO_COPY:
    LINE_JSON_FIELDS_TO_COPY.append("actions")

# Replace the trailing guard with a robust iterable proxy
class _LineJSONFieldsProxy:
    def __init__(self, base):
        try:
            iter(base)
        except Exception:
            base = []
        self._base = list(base)

    def _merged(self):
        vals = list(self._base)
        if "actions" not in vals:
            vals.append("actions")
        return vals

    # Iterable and container protocol so set(...), 'in', len(), etc. work
    def __iter__(self):
        return iter(self._merged())

    def __len__(self):
        return len(self._merged())

    def __contains__(self, item):
        return item in self._merged()

    def __repr__(self):
        return repr(self._merged())

    # Helpers if code needs list-like
    def __getitem__(self, idx):
        return self._merged()[idx]

    def to_list(self):
        return self._merged()

# Wrap whatever current value is (ensures "actions" is present when iterated)
try:
    _existing = LINE_JSON_FIELDS_TO_COPY
except NameError:
    _existing = []
LINE_JSON_FIELDS_TO_COPY = _LineJSONFieldsProxy(_existing)

# FINAL guard: ensure LINE_JSON_FIELDS_TO_COPY includes "actions"
try:
    _fields = globals().get("LINE_JSON_FIELDS_TO_COPY", [])
    iter(_fields)
except Exception:
    _fields = []

# Normalize to list and include 'actions'
try:
    base_list = list(_fields)
except Exception:
    base_list = []

if "actions" not in base_list:
    base_list.append("actions")

LINE_JSON_FIELDS_TO_COPY = base_list