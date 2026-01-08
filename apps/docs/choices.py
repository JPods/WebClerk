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

DOCUMENT_MODEL_CHOICES: Final[ChoiceList] = (
    ("", "Unspecified"),
    ("readme", "Readme"),
    ("policy", "Policy"),
    ("spec", "Specification"),
    ("contract", "Contract"),
    ("template", "Template"),
)

DEFAULT_SELECT_LISTS: Final[dict[str, dict[str, ChoiceList]]] = {
    "Document": {
        "status": DOCUMENT_STATUS_CHOICES,
        "confidential": DOCUMENT_CONFIDENTIALITY_CHOICES,
        "model_name": DOCUMENT_MODEL_CHOICES,
    },
}
