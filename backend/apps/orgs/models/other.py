from .base import OrgBase
from .constants import OrgType
from ._typed import _TypeFilteredManager, OrgTypeFinancialMixin


class Other(OrgTypeFinancialMixin, OrgBase):
    """Catch-all org type for regulators, government agencies, associations,
    utilities, and any entity that is not a customer, vendor, manufacturer,
    rep, or employee but still needs to be tracked and touched."""
    FINANCIAL_ORG_TYPE = OrgType.OTHER

    class Meta:
        proxy = True
        verbose_name = "Other Org"
        verbose_name_plural = "Other Orgs"

    objects = _TypeFilteredManager(OrgType.OTHER)
