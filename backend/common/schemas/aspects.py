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


# ── Document parties: the one list ──────────────────────────────
# Which party blocks each document carries, and who fills each (Bill, 2026-11-12). Everything
# that needs to know reads this table: the schema classes below (and so the access leaves,
# apps/core/services/field_leaves), the party fill (apps/transactions/services/party_fill)
# and the check that layouts and stored access sets name only these (tests/test_document_parties).
# A block is filled by the document's 'customer' or 'vendor' when that party is picked, by the
# 'company' (our own profile) when blank, or by nobody (None: the person, or a conversion).
SALE_PARTIES = {'bill_to': 'customer', 'ship_to': 'customer'}
DOCUMENT_PARTIES = {
    'quote': SALE_PARTIES, 'order': SALE_PARTIES, 'invoice': SALE_PARTIES,
    'workorder': SALE_PARTIES,                     # a requisition carries no party blocks
    # Who we buy from, and our own bill-to and ship-to.
    'purchase': {'vendor': 'vendor', 'bill_to': 'company', 'ship_to': 'company'},
    # A receipt carries who the goods came from — its purchase's vendor block as it was when
    # they arrived (convert copies it), else the vendor's own. It has no bill-to or ship-to.
    'receipt': {'vendor': 'vendor'},
}
ASPECT_ENTRIES = {'addresses': AddressEntry, 'emails': EmailEntry, 'phones': PhoneEntry}


def party_roles(model_key: str) -> tuple:
    """The party blocks a document carries, in the table's order; () for a model with none."""
    return tuple(DOCUMENT_PARTIES.get(model_key, {}))


def roles_filled_by(model_key: str, source: str) -> tuple:
    """The blocks ``source`` ('customer', 'vendor' or 'company') fills on this document."""
    return tuple(role for role, by in DOCUMENT_PARTIES.get(model_key, {}).items() if by == source)


def counterparty_role(model_key: str):
    """The block that holds the document's counterparty — the customer's on a sale (bill_to),
    the vendor's on a purchase; None for a document whose blocks no party fills."""
    return next((role for role, by in DOCUMENT_PARTIES.get(model_key, {}).items()
                 if by in ('customer', 'vendor')), None)


def _aspect_class(name: str, aspect: str, roles) -> type:
    from pydantic import create_model
    entry = ASPECT_ENTRIES[aspect]
    cls = create_model(name, __config__={'extra': 'allow'},
                       **{role: (entry, Field(default_factory=entry)) for role in roles})
    cls.__doc__ = f'{aspect} aspect: {", ".join(roles)}.'
    cls.__module__ = __name__
    return cls


def aspect_class_name(model_key: str, aspect: str) -> str:
    """'PurchaseAddresses' for a document with its own roles; 'TransactionAddresses' for a sale's."""
    own = DOCUMENT_PARTIES.get(model_key) not in (None, SALE_PARTIES) and \
        tuple(DOCUMENT_PARTIES[model_key]) != tuple(SALE_PARTIES)
    return f"{model_key.capitalize() if own else 'Transaction'}{aspect.capitalize()}"


# One class per distinct set of roles, named for its document (TransactionAddresses for a sale's
# bill_to / ship_to; PurchaseAddresses adds vendor), built from the table — never typed twice.
for _model, _parties in DOCUMENT_PARTIES.items():
    for _aspect in ASPECT_ENTRIES:
        _name = aspect_class_name(_model, _aspect)
        if _name not in globals():
            globals()[_name] = _aspect_class(_name, _aspect, tuple(_parties))


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
