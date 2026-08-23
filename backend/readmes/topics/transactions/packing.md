# Packing — Transaction Flow & Scale Hardware

> **Last updated**: 2026-08-05
> **Owner**: Claude Code + Alice
> **Backend**: `apps/transactions/services/shipping.py`
> **Frontend**: `React2025/src/apps/transactions/components/detail/PackingPanel.tsx`
> **Scale hook**: `React2025/src/hooks/useScale.ts`

---

## The Flow

Packing is the bridge between order and invoice. The order→invoice conversion
IS the ship event. There is no separate "shipped" quantity field — the invoice
line's `quantity.active` is the shipped quantity.

```
Order                          Packing                         Invoice
┌──────────────┐              ┌──────────────┐              ┌──────────────┐
│ quantity:    │              │              │              │ quantity:    │
│   active: 10 │──── pick ───▶│  scan item   │              │   active: 10 │
│   remaining:10│              │  scale check │──── ship ───▶│   staged: 10 │
│              │              │  box assign  │              │   remaining:10│
└──────────────┘              │  confirm     │              └──────────────┘
                              └──────────────┘
                                    │
                              order.remaining
                              decreases by
                              transfer amount
```

### quantity.active is the verb of the document

| Document | `quantity.active` means |
|----------|------------------------|
| order_line | quantity **ordered** |
| invoice_line | quantity **shipped** |
| purchase_line | quantity **purchased** |
| receipt_line | quantity **received** |

There is no `shipped`, `picked`, or `packed` key in the quantity object.
The document type gives the quantity its meaning.

- **What hasn't shipped?** → `order_line.quantity.remaining`
- **What shipped?** → `invoice_line.quantity.active`
- **Partial shipment?** → Multiple invoices from one order. Each invoice's
  `quantity.active` = what that shipment carried. Order `remaining` decreases.

---

## Three Steps

### 1. Pick

Backend: `generate_pick_list(order_id)`

Reads order lines where `quantity.remaining > 0`. Looks up warehouse/bin
from `item.metadata.warehouse` or Warehouse FK. Returns sorted by
warehouse → bin → line_number so the picker walks the warehouse once.

```python
# Returns:
[{
    "line_id": 42,
    "item_id": 100,
    "item_ida": "WIDGET-A",
    "item_name": "Widget Alpha",
    "qty": 10.0,            # quantity.remaining — what needs picking
    "bin_location": "A-3-2",
    "warehouse": "Main",
    "line_number": 10,
}]
```

UI: checklist view. Click to pick, checkbox all. Sorted for efficient walk.

### 2. Pack

Backend: `confirm_pack(order_id, packed_lines)`

Records what goes in which box. Stored in `order.metadata.shipping.packed_lines[]`.
Does NOT mutate line quantities — packing is about boxing, not quantity transfer.

```python
# packed_lines input:
[{
    "line_id": 42,
    "qty_packed": 10,
    "carrier": "UPS",
    "tracking_number": "",
    "weight": 12.5,         # from scale
}]
```

UI: multi-box support. Add items to boxes, set weight (manual or from scale),
edit qty per line. Boxes are frontend-only state until confirm.

### 3. Ship

Backend: `ship_order(order_id, shipping_data)`

Calls `convert_order_to_invoice()` — the ONE PATH for inventory transfer.
This is the ship event:
- Order `quantity.remaining` decreases
- Invoice created with `quantity.active` = shipped amount
- Inventory adjustments fire via signals
- Commission carry-forward handled by conversion chain

Shipping metadata stored on both order and invoice:

```python
# invoice.metadata.shipping:
{
    "carrier": "UPS",
    "tracking_number": "1Z999AA10123456784",
    "ship_date": "2026-08-05",
    "freight_cost": 12.50,
    "dt_shipped": 1722816000000,
}

# order.metadata.shipping.shipments[]:
[{
    "invoice_id": 234,
    "invoice_ida": "INV-0234",
    "carrier": "UPS",
    "tracking_number": "1Z999AA10123456784",
    "ship_date": "2026-08-05",
    "dt_shipped": 1722816000000,
}]
```

---

## Scale Hardware

### How it works

A USB or serial scale sits under the packing box. As items are scanned and
placed in the box, the scale reading increases. The system compares the
actual scale reading to the expected weight (sum of item unit weights ×
quantities scanned plus tare weight of the box).

