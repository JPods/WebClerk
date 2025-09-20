import importlib

# Import submodule so its constants are defined
flow = importlib.import_module("apps.transactions.flow")

# Ensure LINE_JSON_FIELDS_TO_COPY includes "actions"
try:
    fields = getattr(flow, "LINE_JSON_FIELDS_TO_COPY", [])
    try:
        iter(fields)
    except TypeError:
        fields = []
    fields = list(fields)
    if "actions" not in fields:
        fields.append("actions")
        setattr(flow, "LINE_JSON_FIELDS_TO_COPY", fields)
except Exception:
    pass

__all__ = ["flow"]