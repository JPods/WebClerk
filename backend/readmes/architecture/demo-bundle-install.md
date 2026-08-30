# Demo Bundle & Installation — How to Run WebClerk3

**Established:** 2026-08-21

## Get It Running

```bash
git clone https://github.com/JPods/webClerk3.git
git clone https://github.com/JPods/React2025.git
cd webClerk3
bash install-webclerk.sh
```

That's it. The install script checks dependencies, creates the database, builds
the frontend, migrates, seeds system data, loads demo data, and writes a
`run-webclerk.sh` for future starts. Open `http://localhost:8000`.

### Three Paths

| Path | Platform | Command |
|------|----------|---------|
| **Native install** | Mac, Linux | `bash install-webclerk.sh` |
| **Docker** | Mac, Linux, Windows | `bash docker-build.sh && docker compose up` |
| **Manual** | Any | See step-by-step below |

### Manual Steps (what the install script does)

1. Install Python 3.11+, PostgreSQL, Redis, Node.js
2. `createdb commerce_expert`
3. `python3 -m venv venv && venv/bin/pip install -r requirements.txt`
4. `cd ../React2025 && npm install && npm run build && cd ../webClerk3`
5. `cp .env.template .env` (edit database credentials if needed)
6. `venv/bin/python manage.py migrate`
7. `venv/bin/python manage.py seed_freshstart`
8. `venv/bin/python manage.py load_demo_data` (optional)
9. `venv/bin/python manage.py runserver`

---

## The Three Identifiers — id, uuid, ida

Every WC3 record has three identity fields. Each serves a different purpose:

| Field | Scope | Assigned by | Portable? | Purpose |
|-------|-------|-------------|-----------|---------|
| **id** | One database | PostgreSQL auto-increment | No | Fast lookups, FK references within this database |
| **uuid** | All databases | Python `uuid4()` on first save | Yes | The bridge — connects the same record across databases |
| **ida** | Human-readable | Generated on first save | Yes (in demo) | User-facing identifier (`BAT-01`, `INV-01`, `CON-01`) |

### Why Three?

- **id** is fast but not portable. Database A assigns `id=42` to a customer.
  Database B assigns `id=42` to a completely different record.
- **uuid** is portable but not human-readable. Nobody wants to say
  "look up invoice `7a369e49-eab2-4008-aaf4-706e5f8db29c`."
- **ida** is human-readable and meaningful. `INV-01` tells you it's the first
  invoice. But in a busy system with multiple data sources, ida can collide.

The three together solve every case:
- **Within one database:** use `id` (fast, indexed, FK references)
- **Between databases:** use `uuid` (unique everywhere, the bridge for FK remapping)
- **Talking to humans:** use `ida` (readable, meaningful)

### The Matching Rule

When two databases exchange records (sync, bundle import, demo load):

| id match? | uuid match? | Meaning | Action |
|-----------|-------------|---------|--------|
| Yes | Yes | Same record | Update (take newer `dt_modified`) |
| Yes | No | PK collision | Reassign PK |
| No | Yes | Same record, different PKs | Update, align to target PK |
| No | No | New record | Insert |

**uuid is always authoritative.** id is a database-local convenience.

Full sync documentation: [data-sync-consolidated.md](../infrastructure/data-sync-consolidated.md)

---

## Demo Bundle — Portable Data

The demo bundle (`demo-bundle.json`) contains Settings + sample data that can
be loaded into any empty WC3 database.

### What's In the Bundle

| Layer | Records | Purpose |
|-------|---------|---------|
| **Settings** | 85 | System infrastructure — model definitions, field behaviors, RBAC, company profile, GL accounts |
| **Contacts** | 7 | Demo people (Sarah Chen, Mike Rodriguez, etc.) |
| **Orgs** | 6 | 5 customers + 1 vendor (Riverside Sports, Metro Baseball Academy, etc.) |
| **Items** | 12 | Baseball equipment with tiered pricing (bats, balls, gloves, bags, kit) |
| **BOM** | 4 | Kit components (Little League Starter Kit) |
| **Transactions** | 17 | 3 complete cycles: proposal → order → invoice (with lines) |
| **Payments** | 4 | Check and credit card payments applied to invoices |
| **GL Journal** | 14 | AR/Sales/Cash journal entries for each cycle |

### How FK Resolution Works

The bundle carries every record's `id` (old PK from source database) and `uuid`.
When loading into a new database:

1. **Import contacts and orgs first** — they have no FK dependencies
2. **Build uuid→new_pk array** — as each record is inserted, the new database
   assigns a new `id`. We record `{uuid: new_pk}` for every record.
3. **Import transactions** — each has FK fields like `customer_id=5`. We look up
   what uuid had `id=5` in the source, then find that uuid's new PK in our array.
4. **Set the FK to the new PK** — the transaction now points to the right
   customer in this database.

This is the same `uuid_map` pattern used by the full sync system
(§25.1 in [data-sync-consolidated.md](../infrastructure/data-sync-consolidated.md)),
simplified for the demo case where the target database is empty.

**Why demo is simpler than sync:**
- Empty database = no ida collisions, no version conflicts, no merge decisions
- ida values (`BAT-01`, `PROP-01`) are meaningful names, not auto-generated
  prefixed IDs — they arrive clean and stay clean
- Only `id` needs remapping (uuid is the bridge, ida passes through unchanged)

### Commands

| Command | What it does |
|---------|-------------|
| `manage.py seed_demo` | Create demo contacts, orgs, items, BOM |
| `manage.py seed_demo_transactions` | Create 3 transaction cycles with GL |
| `manage.py pack_demo_bundle` | Export Settings + demo data → `demo-bundle.json` |
| `manage.py load_demo_data` | Import bundle into database (with FK resolution) |
| `manage.py load_demo_data --dry-run` | Preview without writing |
| `manage.py load_demo_data --settings-only` | Load Settings only |
| `manage.py load_demo_data --data-only` | Load data only (skip Settings) |
| `manage.py remove_demo_data` | Delete all records tagged `refs.source=demo-baseline` |
| `manage.py remove_demo_data --dry-run` | Preview what would be deleted |

### Tagging — refs.source

Every demo record is tagged `refs.source = "demo-baseline"`. This is how
`remove_demo_data` finds them — no naming convention needed, no prefix on ida,
just a JSON field that says where the record came from.

Settings are never removed. They are system infrastructure.

---

## Flowchart

![Demo Bundle Install Flow](../../flowcharts/demo-bundle-install.svg)

Source: [demo-bundle-install.dot](../../flowcharts/demo-bundle-install.dot)

---

## Files

| File | Purpose |
|------|---------|
| `install-webclerk.sh` | Mac/Linux native installer |
| `docker-compose.yml` | All-platform Docker setup |
| `docker-build.sh` | Multi-repo Docker build helper |
| `Dockerfile` | Container image definition |
| `.env.template` | Environment config template |
| `tools/webclerk-entrypoint.sh` | First-run detection + auto-setup |
| `demo-bundle.json` | Portable demo data bundle |
| `apps/core/management/commands/pack_demo_bundle.py` | Export bundle |
| `apps/core/management/commands/load_demo_data.py` | Import bundle with FK resolution |
| `apps/core/management/commands/remove_demo_data.py` | Clean removal by refs.source |
| `apps/core/management/commands/seed_demo.py` | Seed demo contacts/orgs/items |
| `apps/transactions/management/commands/seed_demo_transactions.py` | Seed transaction cycles |