This is continuous validation — like self-checkout. Each item scan triggers
a weight check. Mismatch = wrong item or wrong count, caught immediately.

### The algorithm (from WC2, ported to `useScale.ts`)

```
Expected = product_weight + tare_weight
Actual   = scale_reading
Deviation = Expected − Actual

If |Deviation| > (precision% + dither%) of Actual:
    STATUS = MISMATCH (red)
    Message: "Scale Over/Under By: X (Y%)"
Else if tare < -(dither + scale × precision%):
    STATUS = NEGATIVE_TARE (red)
Else:
    STATUS = OK (green)
```

**Stability detection**: 6 identical consecutive readings = stable.
Scale readings that fluctuate are not stable — weight is still settling
or items are still being placed.

**Dither factor**: readings below this threshold are treated as zero.
Prevents noise from registering as weight. WC2 default: varies by scale.
WC3 default: 0.05 lbs.

### Variables (WC2 → WC3 mapping)

| WC2 | WC3 `useScale` | What |
|-----|-----------------|------|
| `<>vrWeightScale` | `weightScale` | Live scale reading |
| `<>vrWeightProduct` | `weightProduct` | Expected product weight |
| `<>vrWeightTare` | `weightTare` | Box/container weight |
| `<>vrWeightDeviation` | `deviation` | Expected − actual |
| `<>vrWeightErrPC` | `deviationPct` | Deviation as % |
| `<>wtPrecisionPC` | `precisionPct` | Allowed variance % |
| `<>wtDitherFactor` | `ditherFactor` | Noise floor |
| `<>scanScaleItemWt` | `lastScanWeight` | Scale before last scan |
| `<>itemWt` | `expectedItemWt` | Expected item weight |
| `<>itemDeltaWt` | `itemDelta` | Actual delta from scan |
| `<>scanItemPC` | `itemDeltaPct` | Delta as % of expected |
| `<>pkScaleComment` | `status` + `message` | Human-readable status |

### Serial communication

WC2 used 4D's `SET CHANNEL` to talk to the scale:

```
SET CHANNEL(21; 19466)  — Mac serial port, 9600 baud, 8N1
SEND PACKET("W\r")      — weight command
RECEIVE BUFFER(response) — ASCII weight string
```

WC3 uses the Web Serial API (Chrome/Edge):

```typescript
const port = await navigator.serial.requestPort();
await port.open({ baudRate: 9600, dataBits: 8, stopBits: 1, parity: 'none' });
// Write: encoder.encode("W\r")
// Read: decoder.decode(value) → parse first 12 chars as float
```

### Serial config options

| Parameter | Default | Notes |
|-----------|---------|-------|
| `baudRate` | 9600 | Standard for most bench scales |
| `dataBits` | 8 | WC2 used 7 on some older scales |
| `stopBits` | 1 | |
| `parity` | none | WC2 used even on some scales |
| `weightCommand` | `"W\r"` | Some scales use `"H\r"` for hold weight |
| `pollInterval` | 500ms | WC2 used ~167ms (10 ticks at 60Hz) |

### What we require from a scale

Hardware will change. Alice needs to evaluate any scale against these specs.

**Required:**
- **Serial output** — USB-serial or RS-232. Must enumerate as a serial port
  to the OS. The Web Serial API talks to anything the OS sees as a COM/tty port.
- **ASCII weight command** — scale must accept a single-character command
  (`W`, `H`, `S`, `P`, or similar) followed by CR (`\r`) and return the
  current weight as an ASCII string. Most bench scales do this.
- **ASCII weight response** — weight returned as a plain number string
  (e.g., `"  12.350\r\n"`). First 12 characters parsed as float.
  Sign character OK (negative = underweight). Status bytes before/after
  the number are ignored if they fall outside the 12-char window.
- **Continuous readability** — must respond to repeated weight commands
  at our poll rate (default 500ms, can be faster). Scale must not require
  a button press to transmit. Some scales have "print on demand" vs
  "continuous output" modes — we need continuous or command-response.

**Configurable (varies by model):**

| Parameter | Setting field | Why it varies |
|-----------|--------------|---------------|
| Baud rate | `baudRate` | 9600 is standard; older scales may use 2400/4800 |
| Data bits | `dataBits` | 8 is standard; some older models use 7 |
| Parity | `parity` | none is standard; some use even |
| Stop bits | `stopBits` | 1 is standard; some use 2 |
| Weight command | `weightCommand` | `W\r` (weight), `H\r` (hold/stable), `S\r` (stable), `P\r` (print) |
| Poll interval | `pollInterval` | 500ms default; faster for scan-and-weigh flow |
| Precision | `precision` | Decimal places (3 = 0.001 lb resolution) |

