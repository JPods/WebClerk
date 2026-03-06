# Improving AI Task Results — User Guide

> How your data practices directly affect the quality of Phase 5 AI Intelligence outputs.

---

## Overview

The Phase 5 AI tasks (health scoring, schema drift, data cleanup, margin analysis, etc.) run against your live data. **The better your data, the better the AI results.** This guide explains what each task looks for, what signals weak data, and concrete steps you can take to improve outcomes.

---

## Quick Reference

| Task | What It Measures | You Control |
|------|-----------------|-------------|
| **Health Scoring** | Record completeness (0–100) | Fill fields, add keywords, keep refs current |
| **Schema Drift** | Django ↔ TypeScript alignment | Keep TS interfaces up to date after model changes |
| **Data Cleanup** | Address/phone normalization | Enter data in standard formats from the start |
| **JSON Optimization** | `.refs` / `.prefs` / `.metadata` envelope quality | Remove stale keywords, unused links, dead flags |
| **Margin Tracking** | Price/cost accuracy | Maintain accurate cost and pricing data |
| **Inventory Velocity** | Stock turnover efficiency | Keep quantity-on-hand and usage records current |
| **Sync Advisor** | Conflict resolution quality | Avoid editing same records in wc2 and wc3 simultaneously |

---

## 1. Health Scoring (5E)

### What the AI does
Examines every record and assigns a `health_rating` from 0 to 100 based on field completeness, keyword coverage, relationship connections, and data recency.

### Scoring breakdown by model

**Contacts / Customers / Vendors:**
- First name populated → +15
- Last name populated → +15
- Email populated → +15
- Has at least 1 keyword → +10
- Has linked address → +15
- Has linked orders (within 365 days) → +15
- Record updated within 90 days → +15

**Items:**
- Description populated → +20
- Has at least 1 keyword → +10
- Has price data → +15
- Has cost data → +15
- Has vendor assignment → +15
- Has brand/category → +10
- Has image reference → +15

### How to improve scores

1. **Fill required contact info.** Every contact should have at minimum: first name, last name, and email. A contact missing all three starts at 0.

2. **Add keywords.** The `refs.keywords` array directly contributes to health. At least one keyword per record ensures +10. Good keywords also improve search relevance.
   ```
   Example: A vendor record with keywords ["electrical", "wholesale", "west-coast"]
   scores higher than one with an empty keywords array.
   ```

3. **Link addresses.** Contacts without linked addresses lose 15 points. Use the address form to associate at least a primary billing or shipping address.

4. **Touch stale records.** Records not updated in 90+ days lose their recency bonus. If a vendor is still active, even a minor edit refreshes the timestamp.

5. **Create relationships.** Orders, invoices, line items — records that connect to other records score higher. Orphan records (no linked transactions) always score lower.

### LLM enhancement
When `--llm` is enabled, a sample of records get a 0–15 bonus if the LLM determines the text content is high quality (readable descriptions, clean notes). To benefit:
- Write clear, grammatically readable descriptions
- Avoid pasting raw HTML or encoded strings into description fields
- Use the notes field for structured information, not data dumps

---

## 2. Schema Drift Detection (5D)

### What the AI does
Compares Django model fields against TypeScript interfaces and Zod schemas in React2025. Flags fields present in one but not the other, type mismatches, and required/optional misalignment.

### How to improve results

1. **After changing a Django model, update the TS interface.** The most common drift items are fields added to Django but never reflected in the frontend types.
   - Django `CharField` → TypeScript `string`
   - Django `IntegerField` → TypeScript `number`
   - Django `BooleanField` → TypeScript `boolean`
   - Django `DateTimeField` → TypeScript `string` (ISO format)
   - Django `JSONField` → TypeScript `Record<string, unknown>` or typed interface

2. **Match nullability.** If a Django field has `null=True`, the TS type should be `string | null`, not just `string`.

3. **Keep Zod schemas in sync.** If you use `.optional()` in Zod, the Django field should have `blank=True` or `null=True`. Mismatches here cause runtime validation surprises.

4. **Remove deprecated fields from both sides.** A field removed from Django but still in a TS interface creates a "missing_in_django" alert.

### When to run
Run `python manage.py ai_intelligence --task drift` after any migration or after merging a branch that changes models.

---

## 3. Data Cleanup (5C)

### What the AI does
Normalizes addresses (via USPS-style parsing) and phone numbers (via E.164 formatting). Identifies parseable-but-dirty inputs and suggests corrections.

### How to improve results

