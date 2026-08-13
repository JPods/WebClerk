# Onboarding — Alice's Guide to New Installations and New Users

## What This Is

When a new WC3 installation starts up, or a new user joins an existing one,
Alice coaches them through setup. Not a wizard — a conversation. Alice asks
questions, learns the answers, and configures the system.

## The Two Onboarding Moments

### 1. Installation Onboarding (Admin)

The admin sets up the installation. Alice walks them through:

**Company identity:**
- Company name, address, phone, logo
- Tax ID / business registration
- Time zone, currency, locale

**Payment setup:**
- What payment methods does the company use?
  - "We use a company Visa ending 3425, checks from Wells Fargo, and petty cash"
  - Alice writes: `Setting(payment, field_access).prefs.defaults.method = "visa_3425"`
  - Alice adds to select list: `visa_3425, check-WellsFargo, cash`
- Default expense category?
  - Alice sets: `Setting(payment, field_access).prefs.defaults.category = "Office Supplies"`
- Do you receive customer payments? What methods?
  - Alice configures the received payment defaults separately

**Expense categories:**
- What buckets does the company use?
  - Alice populates `Setting(payment, field_access).config.select_lists.category`
  - Maps each to a GL account via `gl_map`
  - Freehand always allowed — Alice learns new categories as they appear

**GL accounts:**
- Alice seeds default GL accounts (EXP-OFFICE-000, etc.)
- Admin can rename or remap
- The category → GL mapping is the bridge: users never see GL codes

**Contacts:**
- Import from Mac Contacts, CSV, or manual entry
- Alice enriches, deduplicates, scores matches

**Price levels and terms:**
- Default payment terms (Net 30, COD, etc.)
- Price levels if applicable (A/B/C/D)

### 2. User Onboarding (New Employee)

A new user logs in for the first time. Alice notices (no prior activity) and:

**Introduces the defaults:**
- "Your company's default payment method is visa_3425. You can change this per transaction."
- "Expenses default to category 'Office Supplies'. Use the dropdown or type a new category."

**Shows the entry points:**
- "Payments button shows all payments. Expenses button shows expenses only."
- "From an invoice, click Record Payment. From the dashboard, click Expenses for standalone expenses."

**Explains the checkbook:**
- "Positive amounts are money in. Negative amounts are money out."
- "The list is your checkbook register. Click any row to edit."

**Teaches search:**
- "Contact, customer, and vendor fields search by name. Type 2+ characters."
- "If the name isn't found, click '+ Add' to create it on the spot."

## Where Defaults Live

| Setting | Purpose | `.prefs.defaults` |
|---------|---------|-------------------|
| `payment` | `field_access` | `type`, `method`, `category` |
| `payment` | `workbench_fields` | `display.detail_width`, `display.font_size` |
| `order` | `field_access` | `status`, `priority` |
| `invoice` | `field_access` | `status`, `terms` |

Pattern: `Setting(parent_model=X, purpose='field_access').prefs.defaults` holds
the installation-level defaults for new records of type X. These are NOT user
preferences — they are company decisions. "We always start orders in 'draft'."
"Our default payment method is the company card."

## How Alice Learns

Alice watches for patterns:
- 80% of expenses use "visa_3425" → suggest as default
- New category "Software Subscriptions" typed 5 times → suggest adding to select list with GL mapping
- User always changes type from "expense" to "received" on invoices → suggest different entry point

Alice's observation pipeline: `observe → log → pattern → recommend → promote`.
Recommendations go to the admin. Promotions happen when the admin approves.

## What Alice Adds to Her Vectors

This onboarding readme should be chunked into Alice's vector store so she can:
- Answer "how do I enter an expense?"
- Answer "what's the company card?"
- Answer "how do I add a new vendor?"
- Guide a new admin through initial setup
- Recognize when a user is struggling (repeated cancels, empty saves, wrong entry point)

## Flight Simulators — Hands-On Training

After basic setup, Alice assigns flight simulator training as Action records
in the user's weekly project. Flight simulators are interactive step-by-step
windows where the user performs real actions and watches data change.

**Alice's onboarding checklist (new user Actions):**

1. **Complete Flight Simulator: Inventory** (`/flight-sim-inventory`)
   - 9 steps: proposal → order → invoice → purchase → receipt → payment → discount → write-off
   - Teaches: which transactions move inventory, when GL entries are created, why pending exists
   - Shows margin erosion: 40% gross → 5% net (and why Alice tracks it)

2. **Set impact.predicted on first 5 selling actions**
   - Teaches: the impact assessment loop (predict → act → retrospect → learn)
   - Not precision — retrospection. The gap is the learning signal.

3. **Review Alice's auto-filled impact.actual on 3+ actions**
   - Teaches: how Alice contributes (she guesses, user corrects, she learns)
   - Each 2-second correction saves hours of admin over time

4. **View Sales Pipeline** (`/sales-pipeline`) — find your conversion rate
5. **View Cash Conversion** (`/cash-conversion`) — find stalled invoices
6. **View Inventory Velocity** (`/inventory-velocity`) — find dead capital

Alice records completion of each step as an observation. She does not hard-gate
features behind training, but she prompts: "Have you completed the inventory
flight simulator? It takes 10 minutes and shows how these quantities work."

**Full documentation:** `readmes/topics/training/flight-simulators.md`
**Flowcharts:** `readmes/flowcharts/wc3-flight-sim-inventory.pdf`,
`readmes/flowcharts/wc3-impact-assessment-loop.pdf`

## The Principle

Onboarding is not a one-time event. It is Alice's permanent awareness that
some users know less than others, and every interaction is an opportunity to
teach without condescending. The admin sets the defaults. Alice explains them.
The user overrides when needed. Alice learns from the overrides.

The trail must be packed before it's open. A feature not trained is a feature
not used. Flight simulators are how we pack the trail.
