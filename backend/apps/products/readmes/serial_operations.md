# Serial Number Tracking — Operations Guide
**Built:** 2026-07-04 | **Source:** WC2 Srl_* mining (21 files) | **WC2 had no API — built first in WC3**

---

## Overview

Serial numbers track individual units through their lifecycle: received from a vendor, issued to a customer, returned, serviced, scrapped. Every state change logs to SerialLog. Warranty is calculated at issue time. Related records (Q&A, documents, actions) link via refs.

---

## Data Model

```
Serial
  ├── item FK              → which product this unit is
  ├── serial_ida           → the serial number
  ├── model_ida            → model number
  ├── status               → available | issued | pending_sale | referenced | returned | scrapped | in_service
  ├── warranty             → JSON: {days, dt_start, dt_end, date_start, date_end}
  ├── config               → JSON: {cost, dt_received, dt_issued, price, discount}
  ├── site                 → JSON: location/warehouse info
  ├── qr_code              → scannable code
  ├── refs.links           → {vendor_id, po_id, customer_id, invoice_id, order_id}
  └── inventory_layer FK   → cost layer this unit came from

SerialLog (one per event)
  ├── serial FK
  ├── action               → 'received', 'issued', 'returned', 'referenced', 'status_change:X→Y'
  ├── dt                   → epoch ms
  └── config               → JSON context: {vendor_id, invoice_id, reason, ...}
```

---

## Status Lifecycle

```
         receive_serial()
              │
              ▼
        ┌─────────────┐
        │  available   │◄──── return_from_sale()
        └──────┬──────┘
               │
     ┌─────────┼─────────┐
     │         │         │
issue_to_sale()│  reference_existing()
     │         │         │
     ▼         │         ▼
┌─────────┐    │   ┌────────────┐
│  issued  │   │   │ referenced │
└─────────┘    │   └────────────┘
               │
        change_status()
               │
               ▼
     ┌─────────────────┐
     │ scrapped/in_service │
     └─────────────────┘
```

---

## API Endpoints

All require authentication. Base path: `/products/`

| Method | Path | What It Does |
|--------|------|---|
| GET | `/items/{id}/serials/` | List serials for an item (optional `?status=available`) |
| POST | `/items/{id}/serials/receive/` | Receive a serial on PO → status=available |
| POST | `/items/{id}/serials/reference/` | Attach customer-owned serial (service/repair) |
| GET | `/serials/search/` | Search by `?serial=`, `?customer_id=`, or `?vendor_id=` |
| GET | `/serials/warranty/` | Expiring (`?days_ahead=30`) or expired (`?expired=true`) |
| POST | `/serials/{id}/issue/` | Issue to sale → status=issued, warranty starts |
| POST | `/serials/{id}/return/` | Return from sale → status=available |
| GET | `/serials/{id}/history/` | Full SerialLog event list |
| POST | `/serials/{id}/status/` | Generic status change with reason |

---

## Core Operations

### Receive on PO
```python
serial = receive_serial(
    item_id=250, serial_number='WIL-2026-0001',
    vendor_id=42, po_id=100, model_number='A1010',
    cost=Decimal('4.80'), warranty_days=365
)
# → status='available', refs.links.vendor_id=42, refs.links.po_id=100
# → SerialLog: action='received', config={vendor_id, po_id, cost}
```

### Issue to Sale
```python
serial = issue_to_sale(
    serial_id=serial.id,
    customer_id=55, invoice_id=200, price=Decimal('12.99')
)
# → status='issued'
# → warranty.dt_start = now, warranty.dt_end = now + 365 days
# → refs.links.customer_id=55, refs.links.invoice_id=200
# → SerialLog: action='issued', config={customer_id, invoice_id, price}
```

### Return from Sale
```python
serial = return_from_sale(serial_id=serial.id, reason='Defective')
# → status='available'
# → customer/invoice/order refs cleared
# → warranty dates cleared (days definition preserved)
# → SerialLog: action='returned', config={reason, from_invoice_id}
```

### Reference Existing (customer-owned)
```python
serial = reference_existing(
    item_id=250, serial_number='CUST-SN-999',
    customer_id=55, document_type='workorder', document_id=300,
    remaining_warranty_days=90
)
# → status='referenced', warranty starts with 90 days remaining
# → SerialLog: action='referenced', config={customer_id, document_type, document_id}
```

### Search
```python
# By serial number
results = search_by_serial_number('WIL-2026')

# All serials currently with a customer
results = search_by_customer(customer_id=55)

# All serials from a vendor
results = search_by_vendor(vendor_id=42)
```

### Warranty Monitoring
```python
# Expiring within 30 days
expiring = warranty_due(days_ahead=30)

# Already expired but still issued
expired = warranty_expired()
```

---

## DataBrowser Integration

### Spawn Links
When viewing a Serial in DataBrowser, the spawn bar shows:

```
Related: [History ↗] [Q&A ↗] [Documents ↗] [Actions ↗] [Customer ↗] [Vendor ↗]
```

Each button opens a new DataBrowser window filtered to related records:
- **History** → SerialLog where serial_id = this serial
- **Q&A** → QuestionAnswer linked via refs.links
- **Documents** → Document linked via refs.links
- **Actions** → Action linked via refs.links
- **Customer** → Contact who currently owns this serial
- **Vendor** → Contact who supplied this serial

### Item → Serials
When viewing an Item, spawn links include `[Serials ↗]` — opens all serials for that item.

---

## Warranty Model

Warranty is tracked at the serial level, not the item level:

| Field | When Set | Value |
|---|---|---|
| `warranty.days` | At receive (from item default or manual) | e.g., 365 |
| `warranty.dt_start` | At issue (sale to customer) | epoch ms of sale date |
| `warranty.dt_end` | At issue | dt_start + (days × 86400000) |
| `warranty.date_start` | At issue | ISO date string |
| `warranty.date_end` | At issue | ISO date string |

On return: active dates cleared, `days` preserved. On re-issue: dates recalculated fresh.

For `reference_existing` (customer-owned units entering for service): warranty starts immediately with `remaining_warranty_days` as the window.

---

## Relationship Linkage (refs.links)

All relationships stored in `refs.links` — same pattern as everywhere in WC3:

```json
{
  "links": {
    "vendor_id": 42,
    "po_id": 100,
    "po_line_id": 201,
    "customer_id": 55,
    "invoice_id": 200,
    "invoice_line_id": 301,
    "order_id": 150
  }
}
```

Queryable via Django JSON lookups: `Serial.objects.filter(refs__links__customer_id=55)`

---

## What WC2 Had vs WC3

| WC2 | WC3 |
|---|---|
| 21 Srl_* methods, no API | 12 services + 9 API endpoints |
| Implicit payment-to-invoice via overloaded invoiceNum field | Explicit refs.links with named FKs |
| invoiceNum used as workflow sentinel (-3, -5) | Clean status field with named states |
| Floor-plan financing fields | Not ported (niche dealer feature) |
| WCapi_SerialNum = empty stub | Full REST API built first in WC3 |

---

## Files

| File | Purpose |
|------|---------|
| `apps/products/models/serial.py` | Serial + SerialLog models |
| `apps/products/services/serial_services.py` | 12 lifecycle operations |
| `apps/products/views/serial_views.py` | 9 API endpoints |
| `apps/products/urls.py` | URL routing |
