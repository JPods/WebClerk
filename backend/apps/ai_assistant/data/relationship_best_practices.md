# Relationship Intelligence — Best Practices for Alice

Alice's mission: "What can I do to enhance the value of relationships with
customers, vendors, employees, and reps?" This document is Alice's knowledge
base — indexed into her vector store so she can draw on it when observing
patterns and making recommendations.

---

## Core Principle

A business owns one thing of real value: relationships with its customers.
Products and services are widgets — replaceable. The relationship is what
keeps people coming back. That relationship must be nurtured, not given away
free to tech giants who harvest it to sell competing products.

---

## Customer Relationship Enhancement

### Proactive Outreach (Not Reactive Support)

The difference between great service and average service is who initiates.
Average: customer calls with a problem. Great: you call before the problem.

**What Amazon does:**
- Anticipatory shipping — predicts purchases from search/cart/wish list behavior
  and pre-positions inventory. We adapt this: predict reorder timing from order
  history and send reminders before they run out.
- Proactive delivery issue resolution — when logistics data shows a likely delay,
  auto-notifies customer with credit or alternative before they contact support.
  Reduced delivery complaints 60%.
- Product-triggered support — when a product frequently generates tickets,
  proactively sends troubleshooting guides to new buyers at delivery confirmation.
  Alice equivalent: when an item has high return rate, auto-attach care
  instructions to the order confirmation.

**What to watch and when to act:**

| Signal | Threshold | Action |
|--------|-----------|--------|
| Reorder overdue | 1.5x typical cycle | Check-in email: "Everything OK? Need to reorder?" |
| Seasonal window | Service date + seasonal offset | "Time to schedule your annual [service]" |
| Equipment end-of-life | Install date + expected lifecycle | Maintenance reminder + replacement proposal |
| Health score drops 20+ | Monthly scan | Flag to owner with recommended action |
| New product in their category | Item added matching past purchases | "We now carry X — fits what you've bought before" |
| Proposal no follow-up | 30+ days after proposal, no order | Resurface the proposal |
| High-value customer inactive | Top 20% by revenue, 90+ days silent | Personal outreach from owner/rep |

### Customer Health Scoring

Health is not data completeness. Health is relationship strength.

**Scoring formula (Alice uses):**

| Signal | Weight | How to measure |
|--------|--------|----------------|
| Order recency | 30% | Days since last order vs customer's typical cycle |
| Order trend | 20% | Spending up, flat, or declining (compare 90d windows) |
| Issue friction | 20% | Open Small-Stings, unresolved complaints |
| Data completeness | 15% | Missing email, phone, address |
| Engagement depth | 15% | Total orders, years as customer |

**Thresholds:**
- 71-100: Healthy — monitor, look for expansion opportunities
- 31-70: At Risk — intervention required within 7 days
- 0-30: Critical — owner/rep personal contact immediately

**The key insight (from Perspective AI research, 2026):** Qualitative signals
from emails and communications lead usage drops by 30-90 days. A customer who
sounds frustrated in emails but is still ordering will churn. Watch the tone
of communications, not just the transaction log.

### Customer Lifecycle Management

Every customer is in one of six stages. Alice's behavior changes by stage:

| Stage | Definition | Alice's Behavior |
|-------|-----------|-----------------|
| New | First 90 days | Onboarding — ensure first experience is excellent. 30-day check-in. |
| Growing | Order frequency/value increasing | Expand — suggest related products, volume pricing |
| Stable | Consistent pattern | Maintain — don't over-contact. Seasonal touches. |
| At Risk | Pattern breaking | Intervene — "We noticed..." personal outreach |
| Dormant | No activity 2x normal cycle | Re-engagement — special offer or "we miss you" |
| Lost | No response to re-engagement | Archive — stop spending energy, retain records |

### Reorder Pattern Detection

Alice tracks not just "customer X reorders every 30 days" but detects changes
in pattern:
- Regular customer suddenly delays → different intervention than one who
  spends less per transaction
- Seasonal customers (chimney sweep Nov→Aug cycle) need seasonal triggers
- Equipment lifecycle customers (installed product → maintenance window)
  need age-based triggers

---

## Vendor Relationship Enhancement

### Vendor Performance Scoring

Alice tracks every vendor continuously — not periodic reviews:

| Signal | What Alice Watches | Threshold |
|--------|-------------------|-----------|
| On-time delivery | PO date vs receipt date | Alert < 90% |
| Fill rate | Ordered qty vs shipped qty | Alert < 85% |
| Price stability | Cost change frequency and magnitude | Alert > 5% increase |
| Quality | Return/defect rate on their products | Alert > 3% |
| Catalog freshness | Last update to specs, images, pricing | Alert > 90 days stale |
| Response time | How fast they answer inquiries | Track and trend |

**What Alibaba does (worth learning from):**
- AI Sourcing Engine — understands buyer specs in natural language, compares
  factories, scores suppliers on delivery, quality, compliance, price variance
- Continuous supplier scorecards — real-time, not periodic reviews
- 30% improvement in supplier scoring accuracy using AI pattern detection

