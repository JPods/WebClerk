from .base import OrgBase
from .constants import OrgType
from ._typed import _TypeFilteredManager, OrgTypeFinancialMixin


class Employee(OrgTypeFinancialMixin, OrgBase):
    FINANCIAL_ORG_TYPE = OrgType.EMPLOYEE

    class Meta:
        proxy = True
        verbose_name = "Employee"
        verbose_name_plural = "Employees"

    objects = _TypeFilteredManager(OrgType.EMPLOYEE)
