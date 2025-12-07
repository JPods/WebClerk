from django.db import models

from .base import OrgBase
from .constants import OrgType


# -------------- Proxy type models (ergonomic filters, no new tables) -----
class _TypeFilteredManager(models.Manager):
	def __init__(self, org_type: str):
		super().__init__()
		self._org_type = org_type

	def get_queryset(self):  # type: ignore[override]
		return super().get_queryset().filter(org_type=self._org_type)
	
	def create(self, **kwargs):
		"""Auto-set org_type when creating records through proxy models."""
		kwargs['org_type'] = self._org_type
		return super().create(**kwargs)


class Customer(OrgBase):
	class Meta:
		proxy = True
		verbose_name = "Customer"
		verbose_name_plural = "Customers"

	objects = _TypeFilteredManager(OrgType.CUSTOMER)


class Vendor(OrgBase):
	class Meta:
		proxy = True
		verbose_name = "Vendor"
		verbose_name_plural = "Vendors"

	objects = _TypeFilteredManager(OrgType.VENDOR)


class Rep(OrgBase):
	class Meta:
		proxy = True
		verbose_name = "Rep"
		verbose_name_plural = "Reps"

	objects = _TypeFilteredManager(OrgType.REP)


class Employee(OrgBase):
	class Meta:
		proxy = True
		verbose_name = "Employee"
		verbose_name_plural = "Employees"

	objects = _TypeFilteredManager(OrgType.EMPLOYEE)


class Manufacturer(OrgBase):
	class Meta:
		proxy = True
		verbose_name = "Manufacturer"
		verbose_name_plural = "Manufacturers"

	objects = _TypeFilteredManager(OrgType.MANUFACTURER)