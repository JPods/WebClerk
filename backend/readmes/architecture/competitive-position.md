# WC3 Competitive Position — Honest Assessment

**Created:** 2026-08-10
**Purpose:** Where WC3 stands relative to commercial ERP and commerce platforms.

---

## WC3 Is Not an ERP

WC3 is intentionally bottom-up. It focuses on four things:

1. **Selling** — proposals, orders, invoices, commissions, pricing
2. **Building** — actions, work orders, BOM, inventory, serial tracking
3. **Delivering** — shipping, fulfillment, receipts, carrier integration
4. **Collecting** — payments, terms, aging, ledger, GL journal entries

Everything else — HR, payroll, manufacturing planning, fixed assets, general
ledger maintenance, regulatory compliance packages — belongs to other programs.
WC3 produces GL journal entries. Accounting programs consume them.

This is a deliberate choice, not a gap. ERP systems try to be everything.
WC3 does four things well and connects to everything else via Bundles.

---

## WC3 vs Commercial ERP — Where It's Ahead

### Selling

| Capability | WC3 | NetSuite / SAP / Odoo |
|-----------|-----|----------------------|
| **Commission** | Per-line, level factors, split reps, partial-payment scaling, margin or revenue basis | Usually header-level, fixed rate |
| **Pricing** | Tier-based, price level per customer, DynamicCatalogs upstream | Price lists, manual maintenance |
| **Terms / due dates** | Cut-off day logic, multi-installment, early-payment discount | Usually just "Net 30" |
| **Tradeshow split** | Split order by vendor → manufacturer fulfills → commission invoice | Custom development or not available |
| **Consignment** | Status-based GL skip, simple | Complex consignment modules with separate inventory pools |
| **Proposals → Orders → Invoices** | Unified transfer engine, increment-based partial transfer, quantity tracking across the chain | Separate modules, often different data models per document type |

### Building

| Capability | WC3 | Commercial ERP |
|-----------|-----|---------------|
| **Actions** | Universal work unit — who/what/why/when/next, nested projects, kanban sprints | Separate modules for projects, tasks, tickets, service orders |
| **BOM** | Multi-level with loop detection, revision control, alternates, yield/scrap, cost propagation | Similar depth but tied to MRP modules most small businesses don't use |
| **Inventory** | FIFO/LIFO depletion walk, deferred Pending system (zero lock contention), serial tracking with embedded action history | Direct writes, lock contention at scale, serial tracking often an add-on module |
| **Reorder** | Velocity-based: lead_time × monthly_usage, auto-suggest POs grouped by vendor | Usually static min/max reorder points |

### Delivering

| Capability | WC3 | Commercial ERP |
|-----------|-----|---------------|
| **Carrier integration** | UPS, FedEx, DHL, USPS via Connection records | Similar, usually via paid connectors |
| **Freight estimation** | Weight × rate × factor with Alice calibration | Rule-based, no AI learning |
| **Receipt processing** | PO → Receipt with automatic inventory layer creation, landed cost allocation | Similar depth |

### Collecting

| Capability | WC3 | Commercial ERP |
|-----------|-----|---------------|
| **Terms** | Cut-off day, multi-installment, early-payment discount, fixed-date terms | Usually just days-offset |
| **AR aging** | Nightly paginated task, buckets in org.financial JSON | Similar, often a separate report |
| **Payments** | Signed-amount checkbook convention (positive=received, negative=disbursed), category → GL mapping | Separate AR/AP modules, more complex |
| **Partial-payment commission** | Commission scales proportionally with payment fraction | Rarely implemented |
| **Consignment** | Status-based GL skip — revenue deferred until complete | Complex consignment modules |
| **Exchange rates** | Setting-based, base currency like UTC, FX gain/loss at settlement | Separate currency modules, time-windowed rate tables |
| **GL journal output** | Three journal types (sales, purchase, cash), export to QuickBooks/CSV/JSON | Built-in GL with full chart of accounts — more than most businesses need |

---

## WC3 vs Commercial ERP — What ERP Does That WC3 Won't

| ERP Capability | Why WC3 Won't Do It |
|---------------|-------------------|
| **General ledger maintenance** | WC3 produces journal entries. The ledger belongs to the accounting program. |
| **P&L / Balance Sheet** | Accounting output, not commerce input. |
| **Bank reconciliation** | Accounting function. |
| **Payroll / HR** | Different domain entirely. |
| **Manufacturing planning (MRP)** | WC3 has BOM and work orders for assembly. Capacity planning, scheduling, and shop floor control are factory software. |
| **Fixed assets / depreciation** | Accounting function. |
| **Regulatory compliance (SOX, IFRS)** | Enterprise overhead. WC3's customers are small businesses, not public companies. |
| **Marketing automation** | WC3 tracks ad source ROI. Mass email campaigns and lead scoring belong to marketing tools. |

