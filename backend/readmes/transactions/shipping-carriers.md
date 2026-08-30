# Shipping Carriers — Setup Guide

> **Last updated**: 2026-08-05
> **Owner**: Alice
> **Backend**: `apps/transactions/services/carriers/`
> **Connections**: `seed_connections` creates draft records for all four carriers

---

## How It Works

Each carrier is a Connection record with your API credentials. You fill in
your keys, set status to active, and the carrier is live. No rate tables to
download. No charts to maintain. The carrier's API returns live rates,
generates labels, and provides tracking — all through WC3.

**Ask Alice:** "Connect me to UPS" or "Set up FedEx shipping" and she will
walk you through it. She knows what credentials each carrier needs and
where to get them.

---

## Carrier Matrix

| | UPS | FedEx | USPS | DHL Express |
|---|---|---|---|---|
| **Connection ida** | `conn-carrier-ups` | `conn-carrier-fedex` | `conn-carrier-usps` | `conn-carrier-dhl` |
| **Auth method** | OAuth 2.0 | OAuth 2.0 | OAuth 2.0 | Basic Auth |
| **Get rates** | Yes | Yes | Yes | Yes |
| **Create labels** | PDF, GIF, ZPL, PNG | PDF, PNG, ZPL | PDF, PNG | PDF, ZPL, PNG |
| **Track shipments** | Yes | Yes | Yes | Yes |
| **Validate addresses** | Yes | Yes | Yes | — |
| **Cancel/void** | Yes | Yes | — | — |
| **Developer portal** | developer.ups.com | developer.fedex.com | developer.usps.com | developer.dhl.com |
| **Sandbox/test mode** | Yes | Yes | Yes | Yes |
| **Credentials needed** | client_id, client_secret, account_number | client_id, client_secret, account_number | client_id, client_secret | user_id, password, account_number |

---

## Setup — Step by Step

### Ask Alice

The fastest path. Tell Alice which carrier you want and she'll guide you:

> **You:** "I want to ship with UPS"
>
> **Alice:** "I'll walk you through it. First, go to developer.ups.com and
> create a developer account. Then create an app — you'll get a client ID
> and client secret. You'll also need your UPS account number (the shipper
> number on your UPS bills). Tell me when you have all three."
>
> **You:** "Got them — client ID is X, secret is Y, account is Z"
>
> **Alice:** "I've updated your UPS connection with those credentials and
> set it to test mode. Try getting rates on an order to verify it works.
> When you're ready for production, tell me and I'll switch off test mode."

Alice creates or updates the Connection record, sets `test_mode: true` for
safety, and lets you verify before going live.

### Manual Setup

1. **Go to the carrier's developer portal** (see matrix above)
2. **Create a developer account** and register an application
3. **Get your credentials** (client ID, client secret, account number)
4. **Open the Connection record** in databrowser: `/db/connection`
5. **Find your carrier** (e.g., `conn-carrier-ups`)
6. **Edit config.credentials** — paste in your keys
7. **Set status = active**
8. **Test** — go to any order, click Ship Order, rates should appear

### What Each Carrier Needs

#### UPS (developer.ups.com)

1. Create account at developer.ups.com
2. Create an app → get **Client ID** and **Client Secret**
3. Your **UPS Account Number** (shipper number — on your UPS invoices)
4. Paste all three into `config.credentials` on `conn-carrier-ups`

#### FedEx (developer.fedex.com)

1. Create account at developer.fedex.com
2. Create a project → get **API Key** (= client_id) and **Secret Key** (= client_secret)
3. Your **FedEx Account Number** (on your FedEx invoices)
4. Paste all three into `config.credentials` on `conn-carrier-fedex`

#### USPS (developer.usps.com)

1. Create account at developer.usps.com
2. Register an app → get **Consumer Key** (= client_id) and **Consumer Secret** (= client_secret)
3. No account number needed — USPS uses the app credentials directly
4. Paste both into `config.credentials` on `conn-carrier-usps`

#### DHL Express (developer.dhl.com)

1. Create account at developer.dhl.com
2. Register for MyDHL API → get **User ID** and **Password**
3. Your **DHL Account Number**
4. Paste all three into `config.credentials` on `conn-carrier-dhl`