**Not required:**
- Proprietary drivers — Web Serial API talks to the OS serial port directly
- Proprietary protocol — we use plain ASCII command/response
- Network/Bluetooth — serial only (USB-serial adapters are fine)
- Display — the scale's display is for the operator; we read the port

**Alice's job when evaluating a scale:**
1. Does it have serial output (USB-serial or RS-232)?
2. What command returns the current weight? (check manual for "serial commands" or "RS-232 protocol")
3. What is the response format? (ASCII number string?)
4. What are the serial parameters? (baud, data bits, parity, stop bits)
5. Does it support continuous polling or only print-on-demand?

If the answer to #1 is yes and #2-#4 are documented, the scale works.
Store the parameters in a Setting record (purpose='scale_config') so
each workstation can have its own scale configuration.

### Scale models tested with WC2

WC2 was used with USB scales from Fairbanks, Rice Lake, and Mettler Toledo.
Any scale that responds to ASCII weight commands over serial should work.
The weight command (`W` or `H`) and serial parameters may vary — these are
configurable in `useScale` options.

### Per-item weight check

When an item is scanned:

1. `recordItemScan(expectedWeight)` snapshots the current scale reading
2. Item is placed on scale
3. `itemDelta = currentReading − snapshotReading`
4. `itemDeltaPct = itemDelta / expectedWeight × 100`
5. If delta doesn't match expected ± precision → alert

This catches: wrong item (weight doesn't match), wrong quantity (2 instead
of 1), missing item (no weight change after scan).

### Tare

Tare = box weight. Measured by placing an empty box on the scale and
pressing Tare.

```
tare = scaleReading − productWeight
```

After tare, the deviation formula accounts for the box:
```
deviation = productWeight + tare − scaleReading
```

If tare goes negative (product weight exceeds scale reading when tare is
set), that's a `NEGATIVE_TARE` error — something is wrong.

---

## UI Components

### PackingPanel (`PackingPanel.tsx`)

Three-step panel opened from ManageActionPanel "Ship Order" button.

| Step | What user does | Backend call |
|------|---------------|-------------|
| Pick | Click items to pick (or check all) | `generate_pick_list` |
| Pack | Assign to boxes, set weight, verify | `confirm_pack` |
| Ship | Enter carrier/tracking/date/cost | `ship_order` |

### ScaleBar (inside PackingPanel)

Appears in the Pack step. Shows:
- Status dot (green/red/amber)
- Live weight reading (monospace, large)
- Deviation message when mismatch
- STABLE indicator
- Tare button
- Read button (captures weight into current box)
- Connect/Disconnect

### Print templates (via MarkdownEditor)

| Report | ida | Context |
|--------|-----|---------|
| Pick List | `rpt-pick-list-md` | List — order lines sorted by bin |
| Packing Slip | `rpt-packing-slip-md` | Record — ship-to, items, qty, no prices |

Both use `output_type='merge'` → MarkdownEditor renders with `{{tokens}}`.
Seeded via `seed_template_reports` management command.

---

## WC2 Heritage

WC2 packing was built around two tables:

| WC2 Table | What | WC3 Equivalent |
|-----------|------|----------------|
| `LoadTag` | Box/pallet container | `order.metadata.shipping.packed_lines[]` |
| `LoadItem` | Item packed in a container | Items within packed_lines entries |

WC2 had features WC3 does not yet have:
- **Barcode scanning** — `PKBarCodeItem` matched scans to items
- **Pallet nesting** — boxes inside pallets (`containerType` 1 vs 2)
- **Zone-based shipping cost** — local rate tables by ZIP range
- **UPS WorldShip export** — CSV for ODBC import
- **EDI 945** — headless pack/invoice for warehouse automation

WC3 has features WC2 did not:
- **Web Serial API** — no driver installation, works in browser
- **Markdown templates** — user-editable packing slip and pick list
- **Partial shipment via conversion chain** — handles inventory, commission,
  and parent/child linkage in one path
- **Submit to WC_HQ** — user template improvements flow upstream

---

*Established 2026-08-05 by Bill James and the team.*
