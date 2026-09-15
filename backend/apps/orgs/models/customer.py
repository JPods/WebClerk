from .base import OrgBase
from .constants import OrgType
from ._typed import _TypeFilteredManager, OrgTypeFinancialMixin


class Customer(OrgTypeFinancialMixin, OrgBase):
    FINANCIAL_ORG_TYPE = OrgType.CUSTOMER

    class Meta:
        proxy = True
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    objects = _TypeFilteredManager(OrgType.CUSTOMER)
