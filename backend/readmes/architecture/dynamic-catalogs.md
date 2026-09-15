# DynamicCatalogs

> **Reading order**: [← 01-architecture-overview](../../01-architecture-overview.md) | [data-library-ecosystem →](data-library-ecosystem.md)

---

## What DynamicCatalogs Is

DynamicCatalogs (dynamiccatalogs.com) is the data library service that sits between upstream suppliers and downstream WebClerk retailers. It is a separate program from WebClerk — WebClerk owns the retailer's customer relationships and transactions; DynamicCatalogs owns the supplier relationships and the normalization pipeline.

A retailer can switch DynamicCatalogs providers without touching WebClerk. DynamicCatalogs can serve hundreds of retailers without being coupled to any one WebClerk instance. The boundary is clean: DynamicCatalogs writes to cost and catalog models only, via scoped wcapi tokens. It has no access to contacts, transactions, or proprietary retailer data.

---

## The Core Problem DynamicCatalogs Solves

A manufacturer publishes a list price. That is not what a retailer pays.

What the retailer actually pays — their **landed cost** — is produced by applying their specific distribution agreement to the raw supplier data:

| Factor | What it means |
|--------|--------------|
| **Distributor cost** | The distributor's price to this retailer under their specific agreement |
| **Volume tiers** | 10 units vs. 100 units may carry different unit costs |
| **Freight zone** | A retailer in Montana pays different landed cost than one in New Jersey |
| **Duty and tariff rates** | Subject to change with trade policy shifts — volatile |
| **Minimum order terms** | Affects whether a SKU is viable to stock at all |
| **Quarterly rebates** | Volume rebates that reduce effective cost, paid after the fact |
| **Payment terms** | Net 30 vs. net 10 affects the effective cost of capital |

DynamicCatalogs doesn't translate format. It applies *this retailer's specific distribution agreement* with *this distributor* to produce *this retailer's actual landed cost* for every SKU.

This is the real value-add. Format translation is mechanical. Applying distribution agreements correctly, continuously, across thousands of SKUs for dozens of retailers — that is the work that requires expertise and relationship knowledge.

---

## The Distribution Agreement as Data

Because the distribution agreements themselves are the key input to normalization, DynamicCatalogs must store and maintain them:

- Which distributors serve this retailer
- The specific terms for each distributor relationship
- Freight zone assignments by retailer location
- Volume tier schedules
- Rebate structures and payment calendars
- Current duty and tariff rates by product category

**Distribution agreements decay too.** Terms get renegotiated. Freight zones shift. Tariffs change overnight. A DynamicCatalogs provider whose agreement data is stale produces inaccurate cost data — and inaccurate cost data breaks margin calculations, purchasing decisions, and retailer trust.

The librarian who maintains deep, current relationships with distributors — who knows the actual terms for each retailer they serve — is the one who produces reliable cost data. That relationship depth is the competitive moat for a DynamicCatalogs provider.

---

## The Core Loop

DynamicCatalogs operates as a continuous cycle, not a one-time integration:

```
1. INGEST     Pull raw files from manufacturers and distributors
              (whatever format they use — EDI, CSV, XML, API)

2. NORMALIZE  Translate into WebClerk's schema

3. TRANSLATE  Apply this retailer's specific distribution agreement:
              - distributor cost → landed cost
              - volume tier → unit cost at expected purchase quantity
              - freight zone → freight cost per unit
              - duty/tariff rates → duty cost per unit
              - minimum order terms → viability flag
              - payment terms → effective cost of capital adjustment

4. PUSH       POST to /wcapi/save/ for each retailer
              subscribed to this supplier/distributor

5. LISTEN     Receive complication flags from WebClerk instances
              (price mismatch, discontinued SKU, wrong unit of measure,
               missing product, wrong specification)

6. CORRECT    Investigate, update source data or agreement terms,
              propagate correction to all affected subscribers

7. REPEAT     Data decay is continuous; the cycle never ends
```

