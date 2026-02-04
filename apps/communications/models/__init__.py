# path: apps/communications/models/__init__.py
from .address import Address
from .email import Email
from .phone import Phone
from .domain import Domain

# Deprecated alias: Location was renamed to Address
Location = Address

__all__ = ["Address", "Location", "Email", "Phone", "Domain"]