This isn't a roadmap — these items will never be added. WC3 connects to programs that do these things. It doesn't replace them.

---

## What Makes WC3 Genuinely Different

### 1. Sovereignty Architecture

Every commercial ERP assumes centralized control. The vendor hosts, the vendor sees the data, the vendor decides the API, the vendor raises the price.

WC3:
- **Runs on the user's machine** — their database, their rules
- **Sync by choice** — Bundles exchange data between sovereign instances; no central authority
- **CarryOn as identity** — portable, owner-controlled identity with enumerated permissions
- **Free and open source** — no vendor lock-in, no per-seat licensing, no annual price increases

NetSuite charges $999/user/month. SAP Business One starts at $3,213/user perpetual. Odoo charges $24.90/user/month for the full stack. WC3 is free. The user owns the software, the data, and the AI.

### 2. DynamicCatalogs — The Upstream Advantage

Commercial ERPs treat product data as something the user types in or imports from a spreadsheet. WC3 has DynamicCatalogs — a separate upstream service that:
- Normalizes supplier data from any format
- Applies distribution agreements (who can sell what at what margin)
- Produces retailer landed cost (supplier cost + freight + duty + handling)
- Delivers the catalog ready to sell

No commercial ERP has this. They all assume the catalog is someone else's problem.

### 3. Alice — AI That Learns the Business

Commercial ERPs are adding AI as chatbots that answer questions about the software. Alice is different:

- Persistent memory across sessions — she remembers what happened last month
- Observes transaction patterns (observe → log → pattern → recommend → promote)
- Owns data quality, billing integrity, duplicate detection, schema compliance
- Escalates to Claude when she hits her ceiling — and learns from the result
- Runs locally — the user's data never leaves their machine

Odoo's AI summarizes emails. NetSuite's AI forecasts revenue from historical data. Alice watches the business operate in real time and flags what the user hasn't noticed yet. She's a team member, not a feature.

### 4. Bottom-Up, Not Top-Down

Commercial ERPs are designed for the IT department to install, configure, and control. They enforce uniformity across the organization. They require consultants to implement.

WC3 is designed for the person doing the work. One person can install it, configure it, and start selling in a day. It doesn't require an IT department, a consultant, or a steering committee. It grows from the bottom up — one user, one business, one customer at a time.

This is the same difference between a highway system (top-down, federal, everyone uses the same road) and a JPods network (bottom-up, local, each community builds what it needs). The architecture mirrors the philosophy.

---

## The Desktop Hosting Lineage

The closest analog to WC3's architecture is the Desktop Hosting vision from Bill James's Wiley book (2002) — local-first, relationship-aware, publish-based commerce.

- **2002:** The idea was right but the technology was 4D, single-machine, no sync
- **2002–2025:** WC2 ran in production for 20+ years, proving the business model
- **2026:** Django + React + PostgreSQL + Bundles + Alice + CarryOn. Same philosophy, modern stack.

Twenty-four years of production experience distilled into a clean architecture that doesn't compromise on the original principle: **the individual is sovereign; institutions are agents with limited, enumerated, revocable permissions.**

---

## Honest Weaknesses

| Area | Reality |
|------|---------|
| **User base** | Zero production users. WC2 had 20 years of edge-case hardening. WC3 has the architecture but hasn't been beaten up by real customers yet. |
| **Documentation** | Strong for developers (readmes, CLAUDE.md). Weak for end users (no user manual, no video tutorials). |
| **Mobile** | No native mobile app. Responsive web only. |
| **Marketplace** | No plugin/app marketplace. Everything is core or custom. |
| **EDI** | Not built yet. Use a Python standards library when a customer needs it. |
| **Barcode** | Not built yet. Use python-barcode when needed. |
| **Brand recognition** | Nobody has heard of WebClerk. NetSuite has Oracle's marketing budget. |

---

## The Bottom Line

Commercial ERPs sell complexity. They charge per user, per module, per year. They require consultants to configure and IT departments to maintain. They centralize control because that's how they make money.

WC3 sells simplicity. It's free, it's local, it's sovereign. It does four things — sell, build, deliver, collect — and does them well. Everything else connects via Bundles and Connections.

The question isn't whether WC3 can do what SAP does. It can't, and it shouldn't. The question is whether a small business needs SAP, or whether it needs a tool that lets one person sell, build, deliver, collect — without asking permission from a vendor, a cloud provider, or a government.

That's the market. And nobody else is building for it.