1. **Enter addresses in standard format.**
   ```
   Good:  123 Main St, Suite 200, Portland, OR 97201
   Bad:   123 main street suite two hundred portland oregon
   ```
   The parser can handle the second form, but accuracy drops. The cleaner the input, the higher the confidence score.

2. **Use standard phone formats.**
   ```
   Good:  (503) 555-1234       →  +15035551234
   Good:  503-555-1234         →  +15035551234
   Bad:   five oh three 555 1234
   ```

3. **Include country codes for international numbers.** Without a country code, the parser assumes US (+1). European/Asian numbers without codes may parse incorrectly.

4. **Avoid free-text in structured fields.** Don't put notes or instructions in address line 1 (e.g., "talk to Bob at loading dock — 123 Main St"). The parser will try to extract the address but may grab wrong components.

5. **Split multi-line addresses properly.** Use the address_2 field for suite/unit/floor rather than cramming everything into address_1.

### LLM fallback
When the deterministic parser's confidence is below 50%, the LLM attempts interpretation. To help the LLM:
- Include zip codes (strongest address signal)
- Include state abbreviations
- Separate city from state with a comma

---

## 4. JSON Envelope Optimization (5B)

### What the AI does
Audits the `.refs`, `.prefs`, and `.metadata` JSON envelopes on every record. Finds duplicate keywords, empty arrays, orphaned links, unknown preference keys, stale history flags, and oversized fields.

### Common issues and fixes

| Issue | What It Means | Fix |
|-------|---------------|-----|
| `duplicate_keywords` | Same keyword appears twice in `refs.keywords` | Remove duplicate via admin or API |
| `empty_keywords` | Keywords array is `[]` | Add at least one relevant keyword |
| `orphaned_links` | `refs.links` points to records that no longer exist | Remove dead links |
| `null_entries` | `null` values inside a JSON object | Replace with proper values or remove key |
| `unknown_prefs_keys` | Keys in `.prefs` not in the active schema | Remove deprecated pref keys |
| `stale_flags` | Metadata flags older than retention window | Clear old status flags |
| `oversized_field` | JSON blob exceeds 50KB | Reduce content, move large data to files |

### How to improve results

1. **Maintain keyword hygiene.** When adding keywords via the UI, check for duplicates first. Autocomplete helps but doesn't prevent manual duplication.

2. **Clean up after feature removals.** When a feature is deprecated, its `.prefs` keys may linger. Run `--task optimize --report` to find these.

3. **Don't use metadata as a database.** The `.metadata` JSON envelope is for flags and small config, not for storing large datasets. Anything over 10KB should be in a dedicated field or related model.

4. **Review orphaned links quarterly.** Deleted records leave behind link references. The optimizer identifies these — running with `--apply` removes them.

---

## 5. Margin Tracking (5F)

### What the AI does
Calculates `(price - cost) / price * 100` for every item with pricing data. Flags anomalies (negative margins, margins over 90%, missing cost data).

### How to improve results

1. **Enter accurate costs.** Every item should have a `cost` value in its pricing JSON. Items without cost data are flagged as anomalies and excluded from the average margin calculation.

2. **Update costs regularly.** If vendor pricing changes quarterly, update item costs accordingly. Stale costs produce misleading margin numbers.

3. **Use consistent price tiers.** The tracker uses `base_price` (the default/retail price). If you have tiered pricing, ensure the base tier is always populated.

4. **Flag items correctly.** Discontinued items with outdated pricing skew the margin report. Mark them inactive so they're filtered from active analysis.

### LLM enhancement
With `--llm`, the system generates narrative analysis: "Your highest-margin category is Electrical (avg 42%) but 12 items have negative margins suggesting stale cost data." To get useful narratives:
- Use clear, descriptive item names
- Assign items to categories/brands consistently
- Keep cost sources documented in notes

---

## 6. Inventory Velocity (5G)

### What the AI does
Measures capital efficiency: how fast inventory turns into revenue. Calculates days-of-supply, margin-per-day, and carrying cost. Classifies items as healthy, slow-movers, or dead stock.

### Classifications

| Status | Days of Supply | Action |
|--------|---------------|--------|
| **Healthy** | < 90 days | No action needed |
| **Slow mover** | 90–365 days | Consider markdowns or promotions |
| **Dead stock** | > 365 days | Liquidate, return to vendor, or write off |

### How to improve results

1. **Keep quantity-on-hand accurate.** Velocity calculations depend on current inventory levels. If physical counts differ from system records, velocity metrics are unreliable. Do cycle counts.

2. **Record all transactions.** Every sale, return, and adjustment should flow through the system. Missing transactions make items appear slower-moving than they are.

3. **Update reorder points.** Items with wildly high reorder points relative to actual sales create artificially high carrying costs in the analysis.

