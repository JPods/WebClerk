"""
Pydantic schemas for transaction business envelopes — the P in PJPV.

These schemas are the authoritative contract for the business JSON fields
that drive all computation: totals, finance, line price, line cost, line
quantity, and line physical. They provide:

  1. Typing     — Decimal/float/int/bool/str with explicit types
  2. Formatting  — json_schema_extra carries widget, precision, readonly
  3. Labels     — Field(title=) is the authoritative label
  4. Values     — defaults match the Python factory functions exactly
  5. Validation — ge/le/etc. catch bad data at save time

Architecture (established 2026-08-23):
  - These schemas are companions to the default_*() factory functions in
    base_transaction_model.py and base_line_model.py.
  - The totals engine (services/totals.py) validates its output against
    TransactionTotals before persisting.
  - field_behaviors.py LEAF_BEHAVIORS should be generated FROM these
    schemas, not maintained independently.

See: readmes/topics/architecture/pjpv-architecture.md
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════
# Transaction Header Envelopes
# ═══════════════════════════════════════════════════════════════════════

class TransactionCompany(BaseModel):
    """Counterparty snapshot on a transaction header.

    Built from Contact (the person) + OrgBase (the company).
    One contact = all roles (bill_to, ship_to, buy_from) until explicitly split.
    All communication fields resolve through the Contact's FK pointers
    (BigIntegerField → Address, Phone, Email, Domain records).

    Population chain:
      Transaction.contact_id → Contact (person on this document)
        fallback: Transaction.customer/vendor → OrgBase.contact_id → Contact
      Contact provides: attention, full_address, phone, email, domain
      OrgBase provides: id, ida, name (company name)
    """
    id: Optional[int] = Field(
        None, title="Org ID",
        description="OrgBase record id (customer or vendor)",
        json_schema_extra={'widget': 'lookup', 'model': 'orgbase'},
    )
    ida: str = Field(
        "", title="Org Code",
        description="Human-readable org identifier",
        json_schema_extra={'widget': 'text'},
    )
    name: str = Field(
        "", title="Company",
        description="OrgBase.display_name — the company name",
        json_schema_extra={'widget': 'text'},
    )
    contact_id: Optional[int] = Field(
        None, title="Contact ID",
        description="Contact record id (BigIntegerField, not FK)",
        json_schema_extra={'widget': 'lookup', 'model': 'contact'},
    )
    attention: str = Field(
        "", title="Attention",
        description="Person name — from Contact.attention (first + last)",
        json_schema_extra={'widget': 'text'},
    )
    full_address: str = Field(
        "", title="Address",
        description="From Contact.address_id → Address.full",
        json_schema_extra={'widget': 'textarea'},
    )
    phone: str = Field(
        "", title="Phone",
        description="From Contact.phone_id → Phone.number",
        json_schema_extra={'widget': 'phone'},
    )
    email: str = Field(
        "", title="Email",
        description="From Contact.email (scalar) or Contact.email_id → Email.email",
        json_schema_extra={'widget': 'email'},
    )
    domain: str = Field(
        "", title="Domain",
        description="From Contact.domain_id → Domain.path",
        json_schema_extra={'widget': 'text'},
    )
    is_individual: bool = Field(
        False, title="Individual",
        description="True if org is a person, not a company",
        json_schema_extra={'widget': 'boolean'},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


class TransactionTotals(BaseModel):
    """Header totals — computed by services/totals.py, never by React.

    This is the most critical PJPV schema. Every value here is computed
    by exactly one engine (recalculate_totals or update_received).
    React reads via path resolution: data?.totals?.total
    Shadow fields (header.total, header.balance) are query indexes only.
    A credit memo is an invoice with negative totals.
    """
    amount: float = Field(
        0.0,
        title="Amount",
        description="Σ line totals.amount: goods after discounts, before tax, shipping and other charges",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    discount: float = Field(
        0.0,
        title="Discount",
        description="Header discount amount",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    taxable: float = Field(
        0.0,
        title="Taxable",
        description="Subtotal minus discount — the amount subject to tax",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    tax: float = Field(
        0.0,
        title="Tax",
        description="Sales tax amount",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    shipping: float = Field(
        0.0,
        title="Shipping",
        description="Shipping and handling charged to customer",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    other: float = Field(
        0.0,
        title="Other",
        description="Miscellaneous charges",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    finance_charge: float = Field(
        0.0,
        title="Finance Charge",
        description="Sum of finance_charge lines: interest on past-due balances (config.receivables)",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    total: float = Field(
        0.0,
        title="Total",
        description="Grand total: subtotal + tax + shipping + finance_charge",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    cost: float = Field(
        0.0,
        title="Cost",
        description="Σ line totals.cost",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    margin: float = Field(
        0.0,
        title="Margin",
        description="Subtotal minus cost — NOT total minus cost",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    margin_pc: float = Field(
        0.0,
        title="Margin %",
        description="(margin / subtotal) * 100",
        json_schema_extra={'widget': 'number', 'precision': 1, 'readonly': True},
    )
    received: float = Field(
        0.0,
        title="Received",
        description="Σ applied cash (invoices); negative on a settled credit memo. Updated by update_received() only.",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    adjusted: float = Field(
        0.0, title="Adjusted",
        description="Settled without money: write-offs, small balances, FX differences",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    balance: float = Field(
        0.0,
        title="Balance",
        description="Total minus received. Updated by update_received() only.",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    cash_state: str = Field(
        '',
        title="Cash State",
        description="Derived from total and received: open | partial | paid | credit | over. Never typed.",
        json_schema_extra={'widget': 'text', 'readonly': True},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    # ── AP leaves — a receipt is a transaction too (Bill, 2026-09-19) ──
    # Landed costs spread over the lines; 'paid' is AP's 'received'.
    freight: float = Field(
        0.0, title="Freight", description="Receipt landed cost: freight, spread over the lines",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    duty: float = Field(
        0.0, title="Duty", description="Receipt landed cost: duties and tariffs, spread over the lines",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    handling: float = Field(
        0.0, title="Handling", description="Receipt landed cost: handling and insurance, spread over the lines",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    vat: float = Field(
        0.0, title="VAT", description="Receipt landed cost: VAT, spread over the lines",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    paid: float = Field(
        0.0, title="Paid", description="Cash applied against this payable — AP's 'received'",
        json_schema_extra={'widget': 'currency', 'precision': 2, 'readonly': True},
    )

    class Config:
        extra = "forbid"  # PJPV: unknown keys fail — use custom{} for extensions


class TransactionFinance(BaseModel):
    """Tax configuration and financial metadata on the transaction header."""
    sales_tax_id: int = Field(
        0, title="Sales Tax ID",
        description="FK to tax jurisdiction for sales tax",
        json_schema_extra={'widget': 'lookup', 'model': 'tax_jurisdiction'},
    )
    sales_tax_name: str = Field(
        "", title="Sales Tax Name",
        description="Display name of sales tax jurisdiction",
        json_schema_extra={'widget': 'text'},
    )
    sales_tax_rate: Optional[float] = Field(
        None, title="Sales Tax Rate",
        description="Tax rate as decimal (0.0825 = 8.25%)",
        json_schema_extra={'widget': 'number', 'precision': 6},
    )
    sales_tax: Optional[float] = Field(
        None, title="Sales Tax Amount",
        description="Computed sales tax amount",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    cost_tax_id: int = Field(
        0, title="Cost Tax ID",
        json_schema_extra={'widget': 'lookup', 'model': 'tax_jurisdiction'},
    )
    cost_tax_name: str = Field(
        "", title="Cost Tax Name",
        json_schema_extra={'widget': 'text'},
    )
    cost_tax_rate: Optional[float] = Field(
        None, title="Cost Tax Rate",
        json_schema_extra={'widget': 'number', 'precision': 6},
    )
    cost_tax: Optional[float] = Field(
        None, title="Cost Tax Amount",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    tax_subtotal: Optional[float] = Field(
        None, title="Tax Subtotal",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    tax_pc: Optional[float] = Field(
        None, title="Tax %",
        json_schema_extra={'widget': 'number', 'precision': 2},
    )
    collection_expense: Optional[float] = Field(
        None, title="Collection Expense",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    exchange_expense: Optional[float] = Field(
        None, title="Exchange Expense",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    exchange_rate: Optional[float] = Field(
        None, title="Exchange Rate",
        description="Rate captured when the document was issued; 1 or None = home currency",
        json_schema_extra={'widget': 'number', 'precision': 6},
    )
    exchange_currency: str = Field(
        "", title="Exchange Currency", description="ISO 4217 code the rate converts from",
        json_schema_extra={'widget': 'text'},
    )
    dt_exchange: Optional[int] = Field(
        None, title="Exchange Captured", description="When the rate was captured (epoch ms UTC)",
        json_schema_extra={'widget': 'date'},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


class TransactionCost(BaseModel):
    """Header-level cost summary (distinct from line-level LineCost)."""
    line_sum_goods: Optional[float] = Field(
        None, title="Line Sum Goods",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    line_sum_tax: Optional[float] = Field(
        None, title="Line Sum Tax",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    line_sum_shipping: Optional[float] = Field(
        None, title="Line Sum Shipping",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    line_sum_handling: Optional[float] = Field(
        None, title="Line Sum Handling",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    handling: Optional[float] = Field(
        None, title="Handling",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    freight: Optional[float] = Field(
        None, title="Freight",
        description="Header-level freight cost (separate from line shipping)",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    tax_rate: Optional[float] = Field(
        None, title="Cost Tax Rate",
        json_schema_extra={'widget': 'number', 'precision': 6},
    )
    tax: Optional[float] = Field(
        None, title="Cost Tax",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    commissions: Optional[float] = Field(
        None, title="Commissions",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    total: Optional[float] = Field(
        None, title="Cost Total",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


class TransactionTax(BaseModel):
    """Header-level tax configuration — per-line tax is in LineTax.

    Links to tax engine records and carries rate/amount for both sell-side
    and cost-side tax. Dollar amounts here mirror totals.tax and totals.cost_tax
    but this envelope owns the jurisdiction and rate detail.
    """
    sales_rate: Optional[float] = Field(
        None, title="Sales Tax Rate",
        description="Tax rate as decimal (0.0825 = 8.25%)",
        json_schema_extra={'widget': 'number', 'precision': 6},
    )
    sales: Optional[float] = Field(
        None, title="Sales Tax",
        description="Computed sales tax amount",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    cost_rate: Optional[float] = Field(
        None, title="Cost Tax Rate",
        json_schema_extra={'widget': 'number', 'precision': 6},
    )
    cost: Optional[float] = Field(
        None, title="Cost Tax",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    shipping: Optional[float] = Field(
        None, title="Tax on Shipping",
        description="Tax applied to shipping charges",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    tax_service_id: int = Field(
        0, title="Tax Service ID",
        description="Link to tax engine records (Avalara, TaxJar, etc.)",
        json_schema_extra={'widget': 'number'},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


class TransactionCommission(BaseModel):
    """Header-level commission summary — per-line commission is in LineCommission.

    Aggregates commission across all lines. reps[] carries the split when
    multiple reps share a transaction.
    """
    total: float = Field(
        0.0, title="Commission Total",
        description="Total commission amount across all lines",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    reps: list = Field(
        default_factory=list, title="Rep Commissions",
        description="List of {rep_id, name, rate_pct, split_pct, basis, amount}",
        json_schema_extra={'widget': 'json-tree'},
    )
    basis: str = Field(
        "revenue", title="Basis",
        description="Commission basis: revenue, margin, or cost",
        json_schema_extra={'widget': 'select', 'selectlist_key': 'commission_basis'},
    )
    method: str = Field(
        "percentage", title="Method",
        description="Calculation method: flat, percentage, or tiered",
        json_schema_extra={'widget': 'select', 'selectlist_key': 'commission_method'},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


class TransactionFlow(BaseModel):
    """Transaction lineage — where this transaction came from and what it spawned.

    source[] tracks parent transactions (e.g., the Order that became this Invoice).
    children[] tracks downstream transactions (e.g., POs created from this Order).
    """
    source: list = Field(
        default_factory=list, title="Source",
        description="Parent transactions: [{type, id}]",
        json_schema_extra={'widget': 'json-tree'},
    )
    children: list = Field(
        default_factory=list, title="Children",
        description="Downstream transactions: [{type, id}]",
        json_schema_extra={'widget': 'json-tree'},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


class TransactionSource(BaseModel):
    """Attribution — how and where this transaction originated.

    campaign_id links to a Project record used as a marketing campaign.
    vendor_id/manufacturer_id track originating supply-side entities.
    """
    campaign_id: int = Field(
        0, title="Campaign",
        description="FK to Project record used as campaign",
        json_schema_extra={'widget': 'lookup', 'model': 'project'},
    )
    campaign_name: str = Field(
        "", title="Campaign Name",
        json_schema_extra={'widget': 'text'},
    )
    catalog_id: int = Field(
        0, title="Catalog",
        json_schema_extra={'widget': 'lookup', 'model': 'catalog'},
    )
    vendor_id: int = Field(
        0, title="Vendor",
        json_schema_extra={'widget': 'lookup', 'model': 'orgbase'},
    )
    manufacturer_id: int = Field(
        0, title="Manufacturer",
        json_schema_extra={'widget': 'lookup', 'model': 'orgbase'},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


class TransactionAction(BaseModel):
    """Next-action tracking on the transaction header."""
    action_next: dict = Field(
        default_factory=lambda: {"who": "", "when": 0, "what": ""},
        title="Next Action",
        description="Who needs to do what by when",
        json_schema_extra={'widget': 'json-tree'},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


# ═══════════════════════════════════════════════════════════════════════
# Line-Level Envelopes
# ═══════════════════════════════════════════════════════════════════════

class LineQuantity(BaseModel):
    """Line quantity envelope — the three canonical keys plus controls.

    quantity.active is the verb of the document:
      quote → proposed, order → ordered, invoice → shipped,
      purchase → purchased, receipt → received, workorder → produced.

    The same three keys carry every document type:
      active    — the quantity this line is acting on
      staged    — allocated FROM parent (mirrors active for standalone)
      remaining — available FOR children = active - sum(children.active)
    """
    staged: float = Field(
        0.0, title="Qty Staged",
        description="Quantity committed from upstream (= active for standalone)",
        json_schema_extra={'widget': 'number'},
    )
    active: float = Field(
        0.0, title="Qty Active",
        description="The quantity this line is acting on (the verb of the document)",
        json_schema_extra={'widget': 'number'},
    )
    remaining: float = Field(
        0.0, title="Qty Remaining",
        description="Available for children = active - sum(children.active)",
        json_schema_extra={'widget': 'number'},
    )
    is_fixed: bool = Field(
        False, title="Qty Fixed",
        description="Whether quantity is locked from editing",
        json_schema_extra={'widget': 'boolean'},
    )
    is_complete: bool = Field(
        False, title="Qty Complete",
        description="When true, remaining is forced to 0 (backlog cancelled)",
        json_schema_extra={'widget': 'boolean'},
    )
    precision: int = Field(
        2, ge=0, le=6, title="Qty Precision",
        description="Decimal places for quantity math",
        json_schema_extra={'widget': 'number'},
    )
    is_blanket: bool = Field(
        False, title="Blanket",
        description="Blanket/open-ended quantity",
        json_schema_extra={'widget': 'boolean'},
    )
    increment: float = Field(
        0.0, ge=0, title="Increment",
        description="Minimum order increment for blanket order fulfillment",
        json_schema_extra={'widget': 'number'},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


class LinePrice(BaseModel):
    """Line price envelope — sell-side lines only (quote, order, invoice).

    Extended is computed by recalculate_line():
      inputs only; results are in line totals (LineTotals)
    """
    unit: float = Field(
        0.0, ge=0, title="Unit Price",
        description="Selling price per unit",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    unit_base: float = Field(
        0.0, ge=0, title="Base Price",
        description="Original price before discounts",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    discount_percent: float = Field(
        0.0, ge=0, le=100, title="Disc %",
        description="Discount percentage (0-100)",
        json_schema_extra={'widget': 'number', 'precision': 2},
    )
    discount_amount: float = Field(
        0.0, title="Disc Amt",
        description="Discount amount in currency",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    is_fixed: bool = Field(
        False, title="Price Fixed",
        description="Whether price is locked from editing",
        json_schema_extra={'widget': 'boolean'},
    )
    precision: int = Field(
        2, ge=0, le=6, title="Price Precision",
        description="Decimal places for price math",
        json_schema_extra={'widget': 'number'},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


LANDED_COMPONENTS = ('freight', 'duty', 'handling', 'vat')
LandedBasis = Literal['value', 'weight', 'quantity']


class LandedMethod(BaseModel):
    """How each of a receipt's landed costs spreads over its lines (Bill, 2026-09-21).

    value    — by the line's amount (qty × discounted unit cost); the default
    weight   — by qty × the line's unit weight; a line with no weight sends the whole
               component back to value, and the decision says so
    quantity — by qty received
    """
    freight: LandedBasis = Field('value', title="Freight By", json_schema_extra={'widget': 'text'})
    duty: LandedBasis = Field('value', title="Duty By", json_schema_extra={'widget': 'text'})
    handling: LandedBasis = Field('value', title="Handling By", json_schema_extra={'widget': 'text'})
    vat: LandedBasis = Field('value', title="VAT By", json_schema_extra={'widget': 'text'})

    class Config:
        extra = "forbid"


class LandedOverride(BaseModel):
    """A line's landed-cost share typed by the user. A component left empty is spread
    by the header's method over the lines that have not pinned it. The pins on a
    component may not exceed the header amount, and when every line pins it they must
    add to it exactly — otherwise the save is refused."""
    freight: Optional[float] = Field(None, ge=0, title="Freight (pinned)",
        json_schema_extra={'widget': 'currency', 'precision': 2})
    duty: Optional[float] = Field(None, ge=0, title="Duty (pinned)",
        json_schema_extra={'widget': 'currency', 'precision': 2})
    handling: Optional[float] = Field(None, ge=0, title="Handling (pinned)",
        json_schema_extra={'widget': 'currency', 'precision': 2})
    vat: Optional[float] = Field(None, ge=0, title="VAT (pinned)",
        json_schema_extra={'widget': 'currency', 'precision': 2})

    class Config:
        extra = "forbid"


class LineCost(BaseModel):
    """Line cost envelope — all lines (sell-side and exec-side).

    Extended is computed by recalculate_line():
      inputs only; results are in line totals (LineTotals)
    """
    unit: float = Field(
        0.0, ge=0, title="Unit Cost",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    unit_base: float = Field(
        0.0, ge=0, title="Base Cost",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    discount_percent: float = Field(
        0.0, ge=0, le=100, title="Disc %",
        json_schema_extra={'widget': 'number', 'precision': 2},
    )
    discount_amount: float = Field(
        0.0, title="Disc Amt",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    shipping: float = Field(
        0.0, title="Cost: Shipping",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    handling: float = Field(
        0.0, title="Cost: Handling",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    freight: float = Field(
        0.0, title="Cost: Freight",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    commissions: float = Field(
        0.0, title="Commissions",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    tax_rate: float = Field(
        0.0, ge=0, title="Cost Tax Rate",
        json_schema_extra={'widget': 'number', 'precision': 6},
    )
    tax: float = Field(
        0.0, title="Cost: Tax",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    is_fixed: bool = Field(
        False, title="Cost Fixed",
        json_schema_extra={'widget': 'boolean'},
    )
    precision: int = Field(
        2, ge=0, le=6, title="Cost Precision",
        json_schema_extra={'widget': 'number'},
    )
    tax_code: str = Field(
        "", title="Tax Code",
        description="EXEMPT, NONTAXABLE, or empty for taxable",
        json_schema_extra={'widget': 'text'},
    )
    tax_code_id: int = Field(
        0, title="Tax Code ID",
        json_schema_extra={'widget': 'lookup', 'model': 'tax_jurisdiction'},
    )
    tax_lookup_id: int = Field(
        0, title="Tax Lookup ID",
        json_schema_extra={'widget': 'number'},
    )
    landed_override: Optional[LandedOverride] = Field(
        None, title="Landed Override",
        description="Receipt lines: landed-cost shares the user pinned; the rest spread by the header's method",
        json_schema_extra={'widget': 'json-tree'},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


class LineTax(BaseModel):
    """Line-level tax envelope — per-line tax overrides and results."""
    sales_rate: Optional[float] = Field(
        None, title="Sales Tax Rate",
        description="Per-line tax rate override (decimal, not percentage)",
        json_schema_extra={'widget': 'number', 'precision': 6},
    )
    rate_source: Optional[str] = Field(
        None, title="Rate Source",
        description="'line' when sales_rate was typed on the line; the rate used is in line totals.tax_rate",
        json_schema_extra={'widget': 'text'},
    )
    cost_rate: Optional[float] = Field(
        None, title="Cost Tax Rate",
        json_schema_extra={'widget': 'number', 'precision': 6},
    )
    cost: Optional[float] = Field(
        None, title="Cost Tax",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    shipping: Optional[float] = Field(
        None, title="Tax on Shipping",
        description="Tax rate applied to shipping charges",
        json_schema_extra={'widget': 'number', 'precision': 6},
    )
    tax_service_id: int = Field(
        0, title="Tax Service ID",
        description="Link to tax engine records",
        json_schema_extra={'widget': 'number'},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


def _money(title, description):
    return Field(0.0, title=title, description=description,
                 json_schema_extra={'widget': 'currency', 'precision': 2, 'readonly': True})


class LandedShares(BaseModel):
    """The line's share of each landed cost — written only by the totals engine."""
    freight: float = _money("Freight", "Its share of the receipt's freight; adds into shipping")
    duty: float = _money("Duty", "Its share of the receipt's duty; adds into other")
    handling: float = _money("Handling", "Its share of the receipt's handling; adds into other")
    vat: float = _money("VAT", "Its share of the receipt's VAT; adds into other")

    class Config:
        extra = "forbid"