The data decay rate sets the cadence. Some suppliers update weekly, some quarterly, some whenever a tariff shifts. DynamicCatalogs must track update frequency by supplier and push corrections proactively — not wait for retailers to report complications.

---

## Normalization in Detail

Raw supplier data is messy by default:

- Multiple price lists for the same product (regional distributors, inconsistent)
- SKU naming conventions that differ between manufacturer and distributor
- Unit-of-measure ambiguity (case vs. each vs. pallet)
- Missing specifications
- Discontinued products still appearing in active price files
- Overlapping distributor territories

Normalization resolves all of this into a consistent WebClerk schema. The process also forces **retrospection** on the supplier side: a manufacturer who has maintained three inconsistent price lists for the same product across three regional distributors must resolve them when DynamicCatalogs tries to normalize across all three. Inconsistencies that were hidden in sales rep relationships become structurally visible.

This is usufruct applied to data quality: DynamicCatalogs processes data it does not own, returns it in better condition, and the improved baseline benefits every retailer in the network.

---

## Competitive Structure

Multiple DynamicCatalogs providers can serve the same WebClerk ecosystem. A hardware retailer might use one provider for fastener pricing and another for power tool pricing. No provider has a monopoly on any retailer's data.

Providers compete on:

- **Category depth** — which manufacturers and distributors they have agreements with
- **Agreement accuracy** — how current and correct their distribution agreement data is
- **Freshness** — how quickly they process new supplier files
- **Correction speed** — how fast they resolve reported complications
- **Geographic specialization** — freight zone expertise in specific regions
- **Vertical specialization** — deep knowledge of specific product categories

A DynamicCatalogs provider that extracts rather than serves loses retailers. One that serves well attracts them. The market enforces this continuously.

---

## The Usufruct Governing Rule

DynamicCatalogs processes data it does not own:

- The manufacturer's price list belongs to the manufacturer
- The distributor's terms belong to the distributor and retailer
- The retailer's cost calculation belongs to the retailer
- DynamicCatalogs's value is in the processing and the relationship depth, not in the data itself

**DynamicCatalogs may profit from processing the data. It may not retain, aggregate, resell, or weaponize it.**

Specifically, a DynamicCatalogs provider:

- May not sell aggregate retailer purchasing data upstream to manufacturers or distributors
- May not use one retailer's pricing to inform recommendations to a competitor retailer
- May not build profiles of retailer purchasing behavior for third-party commercial use
- Must return data to the retailer in like or better condition — normalized, translated, current

---

## Relationship to WebClerk

```
Manufacturers / Distributors
         │
         │  raw price files, catalogs
         │  distribution agreements
         ▼
[ DynamicCatalogs ]  ←── complications reported by retailers
         │
         │  normalized, retailer-specific landed cost
         │  pushed via scoped wcapi token
         ▼
[ Retailer WebClerk ]
         │
         │  transactions, contacts, orders
         ▼
[ Customers / Suppliers ]
```

DynamicCatalogs has write access only to cost and catalog models in WebClerk — scoped, auditable, revocable. The retailer owns their contacts, transactions, customer relationships, and pricing history. DynamicCatalogs never touches those.

---

## Why This Is a Separate Program

WebClerk is designed for bottom-up local commerce — each instance locally governed, each retailer owning their own data. DynamicCatalogs operates upstream of that: it aggregates supplier relationships across many retailers to make normalization economically viable.

These are different problems requiring different architectures. Keeping them separate means:

- A retailer can switch DynamicCatalogs providers without data migration
- A DynamicCatalogs provider can improve its normalization pipeline without waiting for WebClerk releases
- The open wcapi standard means any DynamicCatalogs provider can serve any WebClerk instance
- Competition between providers is structurally enforced — no single provider can lock in a retailer

This separation is the same structural principle as the Divided Sovereignty framework: enumerated permissions, explicit scope, revocable access, value through service not extraction.

---

*See [data-library-ecosystem.md](data-library-ecosystem.md) for the full ecosystem context.*
*See [allie-webclerk-integration.md](allie-webclerk-integration.md) for how Allie accesses WebClerk under the same scoped-access model.*
