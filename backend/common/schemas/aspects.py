"""
Pydantic schemas for party-keyed communication aspects.

Three models × three contexts:

  Contact:     home, work, primary, mobile, office
  OrgBase:     prime, bill_to, ship_to
  Transaction: bill_to, ship_to

Each aspect type (address, email, phone) uses the same entry schema
but different party keys per model context.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ── Entry schemas (the leaf objects) ─────────────────────────────

class AddressEntry(BaseModel):
    """Single address within a party-keyed aspect."""
    contact_id: Optional[int] = None
    company: str = ""
    attention: str = ""
    full_address: str = ""
    instructions: str = Field(default="", max_length=255)

    class Config:
        extra = "allow"


class EmailEntry(BaseModel):
    """Single email within a party-keyed aspect."""
    email_id: Optional[int] = None
    email: str = ""

    class Config:
        extra = "allow"


class PhoneEntry(BaseModel):
    """Single phone within a party-keyed aspect."""
    phone_id: Optional[int] = None
    number: str = ""

    class Config:
        extra = "allow"


# ── Transaction aspects (bill_to / ship_to) ─────────────────────

class TransactionAddresses(BaseModel):
    """addresses aspect on Proposal, Order, Invoice, Purchase."""
    bill_to: AddressEntry = Field(default_factory=AddressEntry)
    ship_to: AddressEntry = Field(default_factory=AddressEntry)

    class Config:
        extra = "allow"


class TransactionEmails(BaseModel):
    """emails aspect on Proposal, Order, Invoice, Purchase."""
    bill_to: EmailEntry = Field(default_factory=EmailEntry)
    ship_to: EmailEntry = Field(default_factory=EmailEntry)

    class Config:
        extra = "allow"


class TransactionPhones(BaseModel):
    """phones aspect on Proposal, Order, Invoice, Purchase."""
    bill_to: PhoneEntry = Field(default_factory=PhoneEntry)
    ship_to: PhoneEntry = Field(default_factory=PhoneEntry)

    class Config:
        extra = "allow"


# ── OrgBase aspects (prime / bill_to / ship_to) ─────────────────

class OrgAddresses(BaseModel):
    """addresses aspect on OrgBase (customer, vendor, etc.)."""
    prime: AddressEntry = Field(default_factory=AddressEntry)
    bill_to: AddressEntry = Field(default_factory=AddressEntry)
    ship_to: AddressEntry = Field(default_factory=AddressEntry)

    class Config:
        extra = "allow"


class OrgEmails(BaseModel):
    """emails aspect on OrgBase."""
    prime: EmailEntry = Field(default_factory=EmailEntry)
    bill_to: EmailEntry = Field(default_factory=EmailEntry)
    ship_to: EmailEntry = Field(default_factory=EmailEntry)

    class Config:
        extra = "allow"


class OrgPhones(BaseModel):
    """phones aspect on OrgBase."""
    prime: PhoneEntry = Field(default_factory=PhoneEntry)
    bill_to: PhoneEntry = Field(default_factory=PhoneEntry)
    ship_to: PhoneEntry = Field(default_factory=PhoneEntry)

    class Config:
        extra = "allow"


# ── Contact aspects (personal keys) ─────────────────────────────

class ContactAddresses(BaseModel):
    """addresses aspect on Contact."""
    home: AddressEntry = Field(default_factory=AddressEntry)
    work: AddressEntry = Field(default_factory=AddressEntry)

    class Config:
        extra = "allow"


class ContactEmails(BaseModel):
    """emails aspect on Contact."""
    primary: EmailEntry = Field(default_factory=EmailEntry)
    work: EmailEntry = Field(default_factory=EmailEntry)

    class Config:
        extra = "allow"


class ContactPhones(BaseModel):
    """phones aspect on Contact."""
    mobile: PhoneEntry = Field(default_factory=PhoneEntry)
    office: PhoneEntry = Field(default_factory=PhoneEntry)

    class Config:
        extra = "allow"
