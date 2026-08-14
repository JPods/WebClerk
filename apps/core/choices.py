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

ACTION_TYPE_CHOICES: Final[ChoiceList] = (
    ("", ""),
    ("call", "Call"),
    ("email", "Email"),
    ("visit", "Visit"),
    ("meeting", "Meeting"),
    ("demo", "Demo"),
    ("marketing", "Marketing"),
    ("referral", "Referral"),
    ("social", "Social Media"),
    ("event", "Event"),
    ("follow_up", "Follow-up"),
    ("other", "Other"),
)

ACTION_IMPACT_CHOICES: Final[ChoiceList] = (
    (0, "Not rated"),
    (1, "Minimal (1)"),
    (2, "Low (2)"),
    (3, "Moderate (3)"),
    (4, "High (4)"),
    (5, "Critical (5)"),
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
    ("wc:detail_layout", "wc:detail_layout"),
    ("wc:print_layout", "wc:print_layout"),
    ("compact_layout", "compact_layout"),
    ("wc:list_column_config", "wc:list_column_config"),
    ("field_registry", "field_registry"),
    ("wc:view_edit", "wc:view_edit"),
    ("wc:field_access", "wc:field_access"),
    ("detail_field_access", "detail_field_access"),
    ("wc:workbench_fields", "wc:workbench_fields"),
    # Defaults
    ("wc:db_defaults", "wc:db_defaults"),
    ("constants", "constants"),
    ("sales_defaults", "sales_defaults"),
    ("purchase_defaults", "purchase_defaults"),
    ("accounting_defaults", "accounting_defaults"),
    ("accounting_interface", "accounting_interface"),
    ("wc:print_defaults", "wc:print_defaults"),
    # Search & keywords
    ("wc:keywords", "wc:keywords"),
    ("wc:search", "wc:search"),
    # QA
    ("wc:qa_counters", "wc:qa_counters"),
    ("wc:qa_questions", "wc:qa_questions"),
    # Alice & AI
    ("alice_pending", "alice_pending"),
    ("alice_log", "alice_log"),
    ("wc:alice_coaching", "wc:alice_coaching"),
    ("ai_prompt_history", "ai_prompt_history"),
    # Admin & system
    ("wc:admin", "wc:admin"),
    ("wc:selectlist", "wc:selectlist"),
    ("wc:react_settings", "wc:react_settings"),
    ("seed", "seed"),
    ("wc:system", "wc:system"),
    ("wc:feature", "wc:feature"),
    ("wc:schema_map", "wc:schema_map"),
    ("calculated_function", "calculated_function"),
    # Conditions — document terms/conditions templates
    ("wc:conditions_sales", "wc:conditions_sales"),
    ("conditions_purchase", "conditions_purchase"),
    # Commerce & collaboration
    ("user:campaign", "user:campaign"),
    ("wc:company_profile", "wc:company_profile"),
    ("wc:collaborate", "wc:collaborate"),
    ("wc:wchq_connection", "wc:wchq_connection"),
    # Sync & storage
    ("sync_config", "sync_config"),
    ("file_storage", "file_storage"),
    # Gantt & sprint
    ("gantt_defaults", "gantt_defaults"),
    ("burndown_config", "burndown_config"),
    # Line card
    ("line_card_fields", "line_card_fields"),
    # UI behaviors
    ("wc:ui", "wc:ui"),
    # Payment
    ("wc:payment_gateway", "wc:payment_gateway"),
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
