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
    ("inquiry", "Inquiry"),
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
