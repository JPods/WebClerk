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
    (1, "Easy (1)"),
    (4, "Average (4)"),
    (8, "Hard (8)"),
    (13, "Complex (13)"),
    (21, "Expert (21)"),
)

SETTING_SCOPE_CHOICES: Final[ChoiceList] = (
    ("system", "System — all orgs, all users"),
    ("org", "Organization — one business"),
    ("role", "Role — one role within an org"),
    ("user", "User — one person"),
)

SETTING_PURPOSE_CHOICES: Final[ChoiceList] = (
    ("", ""),
    # Layout & display
    ("detail_layout", "detail_layout"),
    ("compact_layout", "compact_layout"),
    ("list_column_config", "list_column_config"),
    ("field_registry", "field_registry"),
    ("view_edit", "view_edit"),
    ("field_access", "field_access"),
    ("detail_field_access", "detail_field_access"),
    ("workbench_fields", "workbench_fields"),
    # Defaults
    ("db_defaults", "db_defaults"),
    ("constants", "constants"),
    ("sales_defaults", "sales_defaults"),
    ("purchase_defaults", "purchase_defaults"),
    ("accounting_defaults", "accounting_defaults"),
    ("accounting_interface", "accounting_interface"),
    ("print_defaults", "print_defaults"),
    # Search & keywords
    ("keywords", "keywords"),
    ("search", "search"),
    # QA
    ("qa_counters", "qa_counters"),
    ("qa_questions", "qa_questions"),
    # Alice & AI
    ("alice_pending", "alice_pending"),
    ("alice_log", "alice_log"),
    ("alice_coaching", "alice_coaching"),
    ("ai_prompt_history", "ai_prompt_history"),
    # Admin & system
    ("admin", "admin"),
    ("admin_selectlist", "admin_selectlist"),
    ("React_settings", "React_settings"),
    ("seed", "seed"),
    ("system", "system"),
    ("feature", "feature"),
    ("schema_map", "schema_map"),
    ("calculated_function", "calculated_function"),
    # Commerce & collaboration
    ("campaign", "campaign"),
    ("company_profile", "company_profile"),
    ("collaborate_webclerk", "collaborate_webclerk"),
    ("wchq_connection", "wchq_connection"),
    # Sync & storage
    ("sync_config", "sync_config"),
    ("file_storage", "file_storage"),
    # Gantt & sprint
    ("gantt_defaults", "gantt_defaults"),
    ("burndown_config", "burndown_config"),
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