4. **Track vendor lead times.** The velocity calculation is more useful when the system knows how long replenishment takes. Include lead time data in vendor/item relationships.

5. **Review dead stock alerts.** When the system flags dead stock, investigate:
   - Is the item actually in stock, or is the count wrong?
   - Was there a data entry error in the last sale date?
   - Should the item be marked discontinued?

---

## 7. Sync Conflict Advisor (5A)

### What the AI does
When the same record is modified in both wc2 (4D) and wc3 (Django), the advisor examines both versions and recommends which to keep. Prefers deterministic rules (newer version wins, non-empty overwrites empty) before asking the LLM.

### How to improve results

1. **Avoid dual editing.** The single best thing you can do: don't edit the same record in both systems within the same sync window. Pick one system as the source of truth for each record type.

2. **Use timestamps.** Record modifications with timestamps let the advisor apply "newest wins" logic. If timestamps are missing, it falls back to human review.

3. **Adopt single-system workflows.** Where possible, transition record types to one system:
   - New orders → wc3 only
   - Legacy customer edits → wc2 only until migration
   - Inventory adjustments → one system, then sync

4. **Resolve conflicts promptly.** Records flagged for human review should be resolved within 24 hours. Stale conflicts compound when the underlying record changes again.

---

## Running the Tasks

### Quick commands

```bash
# See what's wrong (report mode, no changes)
python manage.py ai_intelligence --report

# Run just health scoring with LLM bonus
python manage.py ai_intelligence --task health --llm --report

# Fix JSON envelopes (applies changes)
python manage.py ai_intelligence --task optimize --apply

# Full run, all tasks, with LLM, 1000 records per model
python manage.py ai_intelligence --llm --limit 1000 --report

# Check schema drift after a migration
python manage.py ai_intelligence --task drift --report

# Focus on a single model
python manage.py ai_intelligence --task health --model item --report
```

### Recommended schedule

| Task | Frequency | Best With LLM? |
|------|-----------|-----------------|
| Health Scoring | Weekly | Optional (slower but richer) |
| Schema Drift | After migrations | No (deterministic) |
| Data Cleanup | Daily | Optional (fallback only) |
| JSON Optimization | Monthly | No (deterministic) |
| Margin Tracking | Weekly | Yes (narrative useful) |
| Inventory Velocity | Weekly | Yes (narrative useful) |
| Sync Advisor | Per sync cycle | Yes (conflict reasoning) |

### Celery beat automation

The tasks are also available as Celery tasks for automated scheduling:

```python
# In your celery beat configuration:
from django_celery_beat.models import PeriodicTask, IntervalSchedule

# Run health scoring every Sunday at 2am
schedule, _ = IntervalSchedule.objects.get_or_create(every=7, period="days")
PeriodicTask.objects.create(
    name="Weekly Health Scoring",
    task="apps.ai_assistant.tasks.health_scoring_task",
    interval=schedule,
    kwargs='{"limit": 500, "use_llm": false}'
)
```

---

## Data Quality Checklist

Use this checklist to audit your data practices. Each item directly impacts one or more AI tasks.

- [ ] All contacts have first name, last name, and email
- [ ] Items have descriptions, at least one keyword, price, and cost
- [ ] Addresses use standard US formatting (street, city, state, zip)
- [ ] Phone numbers include area codes
- [ ] Quantity-on-hand matches physical inventory (within 5%)
- [ ] Item costs updated within the last 90 days
- [ ] No records with empty `.refs.keywords` arrays
- [ ] TypeScript interfaces match current Django models
- [ ] Dead stock items reviewed and acted on quarterly
- [ ] Sync conflicts resolved within 24 hours

---

## Interpreting Reports

### Health Score Distribution

| Range | Meaning | Action |
|-------|---------|--------|
| 80–100 | Excellent | No action |
| 60–79 | Good | Minor gaps — add missing keywords or links |
| 40–59 | Fair | Multiple fields empty — review and complete |
| 20–39 | Poor | Critical data missing — prioritize data entry |
| 0–19 | Critical | Record may be stub/orphan — investigate or delete |

### Margin Anomalies

| Flag | Meaning | Likely Cause |
|------|---------|--------------|
| `negative_margin` | Selling below cost | Cost not updated, or promotional pricing left active |
| `zero_margin` | Price equals cost | Missing markup, or cost = price as placeholder |
| `extreme_margin` | >90% margin | Cost likely $0 or placeholder — update cost |
| `no_cost_data` | Cost field empty | Vendor pricing not entered |

---

*Last updated: Phase 5 implementation. See [ai.md](ai.md) for the full integration plan.*
