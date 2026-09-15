# Training Videos — qq_movie_here_2026-08-12

Videos needed for WC3 deployment training. Each maps to a Document record
that ships with every installation. 1-4 minutes each. Vimeo (internal) +
YouTube (public). Document record holds both links.

**Tag:** `qq_movie_here_2026-08-12`
**Format:** Screen recording with narration. Show the user doing it, not slides.

---

## System (WC3-SYS-*)

| Priority | Document IDA | Video | Duration | Notes |
|----------|-------------|-------|----------|-------|
| 1 | WC3-SYS-ARCHITECTURE | Architecture overview — models, wcapi, React, Alice | 3 min | Big picture: what are the pieces and how do they connect |
| 2 | WC3-SYS-DEV-SETUP | Dev setup walkthrough — clone, venv, migrate, runserver, first login | 4 min | New team member watches this first |
| 3 | WC3-SYS-WCAPI-USAGE | wcapi demo — GET a contact, SAVE changes, MANAGE an action | 3 min | The API is the system; if they understand wcapi they understand WC3 |
| 4 | WC3-SYS-ONBOARDING | First-time user walkthrough — login, dashboard, create first contact, create first order | 4 min | New USER (not dev) watches this first |

## Commerce (WC3-COM-*)

| Priority | Document IDA | Video | Duration | Notes |
|----------|-------------|-------|----------|-------|
| 1 | WC3-COM-TRANSACTIONS | Transaction lifecycle — create order, add lines, convert to invoice, apply payment | 4 min | The core loop; everything else hangs off this |
| 2 | WC3-COM-INVENTORY | Inventory buckets — order allocates, invoice ships, purchase receives, available updates | 3 min | The flight simulator concept — user watches quantities change in real time |
| 3 | WC3-COM-LEDGER | GL posting — invoice creates journal, payment settles, trial balance | 3 min | Commerce people need to see the money move |
| 4 | WC3-COM-PAYMENTS | Payment application — apply to invoice, partial, overpayment | 2 min | Short and tactical — the thing they do every day |

## Operations (WC3-OPS-*)

| Priority | Document IDA | Video | Duration | Notes |
|----------|-------------|-------|----------|-------|
| 1 | WC3-OPS-DATABROWSER | databrowser tour — navigate models, resize columns, save layout, dark/light | 3 min | The daily workspace; users live in this |
| 2 | WC3-OPS-SAVED-SEARCHES | Saved searches — create, name, share, preset dropdown | 2 min | Quick win — users immediately see value |
| 3 | WC3-OPS-COACHING | Alice coaching demo — hint bar, acknowledge tip, run quiz drill | 2 min | Shows Alice is alive and helpful, not a chatbot |

## Alice (ALICE-*)

| Priority | Document IDA | Video | Duration | Notes |
|----------|-------------|-------|----------|-------|
| 1 | ALICE-PATTERN-RECOGNITION | Pattern recognition in action — Alice notices, recommends, promotes | 3 min | The observe→promote loop made visible |
| 2 | ALICE-DATA-QUALITY | Data quality tiers — watch Alice clean a messy import | 2 min | Tier 1 runs silently; show what it fixed |
| 3 | ALICE-DEDUP | Dedup walkthrough — Alice finds duplicates, user reviews bundle | 2 min | The indented list UI, copy field, remove |
| 4 | ALICE-ESCALATION | Escalation demo — Alice hits her limit, creates Action for Claude | 1 min | Short — shows honest boundary, not failure |

---

## Total: 15 videos, ~41 minutes

**Production order:** Onboarding → Transaction lifecycle → databrowser → Inventory →
Saved searches → Payments → GL posting → wcapi → Architecture → Alice coaching →
Pattern recognition → Data quality → Dedup → Dev setup → Escalation

**Why this order:** Users first, then commerce flow, then daily tools, then Alice
intelligence layer. Dev setup is late because devs can read; users need video.

---

## Document Record Integration

Each video gets stored in the Document record's `config.training_video`:

```json
{
    "qq_movie": "qq_movie_here_2026-08-12",
    "training_video": {
        "vimeo_url": "https://vimeo.com/...",
        "youtube_url": "https://youtube.com/...",
        "duration_seconds": 180,
        "dt_recorded": "2026-08-XX",
        "script_path": "readmes/training/scripts/WC3-COM-TRANSACTIONS.md"
    }
}
```

When a video is recorded, update the Document record via wcapi. Alice can serve
the video link in coaching hints and quiz drill results. The `qq_movie` tag stays
until the video exists — then it becomes the `training_video` entry.
