"""Default choice lists for the communications domain.

These tuples provide stable defaults that can seed tenant-level settings
when a database is initialized. Service teams can extend or override them
per tenant without touching model code.
"""

from typing import Final, Tuple

Choice = Tuple[str, str]
ChoiceList = Tuple[Choice, ...]

EMAIL_TYPE_CHOICES: Final[ChoiceList] = (
    ("", "Unspecified"),
    ("work", "Work"),
    ("personal", "Personal"),
    ("support", "Support"),
    ("billing", "Billing"),
    ("other", "Other"),
)

EMAIL_OPT_OUT_CHOICES: Final[ChoiceList] = (
    ("", "Active"),
    ("opted_out", "Opted Out"),
    ("bounced", "Bounced"),
    ("invalid", "Invalid"),
    ("spam_complaint", "Spam Complaint"),
)

DOMAIN_TYPE_CHOICES: Final[ChoiceList] = (
    ("website", "Website"),
    ("linkedin", "LinkedIn"),
    ("facebook", "Facebook"),
    ("twitter", "Twitter"),
    ("github", "GitHub"),
    ("other", "Other"),
)

DOMAIN_STATUS_CHOICES: Final[ChoiceList] = (
    ("", "Unspecified"),
    ("active", "Active"),
    ("verifying", "Verifying"),
    ("suspended", "Suspended"),
    ("retired", "Retired"),
)

ADDRESS_TYPE_CHOICES: Final[ChoiceList] = (
    ("billing", "Billing"),
    ("shipping", "Shipping"),
    ("headquarters", "Headquarters"),
    ("branch", "Branch"),
    ("other", "Other"),
)

DEFAULT_SELECT_LISTS: Final[dict[str, dict[str, ChoiceList]]] = {
    "Email": {
        "type": EMAIL_TYPE_CHOICES,
        "opt_out": EMAIL_OPT_OUT_CHOICES,
    },
    "Domain": {
        "type": DOMAIN_TYPE_CHOICES,
        "status": DOMAIN_STATUS_CHOICES,
    },
    "Address": {
        "address_type": ADDRESS_TYPE_CHOICES,
    },
}
