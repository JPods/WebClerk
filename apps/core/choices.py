"""Default choice lists for the core domain.

Centralizing these tuples keeps models, serializers, and tenant seeding
aligned without duplicating literal lists of roles or workflow states.
"""

from typing import Final, Tuple

Choice = Tuple[object, str]
ChoiceList = Tuple[Choice, ...]

CONTACT_ROLE_CHOICES: Final[ChoiceList] = (
    ("user", "User"),
    ("admin", "Administrator"),
    ("manager", "Manager"),
    ("staff", "Staff"),
    ("guest", "Guest"),
)

ACTION_KANBAN_COLUMNS: Final[ChoiceList] = (
    ("Backlog", "Backlog"),
    ("Planning", "Planning"),
    ("InProcess", "In Process"),
    ("Review", "Review"),
    ("Complete", "Complete"),
)

ACTION_DIFFICULTY_LEVELS: Final[ChoiceList] = (
    (100, "Extreme"),
    (50, "Hard"),
    (15, "Moderate"),
    (10, "Normal"),
    (4, "Easy"),
    (1, "Trivial"),
)

SETTING_PURPOSE_CHOICES: Final[ChoiceList] = (
    ("view_edit", "View / Edit Matrix"),
    ("constants", "User Constants"),
    ("db_defaults", "Database Defaults"),
    ("sales_defaults", "Sales Defaults"),
    ("purchase_defaults", "Purchase Defaults"),
    ("accounting_defaults", "Accounting Defaults"),
    ("keywords", "Keyword Tracking"),
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