### WCHQ Catalog Services

Three modes for keeping vendor data current:

**Mode A — Local harvest:** Alice scrapes vendor websites, reads emailed price
sheets, parses PDFs. Normalizes what she can, flags what she can't. All data
stays local.

**Mode B — WCHQ harvest (with permission):** Local Alice sends raw vendor data
to WCHQ. DynamicCatalogs engine normalizes it — clean JSON back with
standardized fields, proper categorization, landed cost with distribution
agreement terms applied.

**Mode C — WCHQ library subscription:** WCHQ maintains catalogs for common
suppliers. Local Alice subscribes to relevant ones. Updates flow down
automatically. Local business contributes corrections upstream.

**Sovereignty rule:** Local business chooses what to share. WCHQ never sees
customer data, pricing decisions, or margins. WCHQ sees product data that
vendors already publish.

### Single Source Risk Detection

Alice flags items sourced from only one vendor:
- "You buy [product] only from [vendor]. If they have supply issues, you
  have no alternative. Consider qualifying a second source."
- Cross-reference with vendor performance — single-source risk is higher
  when the sole vendor's fill rate or delivery is declining.

---

## Employee Relationship Enhancement

### Training Progress Tracking

Alice tracks AliceCoachingLog per employee:
- Which drills completed, which skipped
- Score trends — improving or plateauing
- Skill gaps — what categories have low scores
- Time between training sessions — are they staying current?

### Productivity Patterns

Alice watches (when data is available):
- Orders processed per day/week
- Error rates (returns, credit memos caused by mistakes)
- Response time to customer inquiries
- Which employees handle which product categories best

### What to recommend:
- "Employee X hasn't completed any training drills in 60 days — schedule a
  coaching session"
- "Employee Y has high error rates on [category] orders — assign targeted
  training"
- "Employee Z is your fastest order processor but hasn't cross-trained on
  [area] — single-point-of-failure risk"

---

## Rep Relationship Enhancement

### Pipeline Health

For sales reps (rep_id on orders):
- Open proposals vs. closed — conversion rate trending
- Follow-up discipline — days between proposal and next contact
- Customer satisfaction for their accounts
- Revenue per rep trending up or down

### What to recommend:
- "Rep X has 12 open proposals older than 30 days — follow-up sweep needed"
- "Rep Y's conversion rate dropped from 40% to 25% this quarter — investigate"
- "Rep Z's customers have the highest health scores — what's their approach?
  Can other reps learn from it?"

---

## What Other Companies and AI Agents Do (Alice Should Learn From)

### Proactive AI (not chatbots)

**Parloa, Ada, Fini:** These AI agents continuously monitor customer data,
predict needs, and initiate conversations. Not "answer when asked" — "reach
out when something matters."

Example: telecom company auto-notifies users of an outage and offers solutions
before customers call.

**Fini:** Handles complete proactive phone calls — dials campaigns, verifies
right party, references account data, negotiates payment arrangements, writes
outcomes back to CRM.

### Field Service AI

**ServiceTitan:** AI dispatch optimization, equipment age tracking with
predictive maintenance flagging, intelligent scheduling by technician skill
and seasonal demand.

**Housecall Pro:** CSR AI (24/7 virtual front desk that books jobs), Analyst
AI (plain-language revenue reports), Coach AI (growth advice from company's
own data). Users save 3.2 hours/week.

**QuoteIQ:** AI-generated inspection reports with before/after photos,
NFPA-compliant documentation, auto-generated service proposals from
inspection findings.

### Supply Chain AI

**SPS Commerce (launched January 2026):** Analyzes shared order, inventory,
and POS data across its entire retail network. Cross-company AI — not just
one company's data, but network-level intelligence. This is what WCHQ can
become for WebClerk users.

**Temu's demand prediction:** Consumer behavior data feeds AI that forecasts
demand, identifies trending items, predicts emerging interests, optimizes
sourcing. Closes the loop between customer behavior and supplier coordination.

### Three-Layer Health Scoring (Perspective AI, 2026)

Most valuable finding: three layers beat one:
1. **Telemetry** — what the customer does (orders, logins, usage)
2. **Relationship** — who they interact with (which rep, which support person)
3. **Conversation** — what they actually think (sentiment from emails and calls)

Qualitative signals from calls and emails are leading indicators that precede
usage drops by 30-90 days. A customer who sounds frustrated but is still
ordering WILL churn. Telemetry-only models miss this.

Internal benchmarks: 2-4x improvement in churn prediction precision over
telemetry-only scores.

---

## Alice's Standing Questions

Alice should always be asking:

1. **For every customer:** "What can I do today to make this relationship
   more valuable — for them and for us?"
2. **For every vendor:** "Is this vendor getting better or worse? Do we have
   alternatives if they fail?"
3. **For every employee:** "Are they growing? Where are they stuck? What
   training would help most?"
4. **For every rep:** "Are they following up? Are their customers healthy?
   What's working that others can learn from?"
5. **For the business:** "What are other companies and AI agents doing that
   we should learn from? What patterns in our data suggest an opportunity
   or a risk we haven't seen?"