---

## Settings You Can Adjust

Each carrier Connection has `config.settings` with tunable parameters:

| Setting | Default | What it does |
|---------|---------|-------------|
| `test_mode` | `true` | Use sandbox API (no real charges, no real labels). Set `false` for production. |
| `label_format` | `pdf` | Label output: `pdf`, `gif`, `zpl` (Zebra), `png`. Match your printer. |
| `fuel_factor` | `0` | Additional fuel surcharge as decimal (0.12 = 12%). Only if the carrier's API doesn't include it in rates. |
| `handling_charge` | `0` | Flat per-package handling fee added to every shipment. |
| `markup_percent` | `0` | Percentage markup on total cost. Use to cover overhead or build margin into shipping. |

**WC2 heritage:** These settings come from WC2's Carrier table fields
(`fuelFactor`, `handlingCharge`). In WC2 you maintained local rate charts
downloaded from the carriers and calculated costs offline. In WC3, the carrier
API calculates the rate — these settings are additional adjustments your
business applies on top.

---

## What Changed from WC2

| WC2 | WC3 | Why |
|-----|-----|-----|
| Downloaded zone/weight rate charts | Live API rate queries | Carriers update rates constantly; local tables go stale |
| Manual ZIP-to-zone lookup tables (CarrierZone) | Carrier API handles routing | No tables to maintain |
| Weight bracket pricing (CarrierWeight) | Carrier API returns total cost | Dimensional weight, surcharges, negotiated rates all handled by API |
| UPS XML toolkit (deprecated 2024) | UPS REST OAuth 2.0 | Old API is shut down |
| FedEx SOAP/WSDL (deprecated 2024) | FedEx REST OAuth 2.0 | Old API is shut down |
| USPS Web Tools XML | USPS REST OAuth 2.0 | Old API deprecated |
| Local barcode generation (UPS mod-10) | Carrier API returns labels | Real tracking numbers, real labels, no local generation |
| CSV export for UPS WorldShip | Direct API label creation | No intermediate file, no desktop software |

**What stayed the same:**
- Fuel surcharge, handling, insurance as business-level adjustments
- Ship-on-date calculation (business days back from needed date)
- ASN email notification pattern
- The packing workflow (pick → pack → ship → invoice)

---

## Rate Shopping

When multiple carriers are active, the Pack & Ship panel can show rates
from all of them side by side. The user picks the best rate for each
shipment.

**How it works:**
1. User clicks Ship Order on an order
2. In the Ship step, system calls `get_shipping_rates` for each active
   carrier Connection
3. Rates displayed in a comparison table: carrier, service, cost, transit days
4. User selects → `create_carrier_shipment` generates the label
5. Label prints → tracking number recorded → invoice created

**Ask Alice:** "Show me rates for this order" and she'll query all active
carriers and present the comparison.

---

## Tracking

After shipment, the tracking number is stored on the invoice
(`metadata.shipping.tracking_number`). The tracking panel calls
`track_shipment` with the Connection ID and tracking number to get
live status and event history from the carrier.

**Ask Alice:** "Track shipment 1Z999AA10123456784" and she'll look up
the carrier from the tracking number prefix and return the status.

---

## Multiple Carriers

Most businesses use 2-3 carriers. Each gets its own Connection record.
You can have multiple connections for the same carrier (e.g., UPS with
different account numbers for different ship-from locations).

The Connection record is the single source of truth for each carrier
relationship — credentials, settings, surcharges, test/production mode.
Alice manages them. You tell her what you need.

---

## Alice's Role

Alice can:
- Walk you through carrier setup (credentials, test mode, go-live)
- Update Connection config with your API keys
- Explain what each setting does
- Help troubleshoot rate or label errors
- Compare rates across carriers for a shipment

Alice should escalate to Claude Code when:
- A carrier changes their API (new endpoints, new auth method)
- Custom carrier integration needed (regional carrier, freight broker)
- Webhook setup for real-time tracking updates

---

*No rate tables. No downloaded charts. No stale data.
The carrier knows their rates. Ask them.*

*Established 2026-08-05 by Bill James and the team.*
