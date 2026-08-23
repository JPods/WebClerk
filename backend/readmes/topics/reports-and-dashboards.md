# Reports & Dashboards — WC3 Standard Library

**Established:** 2026-07-25
**Applies to:** All WC3 installations

---

## Report Model

Reports are records in the `reports` table. Each has:
- `name` — display name
- `model_name` — which model it applies to (contact, order, invoice, etc.)
- `category` — customer_facing, vendor_facing, warehouse, report, accounting, sales_analysis, tool, export
- `output_type` — print, email, action, export, label, merge
- `config` — JSON with template reference, action handler, parameters
- `description` — what the report does

Reports appear in the Reports dialog when the user clicks the Reports button on a model's databrowser or detail page.

---

## Big5 Transaction Reports

### Orders (8 reports)
| Report | Category | Output | Purpose |
|--------|----------|--------|---------|
| Sales Order — Standard | customer_facing | print | Line items, pricing, delivery terms, signature |
| Sales Order — Summary | report | print | Management view — count, value, status |
| Packing Slip | warehouse | print | Package contents, weights, labels |
| Pick List | warehouse | print | Warehouse picking with bin locations |
| Order Acknowledgment | customer_facing | email | Customer confirmation |
| Delivery Note | warehouse | print | Shipping document for carrier |
| Open Orders Report | report | print | All open orders by customer, age, value |
| Backorder Report | report | print | Items ordered but not fulfilled |

### Proposals (5 reports)
| Report | Category | Output | Purpose |
|--------|----------|--------|---------|
| Proposal/Quote — Standard | customer_facing | print | Accept/Use columns, validity, signature |
| Proposal — Summary | report | print | Open proposals by value, expiry |
| Proposal as Proforma Invoice | customer_facing | print | International/prepay format |
| Quote Follow-up List | report | print | Aging quotes needing follow-up |
| Quote Conversion Report | report | print | Win/loss analysis |

### Invoices (9 reports)
| Report | Category | Output | Purpose |
|--------|----------|--------|---------|
| Invoice — Standard | customer_facing | print | Line items, tax, totals, payment terms |
| Invoice — Service | customer_facing | print | Labor hours, rates, project reference |
| Invoice — Shipping | customer_facing | print | With tracking, carrier info |
| Credit Memo | customer_facing | print | Return/adjustment credit |
| Statement of Account | customer_facing | print | Multi-invoice with aging |
| AR Aging Report | accounting | print | Receivables by age bucket |
| Sales by Customer | sales_analysis | print | Revenue by customer for period |
| Sales by Rep | sales_analysis | print | Revenue by rep for period |
| Tax Report | accounting | print | Tax collected by jurisdiction |

### Purchases (7 reports)
| Report | Category | Output | Purpose |
|--------|----------|--------|---------|
| Purchase Order — Standard | vendor_facing | print | Quantities, prices, delivery terms |
| Purchase Order — Summary | report | print | Open POs by vendor, value |
| Receiving Report (GRN) | warehouse | print | Arrived vs ordered |
| PO vs Receipt Variance | report | print | Quantity/price variance |
| AP Aging Report | accounting | print | Payables by age bucket |
| Vendor Scorecard | report | print | Delivery, quality, price, lead time |
| RFQ (Request for Quote) | vendor_facing | print | Pre-PO supplier request |

### Payments (6 reports)
| Report | Category | Output | Purpose |
|--------|----------|--------|---------|
| Payment Receipt | customer_facing | print | Proof of payment with applied invoices |
| Payment Summary | report | print | By period, method, status |
| Bank Reconciliation | accounting | print | Payment vs bank matching |
| Commission Report | report | print | Commissions by rep, line-item detail |
| Refund Report | report | print | Refunds by period, reason |
| Cash Flow Report | accounting | print | Cash in/out with forecast |

---

## Dashboard Specifications

Each dashboard is a JSON structure that can be:
1. Rendered on-screen in the WC3 React app
2. Sent as JSON via the sync app to external systems
3. Printed as a PDF summary

### Dashboard JSON Structure
```json
{
  "dashboard": {
    "type": "sales",
    "timestamp": "2026-07-25T14:30:00Z",
    "metrics": [
      {
        "id": "revenue_this_month",
        "label": "Monthly Revenue",
        "value": 250000,
        "unit": "USD",
        "target": 300000,
        "variance_pct": -16.7,
        "refresh": "daily"
      }
    ],
    "charts": [
      {
        "id": "pipeline_funnel",
        "type": "funnel",
        "title": "Pipeline by Stage",
        "data": [{"stage": "Lead", "value": 500000}],
        "refresh": "daily"
      }
    ],
    "alerts": [
      {
        "severity": "high",
        "message": "3 invoices overdue >60 days",
        "action_url": "/db/invoice?filter=overdue"
      }
    ]
  }
}
```

### 1. Sales Dashboard
**Audience:** Sales manager

| KPI | Refresh |
|-----|---------|
| Monthly revenue vs quota | Daily |
| Pipeline value by stage | Real-time |
| Conversion rate (quote → order) | Daily |
| Win/loss count and ratio | Daily |
| Average deal size | Weekly |
| Sales cycle length (days) | Weekly |
| Top 5 deals at risk | Real-time |
| Rep quota attainment | Daily |

