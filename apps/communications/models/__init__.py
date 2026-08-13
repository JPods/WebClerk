# path: apps/communications/models/__init__.py
from .address import Address
from .email import Email
from .phone import Phone
from .domain import Domain
from .touch import Touch

__all__ = ["Address", "Email", "Phone", "Domain", "Touch"]
