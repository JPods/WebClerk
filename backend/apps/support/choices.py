"""Default choice lists for the support domain."""

from typing import Final, Tuple

Choice = Tuple[str, str]
ChoiceList = Tuple[Choice, ...]

CAMPAIGN_PACE_CHOICES: Final[ChoiceList] = (
    ("planning", "Planning"),
    ("in_market", "In Market"),
    ("paused", "Paused"),
    ("completed", "Completed"),
)

CAMPAIGN_SIZE_CHOICES: Final[ChoiceList] = (
    ("xs", "XS"),
    ("sm", "Small"),
    ("md", "Medium"),
    ("lg", "Large"),
    ("xl", "XL"),
)

MARKET_EFFORT_CHOICES: Final[ChoiceList] = (
    ("email", "Email"),
    ("events", "Events"),
    ("ads", "Advertising"),
    ("social", "Social"),
    ("other", "Other"),
)

DEFAULT_SELECT_LISTS: Final[dict[str, dict[str, ChoiceList]]] = {
    "Campaign": {
        "pace": CAMPAIGN_PACE_CHOICES,
        "size": CAMPAIGN_SIZE_CHOICES,
        "market_effort": MARKET_EFFORT_CHOICES,
    },
}