**Charts:** Pipeline funnel, revenue trend line, win/loss pie, activity heatmap
**Alerts:** Deals stalled >30 days, rep below quota, large deal at risk

### 2. Accounting Dashboard
**Audience:** Bookkeeper / controller

| KPI | Refresh |
|-----|---------|
| Cash balance + 7-day forecast | Daily |
| Days Sales Outstanding (DSO) | Daily |
| AR aging (current, 30, 60, 90+) | Daily |
| AP aging (current, 30, 60, 90+) | Daily |
| Cash conversion cycle | Weekly |
| Collection rate % | Weekly |
| Month-end close status | Daily |

**Charts:** Cash flow waterfall, aging table, GL distribution, YTD vs budget
**Alerts:** Invoices >60 days overdue, payments due within 7 days, low cash

### 3. Inventory Control Dashboard
**Audience:** Warehouse manager

| KPI | Refresh |
|-----|---------|
| Total inventory value | Real-time |
| Turnover ratio | Daily |
| Stockout incidents | Real-time |
| Fill rate % | Daily |
| Days on hand (avg) | Daily |
| Reorder alerts | Real-time |
| Dead stock (no movement 6mo+) | Weekly |

**Charts:** Stock by warehouse, turnover by category, ABC Pareto, reorder alerts
**Alerts:** Low stock, overstock, stockouts, shelf-life expiration

### 4. Purchasing Dashboard
**Audience:** Purchasing agent

| KPI | Refresh |
|-----|---------|
| Open PO value | Real-time |
| PO cycle time (days) | Weekly |
| Supplier on-time delivery % | Weekly |
| Cost savings realized | Monthly |
| Contract compliance % | Weekly |
| Price variance vs contract | Daily |

**Charts:** Spend by supplier, PO status pipeline, supplier scorecard, cost trend
**Alerts:** PO not received, quality alert, price increase, contract expiring

### 5. Rep Management Dashboard
**Audience:** Sales director

| KPI | Refresh |
|-----|---------|
| Quota attainment by rep | Daily |
| Revenue per rep | Daily |
| Pipeline per rep | Real-time |
| Win rate by rep | Weekly |
| Activity compliance % | Daily |
| Reps below 50% quota | Daily |

**Charts:** Leaderboard, quota gauge per rep, pipeline stacked bar, activity scatter
**Alerts:** Rep below quota, low activity, large deal stalled, onboarding lagging

### 6. Manufacturer/Vendor Management Dashboard
**Audience:** Distributor

| KPI | Refresh |
|-----|---------|
| On-time delivery % by vendor | Weekly |
| Quality/defect rate by vendor | Weekly |
| Cost per unit trend | Monthly |
| Rebate/credit earned | Monthly |
| Vendor rating (composite) | Weekly |
| Revenue dependency % | Monthly |

**Charts:** Vendor scorecard heatmap, delivery gauge, cost trend, spend concentration
**Alerts:** Delivery <85%, quality declining, sole-source risk, contract expiring

### 7. Admin Dashboard
**Audience:** System administrator

| KPI | Refresh |
|-----|---------|
| Active users | Real-time |
| System response time | Real-time |
| Database size + growth | Daily |
| Backup status | Daily |
| API error rate | Real-time |
| Failed login attempts | Real-time |
| Alice task status | Real-time |
| Sync lag to external systems | Hourly |

**Charts:** Uptime timeline, response time trend, resource gauges, user heatmap
**Alerts:** Uptime <99%, disk <10%, backup failed, API errors spiking

---

## Print Template System

Two template engines available:

### 1. PrintDocumentLayout (.tsx)
React components at `src/apps/transactions/components/print/`
- `PrintDocumentLayout.tsx` — base layout (US Letter 8.5" x 11")
- `ProposalPrintDocument.tsx`, `OrderPrintDocument.tsx`, `InvoicePrintDocument.tsx`, `PurchasePrintDocument.tsx`
- Uses Tailwind CSS, `@media print` rules
- Developers customize by editing .tsx

### 2. pdfme (JSON templates)
Template-based PDF generation at `src/services/pdfme/`
- `generateCommercePdf.ts` — supports all transaction types
- `templateService.ts` — load/save templates from Report model config
- `fieldRegistry.ts` — maps WC3 fields to template placeholders
- Starter templates in `starter-templates/`
- Users customize via WYSIWYG designer (no code)

### Existing PDF Examples
- `wc3_form_examples/invoices/` — CMA Invoice, Dow Jones Invoice, Lease Invoice
- `wc3_form_examples/proposal/` — Paper proposal with Accept/Use columns
- `readmes/flowcharts/` — Order-to-Invoice workflow, Payment-GL workflow

---

## Alice's Role

Alice should:
1. **Know** the standard reports per model and suggest missing ones
2. **Generate** report records with correct model_name, category, output_type
3. **Help users** customize templates (pdfme JSON or .tsx guidance)
4. **Track usage** and auto-promote popular reports to quick-access
5. **Send dashboards** as JSON via sync app to external systems
6. **Create** visit checklists from QA Document records (paper, phone, on-screen)

The report is the last mile of data. If the user can't print it, email it, or hand it to someone, the data has no value outside the system.
