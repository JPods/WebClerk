"""
Fallback VIEW_CONFIG for admin view role field configuration.

Projects can override or expand this structure as needed. The admin_view imports
VIEW_CONFIG to determine which fields to show per role/model/view type.

Structure example:
VIEW_CONFIG = {
    "admin": {
        "contact": {"detail": ["name", "email"], "list": ["name"]},
    },
}
"""

# Minimal default to avoid import errors in dev environments
VIEW_CONFIG: dict = {}
