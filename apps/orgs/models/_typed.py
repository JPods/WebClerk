from __future__ import annotations

from django.db import models

from .constants import (
    OrgType,
    default_financial,
    flatten_financial_for_type,
    inflate_flat_financial_for_type,
)


class _TypeFilteredManager(models.Manager):
    def __init__(self, org_type: str):
        super().__init__()
        self._org_type = org_type

    def get_queryset(self):  # type: ignore[override]
        return super().get_queryset().filter(org_type=self._org_type)

    def create(self, **kwargs):
        kwargs["org_type"] = self._org_type
        return super().create(**kwargs)


class OrgTypeFinancialMixin:
    """Expose per-org-type flat financial helpers while keeping DB JSON type-keyed.

    Storage remains:
      financial = {common:{...}, customer/vendor/...:{...}, fx:{...}}

    Flat view returns:
      {<common fields>, <type fields>, fx:{...}, _org_type:"customer"}
    """

    FINANCIAL_ORG_TYPE: str = OrgType.CUSTOMER

    def get_flat_financial(self) -> dict:
        return flatten_financial_for_type(
            getattr(self, "financial", None),
            self.FINANCIAL_ORG_TYPE,
        )

    @property
    def financial_flat(self) -> dict:
        """Flat model-centric financial view for this org type."""
        return self.get_flat_financial()

    @financial_flat.setter
    def financial_flat(self, payload: dict | None) -> None:
        self.set_flat_financial(payload)

    def set_flat_financial(self, payload: dict | None) -> None:
        self.financial = inflate_flat_financial_for_type(
            payload,
            self.FINANCIAL_ORG_TYPE,
            getattr(self, "financial", None),
        )

    @classmethod
    def financial_flat_defaults(cls) -> dict:
        """Flat defaults for this org type (derived from canonical defaults)."""
        return flatten_financial_for_type(default_financial(), cls.FINANCIAL_ORG_TYPE)