class LineTotals(BaseModel):
    """The results of a line's math, written only by the totals engine.

    The header's totals.X is Σ line totals.X for every X (Bill, 2026-09-19).
    The discounted unit comes first; the gap to an exact percentage is a rounding difference.
    """
    discounted_unit: float = Field(0.0, title="Discounted Unit",
        description="The customer's unit price after every discount, in the price's precision",
        json_schema_extra={'widget': 'currency', 'precision': 6, 'readonly': True})
    amount: float = _money("Amount", "qty.active × discounted_unit: the line's total before tax; adds into totals.amount")
    discount: float = _money("Discount", "r2(qty × unit) − amount: every discount on this line, including its share of a document discount")
    taxable: float = _money("Taxable", "The amount the tax was computed on (0 when the rate is 0)")
    tax_rate: float = Field(0.0, title="Tax Rate", description="The rate used: typed on the line, else 0 if exempt or non-taxable, else the header's",
        json_schema_extra={'widget': 'number', 'precision': 6, 'readonly': True})
    rate_source: str = Field('', title="Rate Source", description="line, header, exempt or item_exempt",
        json_schema_extra={'widget': 'text', 'readonly': True})
    tax: float = _money("Tax", "r2(amount × tax_rate) + tax on this line's shipping")
    shipping: float = _money("Shipping", "The line's own shipping and handling + its share of the document's shipping")
    other: float = _money("Other", "Its share of the document's other charges (landed costs)")
    finance_charge: float = _money("Finance Charge", "A finance_charge line's amount")
    cost: float = _money("Cost", "qty × discounted unit cost")
    margin: float = _money("Margin", "amount − cost")
    total: float = _money("Total", "amount + tax + shipping + other + finance_charge")
    landed: Optional[LandedShares] = Field(None, title="Landed",
        description="Receipt lines only: the share of each landed cost inside shipping and other",
        json_schema_extra={'widget': 'json-tree', 'readonly': True})

    class Config:
        extra = "allow"


