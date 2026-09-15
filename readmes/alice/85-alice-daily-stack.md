# Alice Daily Stack — Sales Rep Morning Briefing

**Last updated:** 2026-08-28
**Purpose:** How Alice builds a prioritized daily action list from commerce data signals.

---

## The Principle

Alice reads the commerce data and builds the daily stack. The rep opens WC3 in the morning and sees their cards. Each card is a touch waiting to happen — click to call, click to email, click to text. When the touch is made, Alice marks it done and measures the outcome.

This is the flight simulator pattern applied to sales: Alice builds the runway, the rep flies the plane.

---

## Morning Stack for the Sales Rep

```
 "Call Customer X — last order was 45 days ago, they usually order every 30"
 "Follow up Proposal #892 — sent 7 days ago, no response, $12K value"
 "Email Vendor Y — lead time was 14 days last month, confirm current"
 "Text Customer Z — their order shipped yesterday, tracking #ABC"
 "Quote Customer W — they searched for Item Q on the site but didn't buy"
```

---

## Alice's Signals

Alice already has all the data to build this stack:

| Signal | Source | What it tells Alice |
|--------|--------|---------------------|
| **Touches** | `touches` table | When was the last contact? How long since a response? |
| **Proposals** | `proposals` table | What's pending? How old? What's the dollar value? |
| **Orders** | `orders` table | Who's overdue for a reorder? What's their usual cadence? |
| **Invoices** | `invoices` table | Who hasn't paid? How far past due? |
| **Observations** | `alice_observations` table | What patterns is Alice seeing? Margin erosion? Churn risk? |
| **Items** | `items` table | What's slow-moving? What needs promotion? |
| **Connections** | `connections` table (vendor bundles) | What are current vendor lead times? Have they changed? |

---

## How the Stack Works

1. **Alice-hc runs nightly** — scans all signals, identifies the highest-impact actions for each rep
2. **Actions created** — each stack item is an Action record on the Agent Operations project, assigned to the rep's contact
3. **Prioritized by revenue impact** — a $12K stale proposal outranks a shipping notification
4. **One click to act** — each card opens the right channel: call, email, text, quote
5. **Touch recorded automatically** — when the rep acts, a touch is created (channel, direction, outcome)
6. **Alice-lib measures** — did the call result in a reorder? Did the follow-up close the proposal? Grade A-F.
7. **Alice-hc learns** — which stack items produce results? Adjust priority weights over time.

---

## Five Commerce Goals the Stack Serves

| Goal | How the stack helps |
|------|---------------------|
| **Increase margins** | Flag customers where margins are eroding — prompt the rep to renegotiate or upsell |
| **Increase inventory turns** | Prompt reps to push slow-moving items to the right customers |
| **Reduce carrying costs** | Vendor lead time checks enable just-in-time — reduce safety stock as lead times shorten |
| **Reduce admin overhead** | Alice builds the list — the rep doesn't have to hunt for what to do next |
| **Increase customer service** | Shipping notifications, reorder reminders, and follow-ups happen on time, every time |

---

## What Alice Does NOT Do

- Write blog posts or marketing copy — that's a human or Claude escalation
- Make pricing decisions — she flags and recommends, the rep decides
- Contact customers directly — she builds the stack, the rep flies the plane
- Replace judgment — she surfaces data, humans act on it

---

## Social Media Posts

Social media posts are **Action records**, not touches. They are not directed at a specific contact — they broadcast to an audience. The flow:

1. Alice-hc spots a commerce signal worth sharing ("Item X turns jumped 300% this week")
2. Creates an Action record on the Agent Operations project
3. Claude composes the post via the Claude API Connection (rules: brand voice, frequency limits)
4. Human approves
5. Platform API publishes
6. Alice-lib measures: did the post drive traffic or sales?

Every post is backed by a transaction signal. No filler content.

---

## The Multi-Alice Vision

Each WC installation has its own Alice. Each Alice learns its own commerce patterns — what works for a plumbing supplier is different from what works for a restaurant chain. Allie coordinates across all Alices, spotting patterns that span installations. Claude handles the hard problems: catalog conversion (supplier CSV → bundle.json), ERP database migration, and complex analysis that the local 20b model can't handle.

The daily stack is Alice's most visible output — it's what the rep sees every morning. But behind it is the full three-capacity architecture: ops enforcing data quality, hc learning commerce patterns, and the librarian measuring whether the stack items actually drove results.
