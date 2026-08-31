# Alice Data Quality — Three-Tier Processing, Polishing, Field Discipline, File Storage

**Established:** 2026-07-25
**Applies to:** All models, all WC3 installations

---

## Part 1 — Three-Tier Processing

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

### The Rule

> Tier 1 always runs. Tier 2 runs on what Tier 1 can't resolve. Tier 3 runs only when Tier 2 flags low confidence and the user hasn't acted.

Tier 1 and 2 are silent — they just work. The user sees the result, not the machinery.
Tier 3 never runs without asking.

### What Gets Preserved

Every data quality action preserves the original:

| Action | Original stored in |
|--------|--------------------|
| Phone normalized | `config.phone_original` |
| Email scrubbed | `config.scrubbed.original_email` |
| Zip normalized | `config.zip_original` |
| Records merged | `config.merged_records[]` |
| Import data | `config.original_mac` (or `original_{source}`) |

Nothing is lost. Every transformation is reversible.

### Admin Visibility

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

### Email Scrubbing Checklist (Tier 1)

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

### Phone Scrubbing Checklist (Tier 1)

1. Strip all non-digits
2. 10 digits (US) → prepend `1`
3. 11 digits starting with `1` → US, keep as-is
4. Starts with `+` → explicit country code, trust it
5. < 7 digits → invalid, move to config
6. Detect country code from leading digits (try 3, 2, 1 digit prefixes)
7. Display: format per country, separator from user preference (`.` or `-`)
8. Local mode: hide country code when it matches org default
9. International mode: always show `+code`

### Connection-Based Providers

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

---

## Part 2 — Data Polishing (Guess, Review, Validate)

**Established:** 2026-08-01

### The Principle

Better to have a guess than a blank. Blanks are invisible failures. Wrong guesses generate visible corrections. The system learns from corrections, not from blanks.

### Three Correction Layers

| Layer | Who | When | What happens |
|-------|-----|------|-------------|
| **1. Alice guesses** | Alice (nightly) | Automated | Fills blank fields with best available data from linked records |
| **2. Admin reviews** | System admin | Morning dashboard | Sees what Alice changed overnight, overrides if wrong |
| **3. Users validate** | Daily users | During work | See wrong data on orders/invoices, complain → correction signal |

Each layer catches what the previous missed. The cost of asking permission first is higher than the cost of a wrong guess — because asking blocks action, while a wrong guess generates a correction that teaches Alice.

### What Alice Polishes

**Org ← Contact (most common):**

| Org field | Source | How Alice decides |
|-----------|--------|------------------|
| `phone` | Primary contact's phone | Highest-role contact, most recent |
| `email` | Primary contact's email | Same |
| `attention` | Primary contact's display_name | Same |
| `address_full` | Primary contact's address | Same |
| `price_level` | Most recent order's price_level | If org is blank, inherit from transaction history |
| `terms` | Most recent order's terms | Same |

**Contact ← Communications:** When phone/email are in the communications aspect but not on flat fields.

**Transaction ← Customer:** When an order/invoice has `customer_id` but no `company`, `phone`, `attention` populated — Alice fills from the customer's org record + primary contact.

### The Nightly Run

1. **Scan** — find records with blank key fields
2. **Source** — for each blank, find the best available value from linked records
3. **Score** — assign confidence (high: primary contact phone → org phone; low: old order terms → org terms)
4. **Apply** — write the guess to the blank field
5. **Log** — write a polish record: model, ida, field, old_value, new_value, source, confidence, dt_applied

### The Dashboard (db.list)

A DataGrid at `/db/alice_data_polish` showing tonight's changes:

**Columns:** model | ida | field | old | new (guess) | source | confidence | action

**Admin actions per row:**
- **Accept** — confirm Alice's guess (stops showing on dashboard)
- **Override** — enter correct value (teaches Alice)
- **Revert** — put back the blank (Alice was wrong to guess)

Alice learns from admin actions: Overrides teach better sourcing. Reverts teach which fields should stay blank. Accepts confirm heuristics.

### What Alice Does NOT Polish

