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
    ("search", "search"),
    ("workbench_fields", "workbench_fields"),
    ("detail_field_access", "detail_field_access"),
    ("qa_counters", "qa_counters"),
    ("qa_questions", "qa_questions"),
    ("admin", "admin"),
    ("admin_selectlist", "admin_selectlist"),
    ("React_settings", "React_settings"),
    ("list_column_config", "list_column_config"),
    ("alice_pending", "alice_pending"),
    ("alice_log", "alice_log"),
    ("field_access", "field_access"),
    ("seed", "seed"),
    ("alice_coaching", "alice_coaching"),
    ("campaign", "campaign"),
    ("company_profile", "company_profile"),
    ("accounting_interface", "accounting_interface"),
    ("wchq_connection", "wchq_connection"),
    ("ai_prompt_history", "ai_prompt_history"),
    ("calculated_function", "calculated_function"),
    ("print_defaults", "print_defaults"),
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
    "Report": {
        "output_type": (
            ("print", "Print / PDF"),
            ("email", "Email (SMTP)"),
            ("api", "POST to external endpoint"),
            ("json", "Return structured JSON"),
            ("export", "CSV / Excel download"),
            ("label", "Label / barcode print"),
            ("merge", "Word / spreadsheet merge"),
        ),
        "category": (
            ("report", "Report"),
            ("statement", "Statement"),
            ("list", "List"),
            ("summary", "Summary"),
            ("letter", "Letter / Email"),
            ("label", "Label"),
            ("export", "Export"),
            ("utility", "Utility"),
        ),
    },
}
