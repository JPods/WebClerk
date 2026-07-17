"""Default choice lists for the docs domain."""

from typing import Final, Tuple

Choice = Tuple[str, str]
ChoiceList = Tuple[Choice, ...]

DOCUMENT_STATUS_CHOICES: Final[ChoiceList] = (
    ("", "Unspecified"),
    ("draft", "Draft"),
    ("in_review", "In Review"),
    ("published", "Published"),
    ("archived", "Archived"),
    ("retired", "Retired"),
)

DOCUMENT_CONFIDENTIALITY_CHOICES: Final[ChoiceList] = (
    ("", "Unspecified"),
    ("public", "Public"),
    ("internal", "Internal"),
    ("restricted", "Restricted"),
    ("confidential", "Confidential"),
    ("secret", "Secret"),
)

DEFAULT_SELECT_LISTS: Final[dict[str, dict[str, ChoiceList]]] = {
    "Document": {
        "status": DOCUMENT_STATUS_CHOICES,
        "confidential": DOCUMENT_CONFIDENTIALITY_CHOICES,
    },
}
