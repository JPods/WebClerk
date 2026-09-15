# Training Videos — WebClerk Curriculum

> **Owner**: Alice + Bill
> **Rule**: One concept per video. 3-5 minutes each. End with "Take the quiz."
> **Status key**: pending = not recorded, published = live, planned = future

---

## Onboarding Sequence (watch in order)

| # | Video | Min | Status |
|---|-------|-----|--------|
| 1 | First Login & Navigation | 3 | pending |
| 2 | Creating Your First Customer | 4 | pending |
| 3 | Your First Order → Invoice → Payment | 5 | pending |
| 4 | Setting Up Your Company Profile | 3 | pending |

---

## Core Data

| # | Video | Min | Quiz Topic |
|---|-------|-----|-----------|
| 5 | Contacts & Communications | 4 | contact |
| 6 | Customers & Vendors (Same Contact, Different Hats) | 4 | customer |
| 7 | Items — What You Sell and Buy | 4 | item |
| 8 | Actions — Tasks, Follow-ups, Projects | 4 | action |

---

## Transactions

| # | Video | Min | Quiz Topic |
|---|-------|-----|-----------|
| 9 | Proposals & Quotes | 3 | proposal |
| 10 | Orders & Fulfillment | 4 | order |
| 11 | Invoicing & Shipping | 4 | invoice |
| 12 | Payments — Received & Disbursed | 4 | ledger |
| 13 | Purchase Orders & Receiving | 4 | purchase |
| 14 | Transaction Flow (Interactive) | 5 | transaction-flow |

---

## Inventory

| # | Video | Min | Quiz Topic |
|---|-------|-----|-----------|
| 15 | Inventory Buckets — on_hand, on_so, on_po | 4 | inventory-buckets |
| 16 | Warehouses & Bin Locations | 3 | warehouses |
| 17 | Cycle Counts & Adjustments | 4 | cycle-counts |

---

## Accounting

| # | Video | Min | Quiz Topic |
|---|-------|-----|-----------|
| 18 | GL Journal Entries — What They Are | 3 | gl-journal-concepts |
| 19 | GL Journal Export & Journal Formatter | 4 | gl-journal-export |
| 20 | Statement Sorter — Bank Import | 4 | statement-sorter |
| 21 | AR Aging & Customer Statements | 3 | ar-aging |

---

## Tools

| # | Video | Min | Quiz Topic |
|---|-------|-----|-----------|
| 22 | DataBrowser — Browse Any Model | 5 | databrowser |
| 23 | Setting Parade — How Settings Control Your UI | 4 | setting-parade |
| 24 | Reports & Print | 3 | reports |
| 25 | Documents & File Upload | 3 | documents |

---

## AI & Alice

| # | Video | Min | Quiz Topic |
|---|-------|-----|-----------|
| 26 | Meet Alice — Your AI Assistant | 3 | alice-intro |
| 27 | AI Escalation Chain | 4 | ai-escalation |
| 28 | Alice Quiz & Training | 3 | alice-quiz |

---

## Administration

| # | Video | Min | Quiz Topic |
|---|-------|-----|-----------|
| 29 | Multi-Location Setup | 5 | multi-location |
| 30 | Connections — Integrations & Sync | 4 | connections |

---

## Totals

- **30 videos**, average 3.8 minutes each
- **~115 minutes** total runtime
- **Videos 1-4**: onboarding sequence — new user watches in order
- **Videos 5-28**: topic-based — Alice recommends based on what the user is doing
- **Videos 29-30**: admin-only

## Design Rules

1. One concept per video — if it needs two, make two videos
2. Show, don't tell — screen recording with mouse, not slides
3. End each video with "Take the quiz" link
4. Keep it under 5 minutes — respect the user's time
5. Each video teaches to its quiz — the quiz tests what the video shows
6. Alice recommends videos based on what the user is struggling with
7. Videos are free — no paywall on training

## How Alice Uses This

- When a user asks about a topic, Alice links to the relevant video
- After quiz failures, Alice recommends the corresponding video
- Onboarding Actions (seed_coaching) include "Watch video #N" steps
- The training video catalog lives in `Setting(name='alice-training-videos')`

---

*Curriculum designed 2026-08-31. Bill records, Alice teaches, quizzes confirm.*
