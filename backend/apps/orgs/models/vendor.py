from .base import OrgBase
from .constants import OrgType
from ._typed import _TypeFilteredManager, OrgTypeFinancialMixin


class Vendor(OrgTypeFinancialMixin, OrgBase):
    FINANCIAL_ORG_TYPE = OrgType.VENDOR

    class Meta:
        proxy = True
        verbose_name = "Vendor"
        verbose_name_plural = "Vendors"

    objects = _TypeFilteredManager(OrgType.VENDOR)