- **Fields with values** — Alice never overwrites existing data
- **Fields marked "intentionally blank"** — admin can flag a field as intentionally empty
- **Sensitive fields** — passwords, API keys, financial account numbers
- **Calculated fields** — totals, margins, balances (those come from transactions)

---

## Part 3 — Field Size Discipline

### Thresholds (system defaults, overridable per Setting)

| Field | Max bytes | Purpose |
|-------|-----------|---------|
| metadata | 128,000 | System behavior — workflow, flags, history |
| prefs | 96,000 | User preferences — UI state, display |
| config | 64,000 | Application data — form fields, content |
| refs | 64,000 | Relationships — links, parents, pointers |
| actions | 32,000 | Task/action list — small, query-friendly |

Progressive telemetry fires at 30%, 60%, 75% of each limit.

### Alice's Role

**Observe:** Alice watches `check_size` telemetry. Every threshold crossing is tracked by user, model, and field.

**Coach at 75%:** "Your config on Action #4521 is 48KB. The specs section is 40KB. Want me to move it to a Document?"

**Enforce at the write boundary:** Alice prevents oversized inline data — she does not coach after the fact. Behavior that harms the user is not a preference to respect.

- **Documents over threshold** → stored as files, referenced by path
- **Images** → stored as files, always. Thumbnail in metadata if needed.
- **Reports** → generated on demand, cached as files, path in the record.

At save time, if content exceeds the inline threshold:
1. Create a Document record (or file) with the oversized content
2. Replace the inline data with a pointer: `{"_document_id": <id>, "_path": "<path>"}`
3. Log what she did in the record's metadata.history
4. This is automatic, not optional. The user gets the same data faster.

**Auto-offload (learned behavior):** For patterns Alice observes over time — same model type always producing large content — she preemptively routes to Document at creation time.

### For Sync

- Payload below 4KB: inline in bundle (encrypted)
- Payload above 4KB: encrypted to Document, path + key in bundle
- Receiver creates per-document Pending records
- Each document retries independently until received + verified

---

## Part 4 — File Storage Enforcement

### Rules Alice Enforces

**1. Path Structure:** Every file must follow: `/media/<org_id>/<model>/<record_id>/<filename>`

If a file is saved outside this structure, Alice moves it, updates metadata.images, and logs the correction.

**2. Image Sizes:** On every image upload, Alice ensures all sizes are generated:
- tn (64px) — lists, badges, gantt assignee
- sm (128px) — contact card, chat avatar
- md (256px) — profile page, directory
- lg (512px) — detail page hero
- original — user download, print

Missing sizes are generated on demand. Alice tracks which sizes are accessed and can skip pre-generation for rarely-viewed records.

**3. Metadata Sync:** After file operations, Alice verifies:
- `record.metadata.images` paths match actual files on disk
- Orphaned files (on disk but not in metadata) are flagged
- Dead references (in metadata but not on disk) are cleaned

**4. Tenant Isolation:** Alice never serves a file from org A to a user in org B. Path structure enforces this — Alice validates at the application layer as defense-in-depth.

**5. Size Limits:** Images over 10MB rejected at upload. Documents over inline threshold stored as files.

### Nightly Cleanup Algorithm

1. Walk `/media/{org_id}/` directories
2. For each file, check if metadata.images references it
3. Orphaned files → log warning, do not delete (admin decides)
4. Dead references → clear from metadata.images
5. Missing sizes → generate on demand if record was accessed recently

---

## Key Files

| File | Purpose |
|------|---------|
| `apps/ai_assistant/services/dedup_service.py` | Dedup scan and bundle extraction |
| `apps/ai_assistant/services/user_patterns.py` | Pattern detection, observation creation |
| `apps/ai_assistant/services/field_change_requests.py` | Field change requests as observations |
| `apps/core/services/wcapi_registry.py` | `_ALIAS_MAP` for alice model names |

## Related

- [pattern-recognition.md](pattern-recognition.md) — Alice's observe > log > pattern > recommend > promote loop
- [dedup.md](dedup.md) — Duplicate detection (uses Tier 1 matching strategies)
- [observation-setup.md](observation-setup.md) — How Alice observations feed the coaching UI
