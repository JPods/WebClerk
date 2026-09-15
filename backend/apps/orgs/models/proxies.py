"""Proxy model re-exports.

Per-type model definitions live in:
  customer.py, vendor.py, rep.py, employee.py, manufacturer.py
"""

from .customer import Customer
from .vendor import Vendor
from .rep import Rep
from .employee import Employee
from .manufacturer import Manufacturer

__all__ = ["Customer", "Vendor", "Rep", "Employee", "Manufacturer"]