class TransactionAllocations(BaseModel):
    """Document-level inputs the totals engine spreads over the lines — by amount, except
    a receipt's landed costs, which spread by allocations.method per component."""
    discount_percent: float = Field(0.0, title="Discount %",
        description="A discount on the whole document, as a percent of each line's discounted unit",
        json_schema_extra={'widget': 'number', 'precision': 4})
    discount_amount: float = Field(0.0, title="Discount $",
        description="A discount on the whole document, spread over the lines in proportion to their amounts",
        json_schema_extra={'widget': 'currency', 'precision': 2})
    shipping: float = Field(0.0, title="Shipping",
        description="Document shipping, spread over the lines by amount (exact cents)",
        json_schema_extra={'widget': 'currency', 'precision': 2})
    other: float = Field(0.0, title="Other",
        description="Landed costs and other charges, spread over the lines by amount (exact cents)",
        json_schema_extra={'widget': 'currency', 'precision': 2})

    # ── Buy side: a receipt's landed costs, spread the same way (Bill, 2026-09-19) ──
    freight: float = Field(0.0, title="Freight",
        description="Receipt freight, spread over the lines — lands in line totals.shipping",
        json_schema_extra={'widget': 'currency', 'precision': 2})
    duty: float = Field(0.0, title="Duty",
        description="Receipt duties and tariffs, spread over the lines — lands in line totals.other",
        json_schema_extra={'widget': 'currency', 'precision': 2})
    handling: float = Field(0.0, title="Handling",
        description="Receipt handling and insurance, spread over the lines — lands in line totals.other",
        json_schema_extra={'widget': 'currency', 'precision': 2})
    vat: float = Field(0.0, title="VAT",
        description="Receipt VAT, spread over the lines — lands in line totals.other",
        json_schema_extra={'widget': 'currency', 'precision': 2})
    method: LandedMethod = Field(default_factory=LandedMethod, title="Allocation Method",
        description="How each landed cost spreads over the lines the user has not pinned",
        json_schema_extra={'widget': 'json-tree'})

    class Config:
        extra = "forbid"


