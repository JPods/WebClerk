# Labels — Printing and Barcodes

## Overview

WebClerk does **not** include a built-in label designer. Labels are a specialized
domain — thermal printers (Zebra, DYMO, Brother) have their own SDKs, driver
languages, and size constraints. WC3 provides the **data and export**; dedicated
label software handles the printing.

## How It Works

1. **Report record** with `output_type: 'label'` defines the field mapping
2. **WC3 exports** structured data (ZPL, CSV, or JSON) to a watched folder or API
3. **Label software** picks up the file and prints

## Delivery Methods

| Method | How | Best for |
|--------|-----|----------|
| **Folder watch** | WC3 drops files in `wc_labels/pending/`, label software watches | Universal — any printer, any OS |
| **Zebra raw TCP** | Send ZPL directly to printer IP on port 9100 | High-volume warehouse, shipping |
| **DYMO Connect** | REST API on localhost:41951 | Small office, product labels |
| **PDF fallback** | WC3 generates label-sized PDF (2"×4", 4"×6") | Any printer, no special software |

## Folder Structure

```
wc_labels/
  pending/      ← WC3 drops ZPL/CSV files here
  processed/    ← label software moves after printing
  errors/       ← failed prints
```

Alice monitors `processed/` vs `pending/` for stuck jobs.

## Recommended Label Printers

| Printer | Protocol | Price range | Notes |
|---------|----------|-------------|-------|
| **Zebra ZD421** | ZPL via TCP | $300–500 | Industry standard, direct network print |
| **DYMO LabelWriter 550** | DYMO Connect SDK | $100–150 | Small office, USB |
| **Brother QL-820NWB** | b-PAC SDK, network | $150–250 | WiFi + Bluetooth, retail |
| **Rollo X1038** | ZPL compatible | $200–300 | Shipping labels, 4"×6" |

## Barcodes and QR Codes

WC3 can generate barcodes and QR codes server-side for any label or document.

### Recommended Libraries (Python, server-side)

| Library | What it does | Install |
|---------|-------------|---------|
| **python-barcode** | Code128, EAN, UPC, ISBN — SVG or PNG output | `pip install python-barcode` |
| **qrcode** | QR code generation with PIL/Pillow | `pip install qrcode[pil]` |
| **segno** | Lightweight QR/Micro QR — no Pillow dependency | `pip install segno` |

### Recommended Libraries (JavaScript, client-side)

| Library | What it does | Install |
|---------|-------------|---------|
| **bwip-js** | 100+ barcode types, runs in browser and Node | `npm install bwip-js` |
| **qrcode.react** | QR code React component | `npm install qrcode.react` |
| **JsBarcode** | Code128, EAN, UPC — renders to SVG/Canvas | `npm install jsbarcode` |

### Free Online Tools (for one-off needs)

- **barcode.tec-it.com** — generate any barcode type, download PNG/SVG
- **qr-code-generator.com** — QR codes with logo embedding
- **labelary.com** — ZPL preview and testing (paste ZPL, see the label)

### Implementation Path

1. **Server-side** (recommended): `python-barcode` + `qrcode` generate images,
   stored in `media/barcodes/`, referenced by item.ida or any field
2. **Client-side**: `bwip-js` or `JsBarcode` render inline in print layouts —
   add a `barcode` section type to PrintLayout
3. **ZPL native**: Zebra printers render barcodes from ZPL commands directly —
   no image generation needed, just `^BC` (Code128) or `^BQ` (QR) commands

## WC3 Integration Points

- **Item records**: `item.ida` → barcode, `item.config.upc` → UPC/EAN
- **Order/Invoice**: `ida` → barcode for scanning at pack/ship
- **Shipping labels**: ship-to address + tracking barcode from carrier API
- **Bin labels**: `item.config.bin_location` → barcode for warehouse scanning
- **Price tags**: item name + price + barcode on small label stock

## What WC3 Does NOT Do

- Visual label designer (use Zebra Designer, DYMO Connect, Bartender)
- Thermal printer driver management
- Print queue management for label printers
- WYSIWYG barcode positioning (the label software handles layout)

## Setting Up

1. Create a Report record: `output_type: 'label'`, `category: 'label'`
2. Configure `config.label_format`: `'zpl'`, `'csv'`, or `'json'`
3. Configure `config.label_fields`: array of field mappings
4. Set `config.delivery`: `'folder'` (path) or `'tcp'` (printer IP:port)
5. Double-click the report in ReportsDialog → exports/prints

## Alice's Role

- Tracks which label formats each customer/installation uses
- Monitors folder watch for stuck jobs (pending > 5 min without processing)
- Recommends barcode type based on use case (Code128 for internal, UPC for retail)
- Flags items missing barcode data that have label reports configured
