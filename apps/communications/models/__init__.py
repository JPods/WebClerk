# path: apps/communications/models/__init__.py
from .address import Address
from .location import Location  # deprecated alias; import Address instead
from .email import Email
from .phone import Phone
from .domain import Domain

__all__ = ["Address", "Location", "Email", "Phone", "Domain"]