class LinePhysical(BaseModel):
    """Physical attributes for a line item — weight, dimensions, hazmat."""
    weight: float = Field(
        0.0, ge=0, title="Weight",
        json_schema_extra={'widget': 'number', 'precision': 2},
    )
    weight_unit: str = Field(
        "lb", title="Weight Unit",
        json_schema_extra={'widget': 'text'},
    )
    length: float = Field(
        0.0, ge=0, title="Length",
        json_schema_extra={'widget': 'number', 'precision': 2},
    )
    width: float = Field(
        0.0, ge=0, title="Width",
        json_schema_extra={'widget': 'number', 'precision': 2},
    )
    height: float = Field(
        0.0, ge=0, title="Height",
        json_schema_extra={'widget': 'number', 'precision': 2},
    )
    dimension_unit: str = Field(
        "in", title="Dimension Unit",
        json_schema_extra={'widget': 'text'},
    )
    volume: float = Field(
        0.0, ge=0, title="Volume",
        json_schema_extra={'widget': 'number', 'precision': 2},
    )
    package_count: int = Field(
        0, ge=0, title="Package Count",
        json_schema_extra={'widget': 'number'},
    )
    is_hazmat: bool = Field(
        False, title="Hazmat",
        json_schema_extra={'widget': 'boolean'},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


# ═══════════════════════════════════════════════════════════════════════
# Line Item & Commission Envelopes
# ═══════════════════════════════════════════════════════════════════════

class LineItem(BaseModel):
    """Denormalized item snapshot on a transaction line.

    Captures item identity at time of transaction. The item_fk FK is the
    source of truth for the relationship; this JSON carries display data
    for fast reads without joining.
    """
    item_id: Optional[int] = Field(
        None, title="Item ID",
        description="FK to Item record",
        json_schema_extra={'widget': 'lookup', 'model': 'item'},
    )
    ida_item: str = Field(
        "", title="Item Code",
        json_schema_extra={'widget': 'text'},
    )
    uuid_item: str = Field(
        "", title="Item UUID",
        json_schema_extra={'widget': 'readonly'},
    )
    description: str = Field(
        "", title="Description",
        json_schema_extra={'widget': 'text'},
    )
    description_text: str = Field(
        "", title="Description Text",
        description="Plain text version of description",
        json_schema_extra={'widget': 'textarea'},
    )
    time_lead: Optional[float] = Field(
        None, title="Lead Time",
        description="Lead time in days",
        json_schema_extra={'widget': 'number'},
    )
    addresses: list = Field(
        default_factory=list, title="Addresses",
        json_schema_extra={'widget': 'json-tree'},
    )
    unit_measure: str = Field(
        "", title="UOM",
        description="Unit of measure",
        json_schema_extra={'widget': 'text'},
    )
    sequence: int = Field(
        0, ge=0, title="Sequence",
        description="Display sequence (user-changeable)",
        json_schema_extra={'widget': 'number'},
    )
    line_number: int = Field(
        0, ge=0, title="Line Number",
        json_schema_extra={'widget': 'number'},
    )
    is_active: bool = Field(
        True, title="Active",
        json_schema_extra={'widget': 'boolean'},
    )
    is_archived: bool = Field(
        False, title="Archived",
        json_schema_extra={'widget': 'boolean'},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


class LineCommission(BaseModel):
    """Commission envelope on a transaction line — computed by commission.py."""
    total: float = Field(
        0.0, title="Commission Total",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    reps: list = Field(
        default_factory=list, title="Rep Commissions",
        description="List of {rep_id, name, rate_pct, split_pct, basis, amount}",
        json_schema_extra={'widget': 'json-tree'},
    )
    basis: str = Field(
        "revenue", title="Basis",
        description="Commission basis: revenue, margin, or cost",
        json_schema_extra={'widget': 'text'},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


# ═══════════════════════════════════════════════════════════════════════
# Item Master Envelopes
# ═══════════════════════════════════════════════════════════════════════

class PriceQtyBreak(BaseModel):
    """One row in item.price.qty_breaks[] — quantity-based pricing."""
    min_qty: int = Field(
        0, ge=0, title="Min Qty",
        description="Minimum quantity to trigger this break",
        json_schema_extra={'widget': 'number'},
    )
    unit_price: Optional[float] = Field(
        None, ge=0, title="Unit Price",
        description="Price at this break level",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    variant_item_id: Optional[int] = Field(
        None, title="Variant Item",
        description="Delegate pricing to variant item (alternative to unit_price)",
        json_schema_extra={'widget': 'lookup', 'model': 'item'},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


class CostQtyBreak(BaseModel):
    """One row in item.cost.qty_breaks[] — quantity-based costing."""
    min_qty: int = Field(
        0, ge=0, title="Min Qty",
        json_schema_extra={'widget': 'number'},
    )
    unit_cost: Optional[float] = Field(
        None, ge=0, title="Unit Cost",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


class ItemPrice(BaseModel):
    """Item.price envelope — master pricing for all price levels.

    base is the primary sell price. Level prices (retail, wholesale,
    distributor, sample) are typically percentages of base. qty_breaks
    provide volume-based pricing tiers.
    """
    base: Optional[float] = Field(
        None, title="Base Price",
        description="Primary sell price",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    msrp: Optional[float] = Field(
        None, title="MSRP",
        description="Manufacturer suggested retail price",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    retail: Optional[float] = Field(
        None, title="Retail",
        description="100% of base (price level A)",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    wholesale: Optional[float] = Field(
        None, title="Wholesale",
        description="~90% of base (price level B)",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    distributor: Optional[float] = Field(
        None, title="Distributor",
        description="~75% of base (price level C)",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    sample: Optional[float] = Field(
        None, title="Sample",
        description="~70% of base (price level D)",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    qty_breaks: list[PriceQtyBreak] = Field(
        default_factory=list, title="Qty Breaks",
        description="Quantity-based pricing tiers, sorted by min_qty ascending",
        json_schema_extra={'widget': 'json-tree'},
    )
    currency: str = Field(
        "USD", title="Currency",
        description="ISO 4217 currency code",
        json_schema_extra={'widget': 'text'},
    )
    history: list = Field(
        default_factory=list, title="Price History",
        description="Recent price adjustments (bounded, not authoritative ledger)",
        json_schema_extra={'widget': 'json-tree'},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


class ItemCost(BaseModel):
    """Item.cost envelope — cost tracking across multiple methods.

    standard is for GL alignment. last is most recent receipt. avg is
    moving average. landed includes freight/duties/overhead. components
    breaks down the landed cost allocation.
    """
    standard: Optional[float] = Field(
        None, title="Standard Cost",
        description="Standard cost (GL alignment)",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    last: Optional[float] = Field(
        None, title="Last Cost",
        description="Last receipt unit cost",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    avg: Optional[float] = Field(
        None, title="Avg Cost",
        description="Moving average cost",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    landed: Optional[float] = Field(
        None, title="Landed Cost",
        description="Landed cost including allocated freight/duty/overhead",
        json_schema_extra={'widget': 'currency', 'precision': 2},
    )
    currency: str = Field(
        "USD", title="Currency",
        description="ISO 4217 currency code",
        json_schema_extra={'widget': 'text'},
    )
    components: dict = Field(
        default_factory=dict, title="Cost Components",
        description="Breakdown: freight, duty, overhead allocations",
        json_schema_extra={'widget': 'json-tree'},
    )
    qty_breaks: list[CostQtyBreak] = Field(
        default_factory=list, title="Cost Qty Breaks",
        description="Quantity-based cost tiers",
        json_schema_extra={'widget': 'json-tree'},
    )
    history: list = Field(
        default_factory=list, title="Cost History",
        description="Recent cost field adjustments (bounded)",
        json_schema_extra={'widget': 'json-tree'},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


class ItemCatalogWeb(BaseModel):
    """Web presentation metadata for catalog display."""
    slug: str = Field("", title="URL Slug", json_schema_extra={'widget': 'text'})
    title: str = Field("", title="Page Title", json_schema_extra={'widget': 'text'})
    short: str = Field("", title="Short Description", json_schema_extra={'widget': 'textarea'})
    seo: dict = Field(default_factory=dict, title="SEO", json_schema_extra={'widget': 'json-tree'})
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


class ItemCatalog(BaseModel):
    """Item.catalog envelope — placement, attributes, web, and flags."""
    categories: list[str] = Field(
        default_factory=list, title="Categories",
        description="Ordered list of category slugs/IDs",
        json_schema_extra={'widget': 'json-tree'},
    )
    attributes: dict = Field(
        default_factory=dict, title="Attributes",
        description="Free-form specification key/value pairs",
        json_schema_extra={'widget': 'json-tree'},
    )
    web: ItemCatalogWeb = Field(
        default_factory=ItemCatalogWeb, title="Web",
        description="Web presentation: slug, title, short description, SEO",
        json_schema_extra={'widget': 'json-tree'},
    )
    flags: dict = Field(
        default_factory=dict, title="Flags",
        description="Lightweight booleans: featured, seasonal, restricted",
        json_schema_extra={'widget': 'json-tree'},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


# ═══════════════════════════════════════════════════════════════════════
# BOM Envelope
# ═══════════════════════════════════════════════════════════════════════

class BomOperationalData(BaseModel):
    """BillOfMaterial.op_data — lightweight routing and tooling notes.

    Intentionally open-ended (extra=allow). Structure emerges from usage;
    the schema declares the known fields and gives them labels.
    """
    operation: str = Field(
        "", title="Operation",
        description="Manufacturing operation or process step",
        json_schema_extra={'widget': 'text'},
    )
    work_center: str = Field(
        "", title="Work Center",
        description="Work center or machine group",
        json_schema_extra={'widget': 'text'},
    )
    setup_time: Optional[float] = Field(
        None, title="Setup Time",
        description="Setup time in minutes",
        json_schema_extra={'widget': 'number', 'precision': 1},
    )
    run_time: Optional[float] = Field(
        None, title="Run Time",
        description="Run time per unit in minutes",
        json_schema_extra={'widget': 'number', 'precision': 2},
    )
    tooling: str = Field(
        "", title="Tooling",
        description="Tooling requirements or notes",
        json_schema_extra={'widget': 'textarea'},
    )
    notes: str = Field(
        "", title="Notes",
        description="General routing/assembly notes",
        json_schema_extra={'widget': 'textarea'},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


# ═══════════════════════════════════════════════════════════════════════
# OrgBase Aspect Schemas (unified from apps/orgs/pydantic_schemas.py)
# ═══════════════════════════════════════════════════════════════════════

class OrgAddress(BaseModel):
    """One address in OrgBase.addresses[] or Contact.addresses[]."""
    id: Optional[int] = Field(None, title="Address ID")
    type: Optional[str] = Field(
        None, title="Type",
        description="billing, shipping, office, warehouse, other",
        json_schema_extra={'widget': 'select', 'selectlist_key': 'address_type'},
    )
    address1: Optional[str] = Field(None, title="Address 1", json_schema_extra={'widget': 'text'})
    address2: Optional[str] = Field(None, title="Address 2", json_schema_extra={'widget': 'text'})
    city: Optional[str] = Field(None, title="City", json_schema_extra={'widget': 'text'})
    region: Optional[str] = Field(
        None, title="State/Province",
        description="State, Province, or Region",
        json_schema_extra={'widget': 'text'},
    )
    postal: Optional[str] = Field(None, title="Postal Code", json_schema_extra={'widget': 'text'})
    country: Optional[str] = Field(
        None, title="Country",
        description="ISO 2-letter country code",
        json_schema_extra={'widget': 'text'},
    )
    geo: Optional[dict] = Field(
        None, title="Geo",
        description="{'lat': float, 'lng': float}",
        json_schema_extra={'widget': 'json-tree'},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


class OrgPhone(BaseModel):
    """One phone in OrgBase.phones[] or Contact.phones[]."""
    id: Optional[int] = Field(None, title="Phone ID")
    type: Optional[str] = Field(None, title="Type", json_schema_extra={'widget': 'text'})
    number: str = Field("", title="Number", json_schema_extra={'widget': 'phone'})
    ext: Optional[str] = Field(None, title="Extension", json_schema_extra={'widget': 'text'})
    primary: bool = Field(False, title="Primary", json_schema_extra={'widget': 'boolean'})
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


class OrgEmail(BaseModel):
    """One email in OrgBase.emails[] or Contact.emails[]."""
    id: Optional[int] = Field(None, title="Email ID")
    type: Optional[str] = Field(None, title="Type", json_schema_extra={'widget': 'text'})
    email: str = Field("", title="Email", json_schema_extra={'widget': 'email'})
    primary: bool = Field(False, title="Primary", json_schema_extra={'widget': 'boolean'})
    bounce_count: int = Field(0, ge=0, title="Bounce Count", json_schema_extra={'widget': 'number'})
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


class OrgDomain(BaseModel):
    """One domain in OrgBase.domains[]."""
    domain: str = Field("", title="Domain", json_schema_extra={'widget': 'text'})
    verified: bool = Field(False, title="Verified", json_schema_extra={'widget': 'boolean'})
    dt_verified: Optional[int] = Field(
        None, title="Verified Date",
        description="Epoch ms when domain was verified",
        json_schema_extra={'widget': 'timestamp'},
    )
    custom: dict = Field(default_factory=dict, title="Custom", description="User-defined extensions — Alice tracks and documents")

    class Config:
        extra = "forbid"


# ═══════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════
# Transaction Shipping — logistics envelope (not the dollar amount; that's totals.shipping)
# ═══════════════════════════════════════════════════════════════════════

class ShippingPackageItem(BaseModel):
    """One item in a shipping package."""
    item_id: Optional[int] = None
    description: str = ''
    quantity: float = 0.0
    weight: float = 0.0

    class Config:
        extra = 'forbid'


class ShippingCosts(BaseModel):
    """Cost breakdown for a shipment."""
    freight: float = Field(0.0, ge=0, title="Freight", description="Base carrier freight cost", json_schema_extra={'widget': 'currency', 'precision': 2})
    fuel_surcharge: float = Field(0.0, ge=0, title="Fuel Surcharge", json_schema_extra={'widget': 'currency', 'precision': 2})
    insurance: float = Field(0.0, ge=0, title="Insurance", json_schema_extra={'widget': 'currency', 'precision': 2})
    handling: float = Field(0.0, ge=0, title="Handling", json_schema_extra={'widget': 'currency', 'precision': 2})
    estimated: float = Field(0.0, ge=0, title="Estimated", description="Pre-ship estimate", json_schema_extra={'widget': 'currency', 'precision': 2})
    actual: float = Field(0.0, ge=0, title="Actual", description="What we paid the carrier", json_schema_extra={'widget': 'currency', 'precision': 2})
    customer: float = Field(0.0, ge=0, title="Customer Charge", description="What we charge the customer (mirrors totals.shipping)", json_schema_extra={'widget': 'currency', 'precision': 2})

    class Config:
        extra = 'forbid'


class ShippingPackage(BaseModel):
    """One package in a shipment (LoadTag equivalent)."""
    type: str = ''                            # box, pallet, envelope, tube
    tracking: str = ''
    weight: float = 0.0
    length: float = 0.0
    width: float = 0.0
    height: float = 0.0
    declared_value: float = 0.0
    items: list[ShippingPackageItem] = Field(default_factory=list)
    costs: ShippingCosts = Field(default_factory=ShippingCosts)

    class Config:
        extra = 'forbid'


class ShippingWeight(BaseModel):
    """Weight summary for a shipment."""
    gross: float = Field(0.0, ge=0, title="Gross Weight", json_schema_extra={'widget': 'number', 'precision': 1})
    unit: str = Field('lbs', title="Weight Unit", json_schema_extra={'widget': 'select', 'selectlist_key': 'weight_unit'})
    dimensional: float = Field(0.0, ge=0, title="Dimensional Weight", json_schema_extra={'widget': 'number', 'precision': 1})
    billable: float = Field(0.0, ge=0, title="Billable Weight", json_schema_extra={'widget': 'number', 'precision': 1})

    class Config:
        extra = 'forbid'


class ShipToSnapshot(BaseModel):
    """The address a shipment actually went to, frozen at ship time.

    Not a copy of addresses.ship_to: that is where the customer wants goods now;
    this is where these goods went. Phone is here because the carrier needs it.
    """
    company: str = Field('', title="Ship To Company")
    attention: str = Field('', title="Ship To Attention")
    full_address: str = Field('', title="Ship To Address", json_schema_extra={'widget': 'textarea'})
    phone: str = Field('', title="Ship To Phone")

    class Config:
        extra = 'forbid'


class TransactionShipping(BaseModel):
    """Shipping logistics on a transaction header — carrier, costs, weight, packages.

    packages[] is the operational array (LoadTag/LoadItem from WC2).
    """
    status: str = Field('', title="Status", description="Fulfillment status: partial, shipped, delivered", json_schema_extra={'widget': 'select', 'selectlist_key': 'shipping_status'})
    carrier: str = Field('', title="Carrier", description="UPS, FedEx, USPS, freight, etc.", json_schema_extra={'widget': 'select', 'selectlist_key': 'shipping_carrier'})
    carrier_account: str = Field('', title="Carrier Account", description="Carrier account number for third-party billing", json_schema_extra={'widget': 'text'})
    service: str = Field('', title="Service", description="Ground, 2Day, NextDay, etc.", json_schema_extra={'widget': 'select', 'selectlist_key': 'shipping_service'})
    package_count: int = Field(0, ge=0, title="Package Count", json_schema_extra={'widget': 'number'})
    ship_to: ShipToSnapshot = Field(default_factory=ShipToSnapshot)
    packages: list[ShippingPackage] = Field(default_factory=list)
    costs: ShippingCosts = Field(default_factory=ShippingCosts)
    weight: ShippingWeight = Field(default_factory=ShippingWeight)
    dt_shipped: Optional[int] = Field(None, title="Date Shipped", description="When the last package shipped (epoch ms UTC)", json_schema_extra={'widget': 'date'})
    dt_delivered: Optional[int] = Field(None, title="Date Delivered", description="Carrier delivery confirmation (epoch ms UTC)", json_schema_extra={'widget': 'date'})
    notes: str = Field('', title="Notes", json_schema_extra={'widget': 'textarea'})

    class Config:
        extra = 'forbid'


# Schema → LEAF_BEHAVIORS bridge
# ═══════════════════════════════════════════════════════════════════════

# Maps envelope field names to their Pydantic schema classes.
# Used by field_behaviors.py to generate LEAF_BEHAVIORS from schemas
# instead of maintaining a parallel hardcoded dict.
ENVELOPE_SCHEMA_MAP = {
    # Transaction header envelopes
    'company': TransactionCompany,
    'totals': TransactionTotals,
    'allocations': TransactionAllocations,
    'finance': TransactionFinance,
    'header_cost': TransactionCost,
    'header_tax': TransactionTax,
    'header_commission': TransactionCommission,
    'flow': TransactionFlow,
    'source': TransactionSource,
    'actions': TransactionAction,
    'shipping': TransactionShipping,
    # Line-level envelopes
    'quantity': LineQuantity,
    'price': LinePrice,
    'cost': LineCost,
    'tax': LineTax,
    'line_totals': LineTotals,
    'physical': LinePhysical,
    'item': LineItem,
    'commission': LineCommission,
}

# Item master envelopes — separate map because these are on Item, not transactions.
# Not included in ENVELOPE_SCHEMA_MAP to avoid field_behaviors collision
# (Item.price schema differs from line price schema).
ITEM_SCHEMA_MAP = {
    'item_price': ItemPrice,
    'item_cost': ItemCost,
    'item_catalog': ItemCatalog,
}

# ═══════════════════════════════════════════════════════════════════════
# Financial Leaf Schemas (OrgBase.financial sub-objects)
# ═══════════════════════════════════════════════════════════════════════

class FinancialCredit(BaseModel):
    """Credit tracking — customer or vendor."""
    limit: float = Field(0.0, title="Credit Limit", json_schema_extra={'widget': 'currency', 'precision': 2})
    high: float = Field(0.0, title="High Balance", json_schema_extra={'widget': 'currency', 'precision': 2})
    available: float = Field(0.0, title="Available Credit", json_schema_extra={'widget': 'currency', 'precision': 2})
    terms_days: int = Field(0, title="Terms Days", json_schema_extra={'widget': 'number'})

    class Config:
        extra = "forbid"


class FinancialAging(BaseModel):
    """AR/AP aging buckets."""
    future: float = Field(0.0, title="Future", json_schema_extra={'widget': 'currency', 'precision': 2})
    current: float = Field(0.0, title="Current", json_schema_extra={'widget': 'currency', 'precision': 2})
    period_1: float = Field(0.0, title="1-30 Days", json_schema_extra={'widget': 'currency', 'precision': 2})
    period_2: float = Field(0.0, title="31-60 Days", json_schema_extra={'widget': 'currency', 'precision': 2})
    period_3: float = Field(0.0, title="61-90+ Days", json_schema_extra={'widget': 'currency', 'precision': 2})

    class Config:
        extra = "forbid"


class FinancialSales(BaseModel):
    """Sales period totals."""
    mtd: float = Field(0.0, title="MTD", json_schema_extra={'widget': 'currency', 'precision': 2})
    ytd: float = Field(0.0, title="YTD", json_schema_extra={'widget': 'currency', 'precision': 2})
    lifetime: float = Field(0.0, title="Lifetime", json_schema_extra={'widget': 'currency', 'precision': 2})
    dt_last_sale: Optional[str] = Field(None, title="Last Sale Date", json_schema_extra={'widget': 'date'})
    last_sale_amount: float = Field(0.0, title="Last Sale Amount", json_schema_extra={'widget': 'currency', 'precision': 2})

    class Config:
        extra = "forbid"


class FinancialCash(BaseModel):
    """Cash history metrics."""
    days_avg_paid: float = Field(0.0, title="Avg Days to Pay", json_schema_extra={'widget': 'number', 'precision': 1})
    days_pay: float = Field(0.0, title="Days Pay", json_schema_extra={'widget': 'number'})
    dt_last_cash: Optional[str] = Field(None, title="Last Cash Date", json_schema_extra={'widget': 'date'})
    last_cash_amount: float = Field(0.0, title="Last Cash Amount", json_schema_extra={'widget': 'currency', 'precision': 2})

    class Config:
        extra = "forbid"


class FinancialCosts(BaseModel):
    """Cost period totals."""
    mtd: float = Field(0.0, title="MTD", json_schema_extra={'widget': 'currency', 'precision': 2})
    ytd: float = Field(0.0, title="YTD", json_schema_extra={'widget': 'currency', 'precision': 2})
    alltime: float = Field(0.0, title="All Time", json_schema_extra={'widget': 'currency', 'precision': 2})

    class Config:
        extra = "forbid"


class FinancialCollection(BaseModel):
    """Collection/receivables health."""
    cost_mtd: float = Field(0.0, title="Collection Cost MTD", json_schema_extra={'widget': 'currency', 'precision': 2})
    cost_ytd: float = Field(0.0, title="Collection Cost YTD", json_schema_extra={'widget': 'currency', 'precision': 2})
    cost_alltime: float = Field(0.0, title="Collection Cost All Time", json_schema_extra={'widget': 'currency', 'precision': 2})
    dt_last_statement: Optional[str] = Field(None, title="Last Statement", json_schema_extra={'widget': 'date'})
    dt_last_contact: Optional[str] = Field(None, title="Last Collection Contact", json_schema_extra={'widget': 'date'})
    health_score: str = Field("green", title="Health Score", json_schema_extra={'widget': 'select', 'selectlist_key': 'health_score'})
    velocity_trend: str = Field("stable", title="Velocity Trend", json_schema_extra={'widget': 'select', 'selectlist_key': 'velocity_trend'})

    class Config:
        extra = "forbid"


# ═══════════════════════════════════════════════════════════════════════
# Comments Schema (replaces hardcoded comments in field_behaviors.py)
# ═══════════════════════════════════════════════════════════════════════

class CommentsChannel(BaseModel):
    """One comment channel — list of timestamped entries."""
    public: list = Field(default_factory=list, title="Public", description="Visible to external parties")
    process: list = Field(default_factory=list, title="Process", description="Internal process notes")
    partner: list = Field(default_factory=list, title="Partner", description="Partner/vendor communication")
    notes: str = Field("", title="Notes", json_schema_extra={'widget': 'textarea'})

    class Config:
        extra = "forbid"


# ═══════════════════════════════════════════════════════════════════════
# Schema Maps — connect envelope names to Pydantic classes
# ═══════════════════════════════════════════════════════════════════════

# BOM + OrgBase aspect schemas + financial + comments
AUXILIARY_SCHEMA_MAP = {
    'bom_op_data': BomOperationalData,
    'org_address': OrgAddress,
    'org_phone': OrgPhone,
    'org_email': OrgEmail,
    'org_domain': OrgDomain,
    'financial_credit': FinancialCredit,
    'financial_aging': FinancialAging,
    'financial_sales': FinancialSales,
    'financial_cash': FinancialCash,
    'financial_costs': FinancialCosts,
    'financial_collection': FinancialCollection,
    'comments': CommentsChannel,
}


def schema_to_leaf_behaviors(schema_cls: type[BaseModel], _prefix: str = '') -> dict:
    """Convert a Pydantic schema to LEAF_BEHAVIORS format.

    Reads Field(title=, json_schema_extra={widget, precision, readonly})
    and produces the dict format that field_behaviors.py expects:
      {field_name: {type, label, precision?, readonly?}}

    A nested schema is a container, not a leaf: its fields appear under their
    dotted path ("costs.freight") and the container itself gets no entry.
    """
    import typing
    behaviors = {}
    for name, field_info in schema_cls.model_fields.items():
        ann = field_info.annotation
        if typing.get_origin(ann) in (typing.Union, getattr(__import__('types'), 'UnionType', None)):
            args = [a for a in typing.get_args(ann) if a is not type(None)]
            ann = args[0] if len(args) == 1 else ann
        if isinstance(ann, type) and issubclass(ann, BaseModel):
            behaviors.update(schema_to_leaf_behaviors(ann, f'{_prefix}{name}.'))
            continue
        extra = field_info.json_schema_extra or {}
        widget = extra.get('widget', 'text')
        entry = {
            'type': widget,
            'label': field_info.title or name,
        }
        if 'precision' in extra:
            entry['precision'] = extra['precision']
        if extra.get('readonly'):
            entry['readonly'] = True
        if field_info.description:
            entry['description'] = field_info.description
        if 'selectlist_key' in extra:
            entry['selectlist_key'] = extra['selectlist_key']
        behaviors[f'{_prefix}{name}'] = entry
    return behaviors


def get_all_leaf_behaviors() -> dict:
    """Generate complete LEAF_BEHAVIORS dict from all envelope schemas.

    Returns the same structure as the hardcoded LEAF_BEHAVIORS in
    field_behaviors.py, but derived from Pydantic schemas.
    Includes transaction envelopes, item envelopes, financial leaves,
    and comments.
    """
    result = {}
    for envelope_name, schema_cls in ENVELOPE_SCHEMA_MAP.items():
        result[envelope_name] = schema_to_leaf_behaviors(schema_cls)
    for envelope_name, schema_cls in AUXILIARY_SCHEMA_MAP.items():
        result[envelope_name] = schema_to_leaf_behaviors(schema_cls)
    return result


# ═══════════════════════════════════════════════════════════════════════
# Signoff — approval workflow on transaction config
# ═══════════════════════════════════════════════════════════════════════

class SignoffAssignee(BaseModel):
    """One approver in the signoff workflow."""
    contact_id: int
    name: str = ''
    approved: bool = False
    rejected: bool = False
    dt_requested: Optional[int] = None        # epoch ms
    dt_response: Optional[int] = None         # epoch ms
    notes: str = ''

    class Config:
        extra = 'forbid'


class SignoffBlockedTransition(BaseModel):
    """The status transition that triggered signoff."""
    from_status: str = Field('', alias='from')
    to_status: str = Field('', alias='to')

    class Config:
        extra = 'forbid'
        populate_by_name = True


class TransactionSignoff(BaseModel):
    """Approval workflow stamped on config['signoff'] by validate_status.py.

    Written to Invoice, Order, Quote, Purchase, WorkOrder.
    """
    required: bool = True
    action_id: Optional[int] = None           # linked Action record
    rule_name: str = ''
    blocked_transition: SignoffBlockedTransition = Field(
        default_factory=SignoffBlockedTransition,
    )
    assigned_to: list[SignoffAssignee] = Field(default_factory=list)
    approvals: list[dict] = Field(default_factory=list)
    status: str = 'pending'                   # pending | approved | rejected

    class Config:
        extra = 'forbid'


# ═══════════════════════════════════════════════════════════════════════
# Shipping — fulfillment structure on transaction header
# ═══════════════════════════════════════════════════════════════════════

