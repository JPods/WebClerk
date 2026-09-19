"""Org aspects — the JSON fields every organisation carries.

Customer, vendor, manufacturer, rep, employee and other orgs share one OrgBase,
so they share these shapes. Each class is the single description of its field:
the default factories in apps/orgs/models/constants.py return
``<Class>().model_dump()``, and the positive view/edit lists may name only the
leaves declared here (apps/core/services/field_leaves.py).

Counters that were open maps (stats, relationship_stats) are declared key by
key. A key that is not declared is not a leaf and cannot be shown to anyone.

Money is float. Counts and day spans are int. dt_* are epoch milliseconds (UTC).
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ── Financial: common ───────────────────────────────────────────────────

class FinAccount(BaseModel):
    dt_opened: Optional[int] = None
    dt_last_activity: Optional[int] = None
    hold: bool = False
    cod_only: bool = False
    inactive: bool = False


class FinRating(BaseModel):
    internal: Optional[str] = None       # A/B/C or 1-10, the company's own score
    comments: str = ''
    credit_score: Optional[int] = None   # external credit score


class FinSettings(BaseModel):
    discount_pct: float = 0
    tax_exempt: bool = False
    tax_exempt_id: str = ''
    terms_id: Optional[int] = None
    statement_interval_days: int = 30    # min days between statement sends
    notes: str = ''


class FinCommon(BaseModel):
    currency: str = 'USD'                # ISO 4217
    net_balance: float = 0               # net ledger balance across every role
    account: FinAccount = Field(default_factory=FinAccount)
    rating: FinRating = Field(default_factory=FinRating)
    settings: FinSettings = Field(default_factory=FinSettings)


# ── Financial: shared pieces ────────────────────────────────────────────

class Aging(BaseModel):
    future: float = 0
    period_1: float = 0                  # 1-30 days
    period_2: float = 0                  # 31-60 days
    period_3: float = 0                  # 61-90+ days


class Period(BaseModel):
    mtd: float = 0
    ytd: float = 0


class PeriodLifetime(Period):
    last_year: float = 0      # the previous calendar year
    lifetime: float = 0


class CountValue(BaseModel):
    count: int = 0
    value: float = 0


class DocStats(BaseModel):
    """Issued / canceled / executed for one document kind."""
    issued: CountValue = Field(default_factory=CountValue)
    canceled: CountValue = Field(default_factory=CountValue)
    executed: CountValue = Field(default_factory=CountValue)


class DocStatsIssuedExecuted(BaseModel):
    issued: CountValue = Field(default_factory=CountValue)
    executed: CountValue = Field(default_factory=CountValue)


class ComplaintCosts(BaseModel):
    us: float = 0
    partner: float = 0
    rep: float = 0


class Complaints(BaseModel):
    our_fault: int = 0
    their_fault: int = 0
    unresolved: int = 0
    costs: ComplaintCosts = Field(default_factory=ComplaintCosts)


class StingsReceived(BaseModel):
    count: int = 0
    value: float = 0
    paid: float = 0
    pending: float = 0


class StingsIssued(BaseModel):
    count: int = 0
    value: float = 0
    collected: float = 0
    pending: float = 0


class StingsByCategory(BaseModel):
    shipping: CountValue = Field(default_factory=CountValue)
    billing: CountValue = Field(default_factory=CountValue)
    quality: CountValue = Field(default_factory=CountValue)
    service: CountValue = Field(default_factory=CountValue)
    other: CountValue = Field(default_factory=CountValue)


class SmallStings(BaseModel):
    received: StingsReceived = Field(default_factory=StingsReceived)
    issued: StingsIssued = Field(default_factory=StingsIssued)
    by_category: StingsByCategory = Field(default_factory=StingsByCategory)


# ── Financial: customer (what they owe us) ──────────────────────────────

class CustCredit(BaseModel):
    limit: float = 0
    high: float = 0                      # historical high balance
    available: float = 0
    used: float = 0


class CustBalances(BaseModel):
    due: float = 0
    current: float = 0                   # not past due, including aging.future
    open_orders: float = 0
    total_exposure: float = 0            # due + open_orders - deposits.unapplied


class CustCash(BaseModel):
    days_avg_paid: int = 0
    invoices_settled: int = 0            # invoices in the days_avg_paid mean
    days_pay: int = 0
    dt_last_cash: Optional[int] = None
    last_cash_amount: float = 0


class CustSales(PeriodLifetime):
    dt_last_sale: Optional[int] = None
    last_sale_amount: float = 0


class CustMargin(Period):
    last_year: float = 0
    pct: float = 0            # year-to-date margin ÷ year-to-date sales × 100


class CustReturns(Period):
    count: int = 0


class CustDeposits(BaseModel):
    unapplied: float = 0                 # cash on account not yet applied (WC2 balanceAvailableCashEntries)


class CustCollection(BaseModel):
    cost_mtd: float = 0
    cost_ytd: float = 0
    cost_alltime: float = 0
    dt_last_statement: Optional[int] = None
    dt_last_contact: Optional[int] = None
    health_score: str = 'green'          # green / yellow / red
    velocity_trend: str = 'stable'       # improving / stable / deteriorating


class MinimumOrder(BaseModel):
    order: float = 0


class CustStats(BaseModel):
    quotes: DocStats = Field(default_factory=DocStats)
    orders: DocStats = Field(default_factory=DocStats)
    invoices: DocStats = Field(default_factory=DocStats)
    cash_entries: DocStats = Field(default_factory=DocStats)


class FinCustomer(BaseModel):
    credit: CustCredit = Field(default_factory=CustCredit)
    balances: CustBalances = Field(default_factory=CustBalances)
    aging: Aging = Field(default_factory=Aging)
    cash: CustCash = Field(default_factory=CustCash)
    sales: CustSales = Field(default_factory=CustSales)
    margin: CustMargin = Field(default_factory=CustMargin)
    returns: CustReturns = Field(default_factory=CustReturns)
    deposits: CustDeposits = Field(default_factory=CustDeposits)
    collection: CustCollection = Field(default_factory=CustCollection)
    minimums: MinimumOrder = Field(default_factory=MinimumOrder)
    stats: CustStats = Field(default_factory=CustStats)
    complaints: Complaints = Field(default_factory=Complaints)
    small_stings: SmallStings = Field(default_factory=SmallStings)


# ── Financial: vendor (what we owe them) ────────────────────────────────

class VendCredit(BaseModel):
    limit: float = 0
    terms_days: int = 0
    available: float = 0
    used: float = 0


class VendBalances(BaseModel):
    due: float = 0
    current: float = 0                   # not past due, including aging.future
    open_pos: float = 0


class VendPurchases(PeriodLifetime):
    dt_last_purchase: Optional[int] = None
    last_purchase_amount: float = 0


class VendCashMade(Period):
    dt_last_cash: Optional[int] = None


class VendMinimums(BaseModel):
    order: float = 0
    purchase: float = 0


class PurchaseStats(BaseModel):
    purchases: DocStats = Field(default_factory=DocStats)


class FinVendor(BaseModel):
    credit: VendCredit = Field(default_factory=VendCredit)
    balances: VendBalances = Field(default_factory=VendBalances)
    aging: Aging = Field(default_factory=Aging)
    purchases: VendPurchases = Field(default_factory=VendPurchases)
    costs: Period = Field(default_factory=Period)
    cash_entries_made: VendCashMade = Field(default_factory=VendCashMade)
    minimums: VendMinimums = Field(default_factory=VendMinimums)
    stats: PurchaseStats = Field(default_factory=PurchaseStats)
    complaints: Complaints = Field(default_factory=Complaints)
    small_stings: SmallStings = Field(default_factory=SmallStings)


# ── Financial: rep, employee, manufacturer, fx ──────────────────────────

class RepCommissions(PeriodLifetime):
    pending: float = 0
    paid: float = 0
    rate_pct: float = 0


class RepStats(BaseModel):
    quotes: DocStatsIssuedExecuted = Field(default_factory=DocStatsIssuedExecuted)
    orders: DocStatsIssuedExecuted = Field(default_factory=DocStatsIssuedExecuted)


class FinRep(BaseModel):
    commissions: RepCommissions = Field(default_factory=RepCommissions)
    sales_credited: PeriodLifetime = Field(default_factory=PeriodLifetime)
    customers_count: int = 0
    stats: RepStats = Field(default_factory=RepStats)


class EmpPayroll(BaseModel):
    salary: float = 0
    rate_hourly: float = 0
    rate_type: str = 'salary'            # salary | hourly | commission


class EmpExpenses(Period):
    pending: float = 0


class EmpTime(BaseModel):
    hours_mtd: float = 0
    hours_ytd: float = 0


class FinEmployee(BaseModel):
    payroll: EmpPayroll = Field(default_factory=EmpPayroll)
    expenses: EmpExpenses = Field(default_factory=EmpExpenses)
    commissions: Period = Field(default_factory=Period)
    time: EmpTime = Field(default_factory=EmpTime)


class MfrRebates(BaseModel):
    earned_ytd: float = 0
    received_ytd: float = 0
    pending: float = 0


class FinManufacturer(BaseModel):
    purchases: PeriodLifetime = Field(default_factory=PeriodLifetime)
    rebates: MfrRebates = Field(default_factory=MfrRebates)
    pricing_tier: Optional[str] = None
    lead_time_days: int = 0
    freight_terms: str = ''
    min_order: float = 0
    stats: PurchaseStats = Field(default_factory=PurchaseStats)


class FinFx(BaseModel):
    gain_loss_mtd: float = 0
    gain_loss_ytd: float = 0
    gain_loss_alltime: float = 0


class FinSummary(BaseModel):
    """What the source records say, next to their ledger echoes (Bill, 2026-09-19:
    "Ledger records are echos of their primary records"; unapplied cash and its
    ledger records should match). Computed, never typed."""
    receivable: float = 0             # Σ open invoice balances (invoice.totals.balance)
    receivable_ledger: float = 0      # Σ invoice ledger value_available — the echo
    unapplied_cash: float = 0         # Σ cash.available — money on account
    unapplied_cash_ledger: float = 0  # Σ cash ledger value_available, sign flipped — the echo
    net: float = 0                    # receivable − unapplied_cash
    in_step: bool = True              # every echo equals its source
    mismatches: List[str] = Field(default_factory=list)   # e.g. "invoice 132: balance 13.00, ledger 0.00"
    dt_computed: str = ''             # UTC ISO-8601


class OrgMetrics(BaseModel):
    """Keep-in-touch metrics, computed from source records (apps/orgs/services/org_metrics.py).
    Amend and reduce as experience shows what matters (Bill, 2026-09-19)."""
    dt_computed: str = ''
    periods: dict = Field(default_factory=dict)     # mtd, ytd, ytd_last_year, last_year, last_90, prior_90, lifetime
    years: list = Field(default_factory=list)       # one entry per calendar year: count, amount, margin, size_bands, channel, fulfillment, online_pickup, …
    largest: dict = Field(default_factory=dict)
    rhythm: dict = Field(default_factory=dict)      # first/last sale, days_since_last, usual_interval_days, expected_next_dt, quiet
    trend: dict = Field(default_factory=dict)
    quotes: dict = Field(default_factory=dict)
    payments: dict = Field(default_factory=dict)
    contact: dict = Field(default_factory=dict)
    proximity: dict = Field(default_factory=dict)
    size_band_edges: list = Field(default_factory=list)
    counts: dict = Field(default_factory=dict)       # legacy keys of default_metrics
    periods_legacy: dict = Field(default_factory=dict)


class OrgFinancial(BaseModel):
    """Type-keyed financial profile. An org may be several types at once."""
    summary: FinSummary = Field(default_factory=FinSummary)
    common: FinCommon = Field(default_factory=FinCommon)
    customer: FinCustomer = Field(default_factory=FinCustomer)
    vendor: FinVendor = Field(default_factory=FinVendor)
    rep: FinRep = Field(default_factory=FinRep)
    employee: FinEmployee = Field(default_factory=FinEmployee)
    manufacturer: FinManufacturer = Field(default_factory=FinManufacturer)
    fx: FinFx = Field(default_factory=FinFx)


# ── Relations and counters ──────────────────────────────────────────────

class OrgRelations(BaseModel):
    parents: List[int] = Field(default_factory=list)
    children: List[int] = Field(default_factory=list)
    linked_ids: List[int] = Field(default_factory=list)


class RelationCounts(BaseModel):
    parents: int = 0
    children: int = 0
    linked: int = 0


class RelationDtLast(BaseModel):
    parents: Optional[int] = None
    children: Optional[int] = None
    linked: Optional[int] = None


class OrgRelationshipStats(BaseModel):
    counts: RelationCounts = Field(default_factory=RelationCounts)
    dt_last: RelationDtLast = Field(default_factory=RelationDtLast)


class StatCounts(BaseModel):
    tx_total: int = 0
    tx_sale_count: int = 0
    tx_purchase_count: int = 0
    tx_return_count: int = 0
    tx_adjust_count: int = 0
    service_calls: int = 0


class StatValues(BaseModel):
    tx_sale_total_value: float = 0
    tx_purchase_total_value: float = 0
    tx_return_total_value: float = 0
    avg_margin_pct: float = 0
    last_margin_pct: float = 0
    last_sale_value: float = 0
    last_purchase_value: float = 0


class StatSample(BaseModel):
    dt: int = 0
    v: float = 0


class StatSeries(BaseModel):
    weekly_sales: List[StatSample] = Field(default_factory=list)
    margin_trend: List[StatSample] = Field(default_factory=list)


class StatLast(BaseModel):
    dt_last_sale: Optional[int] = None
    dt_last_purchase: Optional[int] = None
    dt_last_return: Optional[int] = None
    dt_last_service_call: Optional[int] = None


class RecordStats(BaseModel):
    """Per-record counters (common.stats_mixin). Shared by orgs and items."""
    counts: StatCounts = Field(default_factory=StatCounts)
    values: StatValues = Field(default_factory=StatValues)
    series: StatSeries = Field(default_factory=StatSeries)
    last: StatLast = Field(default_factory=StatLast)


# ── Lists of people, domains, documents ─────────────────────────────────

class OrgContactRef(BaseModel):
    id: Optional[int] = None
    name: str = ''
    role: str = ''


class OrgDomain(BaseModel):
    domain: str = ''
    verified: bool = False
    dt_verified: Optional[int] = None


class OrgDoc(BaseModel):
    id: Optional[int] = None
    kind: str = ''
    name: str = ''
    size: int = 0
    sha256: str = ''


class OrgConnections(BaseModel):
    """Pointers only — never a secret. e.g. email_svc = 'vault:cred:123'."""
    email_svc: Optional[str] = None


class OrgGlAccounts(BaseModel):
    """GL account per activity, e.g. sales = '4000-sales'."""
    sales: str = ''
    purchase: str = ''
    expense: str = ''
    activity: str = ''
    commission: str = ''
