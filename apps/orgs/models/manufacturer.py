from .base import OrgBase
from .constants import OrgType
from ._typed import _TypeFilteredManager, OrgTypeFinancialMixin


class Manufacturer(OrgTypeFinancialMixin, OrgBase):
    FINANCIAL_ORG_TYPE = OrgType.MANUFACTURER

    class Meta:
        proxy = True
        verbose_name = "Manufacturer"
        verbose_name_plural = "Manufacturers"

    objects = _TypeFilteredManager(OrgType.MANUFACTURER)
