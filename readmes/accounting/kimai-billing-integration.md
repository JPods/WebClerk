# Kimai Billing Integration — Invoice Bundles, Not Split AR

**Date:** 2026-09-08
**Decision:** Kimai exports billing bundles to WebClerk. WebClerk creates invoices and collects. Never split receivable collection across two systems.

---

## The Two Options

### Option 1: Kimai bills directly (REJECTED)
Kimai generates invoices and sends them to customers. WebClerk also sends invoices for product sales. The customer receives invoices from two systems.

**Why this fails:**
- AR is split — the sales rep doesn't see the full picture
- Alice can't track customer health accurately (she only sees half the revenue)
- Collections coaching breaks — Alice doesn't know about Kimai invoices
- Customer statements are incomplete
- GL journals come from two sources — the accountant reconciles two streams
- Health scoring is wrong — a customer paying Kimai but not WC3 looks healthier than they are

This is a controlling-function problem infecting the empowering function.

### Option 2: Kimai exports billing bundles to WebClerk (ACCEPTED)
Kimai tracks hours, calculates billable amounts, and exports a billing bundle. WebClerk creates the invoice, sends it, collects payment, ages it, and journals it.

**Why this works:**
- Customer sees one invoice, one statement, one relationship
- Alice sees all revenue — product sales AND time billing — in one place
- Collections dashboard is complete
- Health scoring works (all AR visible)
- GL journals are unified through one AccountingAdapter
- The accountant gets one clean set of journals

---

## The Flow

```
Kimai (controlling)                    WebClerk (empowering)
┌─────────────────────┐                ┌─────────────────────────┐
│ Track hours         │                │                         │
│ Calculate rates     │                │                         │
│ Project/member/org  │   Billing      │ Create invoice          │
│ billable rates      │── Bundle ────→ │ Send to customer        │
│ Utilization reports │                │ Collect payment         │
│ Profitability       │                │ Age receivable          │
│                     │                │ Journal to GL           │
└─────────────────────┘                │ Alice watches pattern   │
                                       └─────────────────────────┘
```

## Billing Bundle Format

```json
{
  "type": "time_billing",
  "version": "1.0",
  "source": "kimai",
  "period": "2026-09",
  "customer": {
    "kimai_id": 42,
    "email": "lacey@abcmotors.com",
    "name": "ABC Motors"
  },
  "project": {
    "kimai_id": 7,
    "name": "Fleet maintenance consulting",
    "wc_project_id": 1234
  },
  "lines": [
    {
      "date": "2026-09-05",
      "activity": "On-site inspection",
      "hours": 4.5,
      "rate": 150.00,
      "amount": 675.00,
      "worker": "Bill James",
      "note": "Quarterly brake system audit"
    }
  ],
  "totals": {
    "hours": 4.5,
    "amount": 675.00
  }
}
```

WebClerk receives this bundle via the TimeAdapter, matches the customer by email, creates an invoice with service lines, and proceeds through the normal billing cycle.

## The Principle

Same as accounting: each system does what it's good at.

| System | Does | Does NOT |
|--------|------|----------|
| **Kimai** | Track time, calculate rates, measure utilization | Send invoices, collect payments, age AR |
| **WebClerk** | Invoice, collect, age, journal, coach | Track hours, manage timesheets |
| **Accounting** | Financial statements, AP, bank rec | Any of the above |

One customer. One invoice. One collection process. One Alice watching the whole picture.
