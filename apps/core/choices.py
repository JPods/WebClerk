"""Default choice lists for the core domain.

Centralizing these tuples keeps models, serializers, and tenant seeding
aligned without duplicating literal lists of roles or workflow states.

NOTE: During development, labels match values exactly for easier debugging.
"""

from typing import Final, Tuple

Choice = Tuple[object, str]
ChoiceList = Tuple[Choice, ...]

CONTACT_ROLE_CHOICES: Final[ChoiceList] = (
    ("", ""),
    ("user", "user"),
    ("employee", "employee"),
    ("admin", "admin"),
)

ACTION_KANBAN_COLUMNS: Final[ChoiceList] = (
    ("", ""),
    ("Backlog", "Backlog"),
    ("Planning", "Planning"),
    ("InProcess", "InProcess"),
    ("Review", "Review"),
    ("Complete", "Complete"),
)

ACTION_DIFFICULTY_LEVELS: Final[ChoiceList] = (
    (None, ""),
    (100, "100"),
    (50, "50"),
    (15, "15"),
    (10, "10"),
    (4, "4"),
    (1, "1"),
)

SETTING_PURPOSE_CHOICES: Final[ChoiceList] = (
    ("", ""),
    ("view_edit", "view_edit"),
    ("constants", "constants"),
    ("db_defaults", "db_defaults"),
    ("sales_defaults", "sales_defaults"),
    ("purchase_defaults", "purchase_defaults"),
    ("accounting_defaults", "accounting_defaults"),
    ("keywords", "keywords"),
    ("workbench_fields", "workbench_fields"),
    ("detail_field_access", "detail_field_access"),
    ("qa_counters", "qa_counters"),
    ("qa_questions", "qa_questions"),
    ("admin", "admin"),
    ("React_settings", "React_settings"),
)

DEFAULT_SELECT_LISTS: Final[dict[str, dict[str, ChoiceList]]] = {
    "Contact": {
        "role": CONTACT_ROLE_CHOICES,
    },
    "Action": {
        "kanban_column": ACTION_KANBAN_COLUMNS,
        "difficulty": ACTION_DIFFICULTY_LEVELS,
    },
    "Setting": {
        "purpose": SETTING_PURPOSE_CHOICES,
    },
}
