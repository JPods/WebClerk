# Community Contributions — Marketplace + Sharing
**Status:** Design concept | **Source:** Bill 2026-07-04

---

## Principle

Users contribute layouts, report templates, saved searches, QA question sets. They get credited. Others benefit. Ingrid and Athena ruthlessly cull for hidden harms. We facilitate, we don't gatekeep the conversation.

---

## Two Channels

### Internal: Contribution System (inside WC3)

Fenced area for submitting:
- databrowser layouts
- Report templates (pdfme)
- Saved searches
- QA question sets
- Email templates

Flow:
```
User submits contribution
  → Ingrid + Athena review (cull hidden harms)
    → approved → available to other users
      → Alice tracks adoption (who uses it, how often)
        → contributor earns points
```

No new model — contributions are Report/Setting records with `config.contribution`:
```json
{
  "contributor_id": 55,
  "contributor_name": "Smith Co",
  "dt_submitted": 1720100000000,
  "dt_approved": 1720200000000,
  "approved_by": "athena",
  "points": 10,
  "adoption_count": 23,
  "category": "layout"
}
```

### External: Community Forum (outside WC3)

Substack group or similar where users share:
- How they use WC3
- Best practices
- Ideas and feature requests
- Industry-specific workflows

**We are not in the middle.** Users talk to each other. We facilitate the channel but don't moderate the conversation. The community owns it.

---

## Points / Credit System

Stored on Contact.metadata:
```json
metadata.community = {
  "points": 150,
  "contributions": 12,
  "adoptions": 87,         // how many times others used their stuff
  "dt_last_contribution": 1720100000000
}
```

Points come from:
- Submitting a contribution (10 points)
- Contribution adopted by another user (+1 per adoption)
- Retrospection submitted (+5 — QA results from the field)

---

## Security — Ingrid + Athena

Every submission passes through:
1. **Ingrid** — checks for data quality, completeness, format compliance
2. **Athena** — security review: no embedded scripts with harmful intent, no data exfiltration, no SQL injection in saved search configs

Ruthless. If in doubt, reject. Users can appeal.

---

## What's NOT Built Yet

1. Submission workflow (submit → review → approve/reject)
2. Points tracking on Contact.metadata
3. Adoption counter (Alice increments when someone loads a contributed layout)
4. External community channel setup (Substack or equivalent)
5. Contribution browser in databrowser (Report records filtered by category + has contributor)

---

## Files

| File | Status | Purpose |
|------|--------|---------|
| `apps/core/models/report.py` | Exists | Stores contributed layouts, templates, searches |
| `apps/core/models/setting.py` | Exists | Stores contributed QA sets |
| `apps/core/models/contact.py` | Exists | metadata.community for points |
