from .base import OrgBase
from .constants import OrgType
from ._typed import _TypeFilteredManager, OrgTypeFinancialMixin


class Rep(OrgTypeFinancialMixin, OrgBase):
    FINANCIAL_ORG_TYPE = OrgType.REP

    class Meta:
        proxy = True
        verbose_name = "Rep"
        verbose_name_plural = "Reps"

    objects = _TypeFilteredManager(OrgType.REP)
