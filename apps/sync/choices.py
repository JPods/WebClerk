"""Default choice lists for the sync domain."""

from typing import Final, Tuple

Choice = Tuple[str, str]
ChoiceList = Tuple[Choice, ...]

CONNECTION_TYPE_CHOICES: Final[ChoiceList] = (
    ("", "Unspecified"),
    ("api", "API"),
    ("sftp", "SFTP"),
    ("database", "Database"),
    ("webhook", "Webhook"),
    ("manual", "Manual"),
    ("internal", "Internal"),
)

CONNECTION_STATUS_CHOICES: Final[ChoiceList] = (
    ("", "Unspecified"),
    ("draft", "Draft"),
    ("active", "Active"),
    ("paused", "Paused"),
    ("error", "Error"),
    ("retired", "Retired"),
)

CONNECTION_PURPOSE_CHOICES: Final[ChoiceList] = (
    ("", "Unspecified"),
    ("ingest", "Ingest"),
    ("export", "Export"),
    ("bi", "Business Intelligence"),
    ("sync", "Bidirectional Sync"),
    ("monitor", "Monitoring"),
)

BUNDLE_DIRECTION_CHOICES: Final[ChoiceList] = (
    ("", "Unspecified"),
    ("push", "Push"),
    ("pull", "Pull"),
    ("sync", "Sync"),
)

BUNDLE_STATUS_CHOICES: Final[ChoiceList] = (
    ("", "Unspecified"),
    ("queued", "Queued"),
    ("running", "Running"),
    ("success", "Success"),
    ("warning", "Warning"),
    ("error", "Error"),
)

BUNDLE_ALERT_CHOICES: Final[ChoiceList] = (
    ("", "Unspecified"),
    ("none", "None"),
    ("info", "Info"),
    ("warning", "Warning"),
    ("critical", "Critical"),
)

DEFAULT_SELECT_LISTS: Final[dict[str, dict[str, ChoiceList]]] = {
    "Connection": {
        "type": CONNECTION_TYPE_CHOICES,
        "status": CONNECTION_STATUS_CHOICES,
        "purpose": CONNECTION_PURPOSE_CHOICES,
    },
    "Bundle": {
        "direction": BUNDLE_DIRECTION_CHOICES,
        "status": BUNDLE_STATUS_CHOICES,
        "alert": BUNDLE_ALERT_CHOICES,
    },
}
