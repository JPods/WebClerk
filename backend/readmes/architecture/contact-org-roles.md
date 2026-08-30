# Contact-to-Org Role Architecture

**Decision date:** 2026-08-25
**Status:** Accepted — keep 5 FK columns, user sets roles manually

## The Problem

The same company can be a customer, a vendor, a rep, a manufacturer, and an employer. The same person (Contact) may need to be linked to that company in multiple roles. How should Contact reference OrgBase?

## Options Considered

### Junction table (ContactRole)

A many-to-many through table: `contact FK, org FK, role, is_primary`.

**Pros:** Extensible, clean queries for "all contacts at this org regardless of role," no nullable FK columns.

**Cons:** Adds a JOIN to every contact query. ~97% of contacts have exactly one org link — the junction table adds complexity to 100% of queries for a problem that affects 3%. The UI must explain a many-to-many relationship that almost never applies.

**Rejected** — the cost is borne by the common case to serve the rare case.

### Auto-population of sibling role FKs on save

When a contact is linked to an org, automatically find other OrgBase records with the same `display_name` and different `org_type`, and set those FK columns.

**Rejected** — too messy. Silently creating relationships behind the user's back leads to invisible data problems. The user owns the relationship.

### 5 FK columns on Contact, user sets each (chosen)

Direct nullable ForeignKeys: `customer_id`, `vendor_id`, `manufacturer_id`, `employee_id`, `rep_id`. Each points to an OrgBase record. The user explicitly sets each one.

**Pros:** Direct, fast, no JOIN for the 97% case. A contact linked to one org = one non-null FK, four nulls. Simple to query, simple to display. User controls what's linked — no surprises.

**Cons:** 4 null columns per contact (trivial storage cost). When the same company is both customer and vendor, the user must set both FKs manually.

**Accepted** — the 97% simplicity outweighs the 3% inconvenience, and a report function can recommend connections for the 3%.

## Handling the 3% — Recommendations, Not Automation

For the ~3% of contacts where an org holds multiple roles, the approach is:

1. **Report function** — a report that identifies contacts where an org's `display_name` matches OrgBase records in other roles that aren't linked. Surfaces recommendations for the user to act on.
2. **Alice watches** — Alice can observe patterns in this data over time. If auto-recommendation proves useful and reliable, it can be added later as a suggestion (never a silent write).

The user always makes the connection. The system can suggest, never assume.

**Location:** `apps/core/models/contact.py` — `save_after()` handles bidirectional refs sync only; no auto-population of role FKs.

## What This Means for the UI

- Linking a contact to an org is explicit — user picks the org and the role
- Contact display shows "John Smith — Acme (customer, vendor)" by reading which FK columns are non-null
- No junction table to explain, no hidden writes, no "where did this link come from?"
- A report surfaces unlinked sibling roles as recommendations

## The Trade-Off in One Sentence

Four null columns on 97% of contacts is a smaller cost than a mandatory JOIN on 100% of contact queries — and the 3% is handled by surfacing recommendations, not by silent automation.
