# Alice Data Quality — Three-Tier Processing

**Established:** 2026-07-25
**Applies to:** All models, all WC3 installations

---

## The Three Tiers

Every data quality operation runs through three tiers. Each tier handles what the previous tier couldn't.

### Tier 1 — Hard Algorithms

Fast, deterministic, zero cost. Runs on every save, every import, every Celery sweep.

**Phone:**
- Strip to digits, prepend country code if missing
- Default country from org Settings
- Store: `14055551234`. Display: `405.555.1234`
- Split concatenated email+phone (`info@okmhf.orgll405-424-5313`)

**Email:**
- Lowercase and trim
- Detect missing `@`, trailing dots, special chars, bare `@`
- Split email+phone concatenation on common separators (`ll`, `ip`, `||`)
- Move garbled emails to `config.scrubbed`, set placeholder
- `+` in local part is valid (Gmail/platform tracking)

**Zip/Postal:**
- Strip to digits (US) or uppercase alphanumeric (CA/UK)
- Format: `74135-4321` (US), `A1B 2C3` (CA), `SW1A 1AA` (UK)

**Dedup:**
- Exact match on email (unique constraint)
- Exact match on first+last name (groups for review)
- Score: real email (+3), phone (+2), company (+1), address (+1), title (+1)
- Auto-merge when single clear winner. Flag for human review when ambiguous.

**When it runs:**
- On every field widget blur (client-side, instant feedback)
- On every import batch (server-side, Celery task)
- Weekly full-database sweep (Celery beat)

### Tier 2 — Alice's Own LLM

Trained on THIS installation's data patterns. Small model, fast, private, runs locally.

**What Alice learns:**
- Card reader OCR patterns specific to this user's contact sources
- Which email provider each company uses (JPods → jpods.com)
- Common name misspellings in this database
- Which contacts are actually organizations stored as people
- Domain → company mapping from existing data

**When it runs:**
- After Tier 1 flags something it can't resolve
- On records with `config.scrubbed` (garbled data needing interpretation)
- During dedup when name similarity is fuzzy (Bill/William, Bob/Robert)
- When suggesting merge candidates

**Confidence threshold:** Alice acts silently above 0.9. Flags for human review between 0.5-0.9. Escalates to Tier 3 below 0.5.

### Tier 3 — General LLM

For things Alice hasn't seen before. Expensive, slower, handles the long tail.

**What Tier 3 handles:**
- New country phone/address formats Alice hasn't encountered
- Company name recognition from domains she doesn't know
- Email domain validation against public records
- Address standardization for countries not in the format table

**When it runs:**
- Only when Tier 2 flags low confidence AND the user hasn't acted
- Never automatically — Alice asks before calling Tier 3
- Results feed back into Tier 2 training (Alice gets smarter)

---

## The Rule

> Tier 1 always runs. Tier 2 runs on what Tier 1 can't resolve. Tier 3 runs only when Tier 2 flags low confidence and the user hasn't acted.

Tier 1 and 2 are silent — they just work. The user sees the result, not the machinery.
Tier 3 never runs without asking.

---

## What Gets Preserved

Every data quality action preserves the original:

| Action | Original stored in |
|--------|--------------------|
| Phone normalized | `config.phone_original` |
| Email scrubbed | `config.scrubbed.original_email` |
| Zip normalized | `config.zip_original` |
| Records merged | `config.merged_records[]` |
| Import data | `config.original_mac` (or `original_{source}`) |

Nothing is lost. Every transformation is reversible.

---

## Admin Visibility

Every automated function Alice performs is visible in the Alice admin dialog:

| Task | Schedule | Controllable |
|------|----------|-------------|
| Phone normalization | On import + weekly sweep | Enable/disable, force run |
| Email scrubbing | On import + weekly sweep | Enable/disable, force run |
| Zip formatting | On import + weekly sweep | Enable/disable, force run |
| Dedup scan | On import + monthly sweep | Enable/disable, force run |
| ZeroBounce validation | On demand + quarterly | Enable/disable, set provider |
| Address verification | On demand | Enable/disable, set provider |

Admin sees: task name, last run, next run, records affected, pass/fail.
Admin can: enable, disable, force run, view history.

No invisible automation. Gordy's quality principle applied to AI.

---

## Email Scrubbing Checklist (Tier 1)

1. No `@` sign → not an email (move to config)
2. `@` at start or end → garbled
3. Apostrophe in domain → OCR error
4. No dot in domain → truncated or social handle
5. Trailing dot → likely missing TLD (try common: .com, .gov, .org)
6. Special chars (`! # > ~ \`) → OCR garble, clean or placeholder
7. `+` in local part → valid (Gmail/platform tracking)
8. Trailing `>` → copy-paste artifact, strip
9. Email+phone concatenation → split on separator (`ll`, `ip`, `||`, digits after valid TLD)
10. If cleaned email collides with existing → it's a dupe, soft-delete
11. Multiple `@` signs → garbled, move to config
12. Space in email → split or clean

## Phone Scrubbing Checklist (Tier 1)

1. Strip all non-digits
2. 10 digits (US) → prepend `1`
3. 11 digits starting with `1` → US, keep as-is
4. Starts with `+` → explicit country code, trust it
5. < 7 digits → invalid, move to config
6. Detect country code from leading digits (try 3, 2, 1 digit prefixes)
7. Display: format per country, separator from user preference (`.` or `-`)
8. Local mode: hide country code when it matches org default
9. International mode: always show `+code`

---

## Connection-Based Providers

External validation services are managed through the WC3 Connection model:

| Provider | Service | Connection config |
|----------|---------|-------------------|
| ZeroBounce | Email validation | `api_key`, `credits_remaining` |
| NeverBounce | Email validation | `api_key` |
| SmartyStreets | Address verification | `auth_id`, `auth_token` |
| USPS | Address standardization | `user_id` |
| Google Places | Address autocomplete | `api_key` |

Admin selects active provider per service type. Alice uses the active Connection.
Multiple providers per service type allowed — Alice can fall back if one is down.
