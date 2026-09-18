"""Default choice lists for the orgs domain."""

from typing import Final, Tuple

from apps.orgs.models.constants import OrgType

Choice = Tuple[str, str]
ChoiceList = Tuple[Choice, ...]

ORG_TYPE_CHOICES: Final[ChoiceList] = tuple(OrgType.choices)  # reuse TextChoices definition

ORG_STATUS_CHOICES: Final[ChoiceList] = (
    ("", "Unspecified"),
    ("active", "Active"),
    ("default_company", "Default Company"),
    ("prospect", "Prospect"),
    ("suspended", "Suspended"),
    ("inactive", "Inactive"),
    ("retired", "Retired"),
)

RELATION_KIND_CHOICES: Final[ChoiceList] = (
    ("parent", "Parent"),
    ("child", "Child"),
    ("partner", "Partner"),
    ("affiliate", "Affiliate"),
    ("other", "Other"),
)

DEFAULT_SELECT_LISTS: Final[dict[str, dict[str, ChoiceList]]] = {
    "OrgBase": {
        "org_type": ORG_TYPE_CHOICES,
        "status": ORG_STATUS_CHOICES,
    },
}
