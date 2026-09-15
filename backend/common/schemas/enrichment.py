"""
Pydantic schemas for model enrichment panels — what detail pages show.

These schemas define the structure of `setting.item_model`, `setting.contact_model`,
and `setting.org_model` records. The UI reads these Settings to know which
enrichment panels to render on each model's detail page.

Each panel defines:
  - key: identifies the panel and maps to a data source
  - label: display name
  - source: where the data comes from (field path on the record)
  - fields: which sub-fields to show
  - read_only: if true, display only (no inline edit)
  - collapsed: if true, panel starts collapsed

The panel list is ordered — top panels render first.

Established: 2026-08-09
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ── Shared panel building blocks ──

class PanelField(BaseModel):
    """A single field within an enrichment panel."""
    field: str                        # dot-path to the value
    label: str                        # display label
    format: Optional[str] = None      # currency, percent, date, number, badge
    width: Optional[str] = None       # flex fraction or fixed px

    class Config:
        extra = "forbid"


class EnrichmentPanel(BaseModel):
    """One panel on a model detail page."""
    key: str                          # unique panel identifier
    label: str                        # section heading
    source: str                       # data source path (e.g., "stats", "financial.customer")
    fields: list[PanelField] = Field(default_factory=list)
    read_only: bool = True            # enrichment panels are read-only by default
    collapsed: bool = False           # start expanded unless explicitly collapsed
    condition: Optional[str] = None   # optional: only show when this field is truthy

    class Config:
        extra = "forbid"


# ── Item enrichment ──

class ItemEnrichment(BaseModel):
    """setting.item_model — panels shown on item detail pages.

    Data sources:
      - price.*           Item.price JSON (base, msrp, levels, breaks)
      - cost.*            Item.cost JSON (standard, last, avg, landed)
      - quantity.*        Item.quantity JSON (on_hand, available, on_so, etc.)
      - catalog.*         Item.catalog JSON (categories, attributes, web)
      - stats.*           Item.stats JSON (StatsMixin: counts, values, series)
      - flags.*           Item.flags JSON (serialized, discountable, etc.)
      - tax_code.*        Item.tax_code JSON
      - gls.*             Item.gls JSON (revenue, inventory, cogs accounts)
      - margin_velocity   promoted column
      - margin_pct        promoted column
      - annual_turns      promoted column
    """
    panels: list[EnrichmentPanel] = Field(default_factory=lambda: [
        EnrichmentPanel(
            key='sales_performance',
            label='Sales Performance',
            source='stats',
            fields=[
                PanelField(field='counts.tx_sale_count', label='Sales Count', format='number'),
                PanelField(field='values.tx_sale_total_value', label='Total Revenue', format='currency'),
                PanelField(field='values.avg_margin_pct', label='Avg Margin', format='percent'),
                PanelField(field='last.dt_last_sale', label='Last Sale', format='date'),
                PanelField(field='last.dt_last_purchase', label='Last Purchase', format='date'),
            ],
        ),
        EnrichmentPanel(
            key='margin_velocity',
            label='Margin Velocity',
            source='',
            fields=[
                PanelField(field='margin_velocity', label='Velocity Score', format='number'),
                PanelField(field='margin_pct', label='Margin %', format='percent'),
                PanelField(field='annual_turns', label='Annual Turns', format='number'),
                PanelField(field='velocity_category', label='Category', format='badge'),
            ],
        ),
        EnrichmentPanel(
            key='inventory',
            label='Inventory',
            source='quantity',
            fields=[
                PanelField(field='on_hand', label='On Hand', format='number'),
                PanelField(field='available', label='Available', format='number'),
                PanelField(field='on_so', label='On SO', format='number'),
                PanelField(field='on_po', label='On PO', format='number'),
                PanelField(field='on_wo', label='On WO', format='number'),
                PanelField(field='inventory_min', label='Reorder Point', format='number'),
                PanelField(field='inventory_max', label='Max Stock', format='number'),
            ],
        ),
        EnrichmentPanel(
            key='pricing',
            label='Pricing',
            source='price',
            fields=[
                PanelField(field='base', label='Base Price', format='currency'),
                PanelField(field='msrp', label='MSRP', format='currency'),
                PanelField(field='retail', label='Retail', format='currency'),
                PanelField(field='wholesale', label='Wholesale', format='currency'),
                PanelField(field='distributor', label='Distributor', format='currency'),
            ],
        ),
        EnrichmentPanel(
            key='costing',
            label='Costing',
            source='cost',
            fields=[
                PanelField(field='standard', label='Standard Cost', format='currency'),
                PanelField(field='last', label='Last Cost', format='currency'),
                PanelField(field='avg', label='Average Cost', format='currency'),
                PanelField(field='landed', label='Landed Cost', format='currency'),
            ],
        ),
        EnrichmentPanel(
            key='gl_accounts',
            label='GL Accounts',
            source='gls',
            collapsed=True,
            fields=[
                PanelField(field='revenue', label='Revenue'),
                PanelField(field='inventory', label='Inventory'),
                PanelField(field='cogs', label='COGS'),
                PanelField(field='purchase', label='Purchase'),
                PanelField(field='variance', label='Variance'),
            ],
        ),
        EnrichmentPanel(
            key='images',
            label='Images',
            source='catalog.web',
            collapsed=True,
            fields=[
                PanelField(field='image_url', label='Primary Image'),
                PanelField(field='thumbnail_url', label='Thumbnail'),
            ],
        ),
    ])

    class Config:
        extra = "forbid"


# ── Contact enrichment ──

class ContactEnrichment(BaseModel):
    """setting.contact_model — panels shown on contact detail pages.

    Data sources:
      - prefs.orgs[]         org links with roles
      - metadata.images      profile images
      - refs.links.*         typed relationship lists
      - stats.*              StatsMixin (transaction counts)
    """
    panels: list[EnrichmentPanel] = Field(default_factory=lambda: [
        EnrichmentPanel(
            key='organizations',
            label='Organizations',
            source='prefs.orgs',
            fields=[
                PanelField(field='org_id', label='Org'),
                PanelField(field='role', label='Role'),
                PanelField(field='is_primary', label='Primary', format='badge'),
            ],
        ),
        EnrichmentPanel(
            key='activity',
            label='Activity Summary',
            source='stats',
            fields=[
                PanelField(field='counts.tx_sale_count', label='Orders', format='number'),
                PanelField(field='values.tx_sale_total_value', label='Total Sales', format='currency'),
                PanelField(field='last.dt_last_sale', label='Last Order', format='date'),
                PanelField(field='last.dt_last_payment', label='Last Payment', format='date'),
            ],
        ),
        EnrichmentPanel(
            key='relationships',
            label='Relationships',
            source='refs.links',
            collapsed=True,
            fields=[
                PanelField(field='rep', label='Reps'),
                PanelField(field='customer', label='Customers'),
                PanelField(field='vendor', label='Vendors'),
                PanelField(field='contact', label='Contacts'),
            ],
        ),
    ])

    class Config:
        extra = "forbid"


# ── Org enrichment ──

class OrgEnrichment(BaseModel):
    """setting.org_model — panels shown on org (customer/vendor) detail pages.

    Data sources:
      - financial.customer.*   customer sales, aging, balances, margins, stats
      - financial.vendor.*     vendor purchases, aging, costs
      - financial.rep.*        rep commissions, sales
      - stats.*                StatsMixin
      - relationship_stats.*   RelationshipStatsMixin
    """
    panels: list[EnrichmentPanel] = Field(default_factory=lambda: [
        EnrichmentPanel(
            key='customer_sales',
            label='Customer Sales',
            source='financial.customer.sales',
            condition='financial.customer',
            fields=[
                PanelField(field='mtd', label='MTD', format='currency'),
                PanelField(field='ytd', label='YTD', format='currency'),
                PanelField(field='lifetime', label='Lifetime', format='currency'),
                PanelField(field='dt_last_sale', label='Last Sale', format='date'),
                PanelField(field='last_sale_amount', label='Last Amount', format='currency'),
            ],
        ),
        EnrichmentPanel(
            key='customer_aging',
            label='Aging',
            source='financial.customer.aging',
            condition='financial.customer',
            fields=[
                PanelField(field='future', label='Future', format='currency'),
                PanelField(field='period_1', label='Current', format='currency'),
                PanelField(field='period_2', label='30 Days', format='currency'),
                PanelField(field='period_3', label='60+ Days', format='currency'),
            ],
        ),
        EnrichmentPanel(
            key='customer_balances',
            label='Balances',
            source='financial.customer.balances',
            condition='financial.customer',
            fields=[
                PanelField(field='due', label='Amount Due', format='currency'),
                PanelField(field='current', label='Current', format='currency'),
                PanelField(field='open_orders', label='Open Orders', format='currency'),
                PanelField(field='total_exposure', label='Total Exposure', format='currency'),
            ],
        ),
        EnrichmentPanel(
            key='customer_credit',
            label='Credit',
            source='financial.customer.credit',
            condition='financial.customer',
            fields=[
                PanelField(field='limit', label='Credit Limit', format='currency'),
                PanelField(field='available', label='Available', format='currency'),
                PanelField(field='high', label='High Balance', format='currency'),
            ],
        ),
        EnrichmentPanel(
            key='customer_margin',
            label='Margin',
            source='financial.customer.margin',
            condition='financial.customer',
            fields=[
                PanelField(field='mtd', label='MTD', format='currency'),
                PanelField(field='ytd', label='YTD', format='currency'),
                PanelField(field='pct', label='Margin %', format='percent'),
            ],
        ),
        EnrichmentPanel(
            key='vendor_purchases',
            label='Vendor Purchases',
            source='financial.vendor.purchases',
            condition='financial.vendor',
            fields=[
                PanelField(field='mtd', label='MTD', format='currency'),
                PanelField(field='ytd', label='YTD', format='currency'),
                PanelField(field='lifetime', label='Lifetime', format='currency'),
                PanelField(field='dt_last', label='Last Purchase', format='date'),
            ],
        ),
        EnrichmentPanel(
            key='vendor_aging',
            label='Vendor Aging',
            source='financial.vendor.aging',
            condition='financial.vendor',
            fields=[
                PanelField(field='future', label='Future', format='currency'),
                PanelField(field='period_1', label='Current', format='currency'),
                PanelField(field='period_2', label='30 Days', format='currency'),
                PanelField(field='period_3', label='60+ Days', format='currency'),
            ],
        ),
        EnrichmentPanel(
            key='rep_commissions',
            label='Rep Commissions',
            source='financial.rep.commissions',
            condition='financial.rep',
            fields=[
                PanelField(field='mtd', label='MTD', format='currency'),
                PanelField(field='ytd', label='YTD', format='currency'),
                PanelField(field='lifetime', label='Lifetime', format='currency'),
                PanelField(field='pending', label='Pending', format='currency'),
                PanelField(field='rate_pct', label='Rate %', format='percent'),
            ],
        ),
    ])

    class Config:
        extra = "forbid"
