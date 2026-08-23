# Campaign-Reseller Collaboration — Manufacturer ROI at the Last Mile

**Established:** 2026-07-25

---

## The Problem

Manufacturers spend on TV, social media, and digital advertising. They measure reach and impressions. They cannot measure what actually sold at the reseller level. The reseller sees walk-in traffic increase but can't attribute it to a specific campaign. Both sides guess.

---

## The Solution

WC3 Connection/Bundle sync ties manufacturer campaigns to reseller orders. The campaign record at the manufacturer links to order records at the reseller. Both see the same signal from different ends.

### What the Manufacturer Sees

> "I spent $50K on the Austin TV campaign. 12 resellers in the Austin area reported 340 orders with this campaign source tag in the 30 days after. Cost per acquisition: $147. ROI: 3.2x."

That's real ROI — not estimated reach, not impression counts, not click-through rates. Actual orders at actual resellers.

### What the Reseller Sees

> "The manufacturer ran an ad campaign. My walk-in traffic went up 15%. These 28 orders came from customers who mentioned the ad or used the promo code. This is my evidence for requesting co-op advertising dollars."

The reseller doesn't need to build a tracking system. WC3 tags the order with the campaign source. Alice correlates the timing.

---

## How It Works

```
Manufacturer                          Reseller
    │                                     │
    ├── Creates Campaign record           │
    │   (budget, channel, dates,          │
    │    geographic target)               │
    │                                     │
    ├── Syncs campaign via                │
    │   Connection/Bundle ──────────────► Receives campaign record
    │                                     │
    │                                     ├── Customer walks in
    │                                     ├── Order created
    │                                     │   source = campaign tag
    │                                     │
    │                                     ├── Alice correlates:
    │                                     │   order timing vs campaign dates
    │                                     │   customer zip vs campaign geo
    │                                     │
    │   ◄────────────────────────────────── Syncs order summary back
    │   (count, value, dates,             │   via Connection/Bundle
    │    no customer PII)                 │
    │                                     │
    ├── Alice aggregates across           │
    │   all resellers in campaign geo     │
    │                                     │
    ├── Campaign ROI calculated           │
    │   (real orders, not estimates)      │
    │                                     │
    └── Evidence for next campaign        └── Evidence for co-op dollars
```

---

## The DynamicCatalogs Pattern

This is the same data supply chain that moves product data — running in both directions:

| Direction | What flows | Purpose |
|-----------|-----------|---------|
| **Down** (manufacturer → reseller) | Product data, pricing, campaigns | Supply the reseller |
| **Up** (reseller → manufacturer) | Order summaries, campaign attribution | Signal back to the manufacturer |

The campaign is just another data type in the same pipe. No new infrastructure. The Connection/Bundle sync that already moves product data and pricing now also moves campaign records down and sales signal up.

---

## Alice on Both Sides

**At the manufacturer:** Alice aggregates campaign attribution across all resellers in the target geography. She calculates cost per acquisition, ROI, and identifies which resellers responded strongest.

**At the reseller:** Alice correlates order timing with campaign dates, customer zip codes with campaign geography. She tags orders automatically when the correlation is strong. She flags orders that might be campaign-driven but weren't tagged.

**n²** — the value is in the number of connections between the manufacturer's campaign and every reseller's register. One manufacturer, 50 resellers, one campaign = 50 data points. That's a signal no single reseller could produce alone.

---

## Privacy

The reseller syncs **order summaries**, not customer records:
- Order count, total value, date range
- Campaign source tag
- Geographic aggregate (city/zip level)
- No customer names, emails, phones, or addresses

The customer's data stays sovereign at the reseller. The manufacturer sees the signal, not the identity.

---

## WC3 Models Involved

| Model | Role |
|-------|------|
| Campaign | Manufacturer's ad campaign (budget, channel, dates, geo) |
| Connection | Sync link between manufacturer and reseller |
| Bundle | Data package sent in each sync (campaign down, orders up) |
| Order | Reseller's order with `source` campaign tag |
| Action | Alice's correlation observations and coaching |
| Report | Campaign ROI report, co-op evidence report |

---

## Relates To

- `readmes/topics/architecture/dynamic-catalogs.md` — the data supply chain pattern
- `readmes/topics/architecture/dual-hosting-model.md` — local-first sovereignty
- `readmes/21-sync-integration.md` — Connection/Bundle sync model
- Campaign ROI service: `apps/transactions/services/campaign_roi.py`
