# QuickQuote Feature Specification

## Overview

QuickQuote is a streamlined interface for rapidly creating quotes by searching and organizing items before posting them to an order. It provides a focused workflow for sales representatives to build quotes efficiently.

## User Stories

1. **As a sales rep**, I want to quickly search for products while on a call with a customer, so I can build a quote in real-time.
2. **As a sales rep**, I want to see product availability and pricing instantly, so I can give accurate information to customers.
3. **As a sales rep**, I want to organize items in a scratch pad before committing them to an order, so I can make changes easily.
4. **As a sales rep**, I want to post multiple items to an existing or new order with one click, so I can work efficiently.

## Features

### 1. QuickQuote Window

A standalone window/modal that can be:
- Opened from any transaction detail page
- Launched from the main navigation
- Kept open alongside other work (floating window mode)

### 2. Item Search Panel

**Search Capabilities:**
- Full-text search across item codes, descriptions, and attributes
- Category/group filtering
- Recently used items list
- Favorites/frequently ordered items
- Barcode/SKU scanning support

**Search Results Display:**
- Item code and description
- Current pricing (customer-specific if available)
- Stock availability indicators
- Quick-add button per item
- Thumbnail image (if available)

### 3. Quote Builder (Scratch Pad)

**Features:**
- Drag-and-drop reordering
- Inline quantity editing
- Price override capability
- Line notes
- Running subtotal display
- Item grouping/categorization

**Line Item Fields:**
- Item Code
- Description
- Quantity
- Unit of Measure
- Unit Price
- Extended Price
- Notes
- Availability status

### 4. Customer Context

**Customer Selection:**
- Search and select customer
- Shows customer-specific pricing
- Displays customer credit status
- Shows recent order history

**Customer Info Panel:**
- Company name and contact
- Shipping preferences
- Payment terms
- Special pricing agreements

### 5. Post to Order

**Options:**
- Create new Sales Order
- Create new Quote
- Add to existing open order/quote
- Save as template for future use

**Post Actions:**
- Validate all items have sufficient stock
- Apply customer-specific pricing
- Generate order number
- Open new order in detail view

## UI/UX Design

### Layout (3-Panel Design)

```
+------------------------------------------+
|  QuickQuote - [Customer: ABC Corp]  [X]  |
+------------------------------------------+
|  [Search Panel]  |  [Quote Builder]      |
|                  |                       |
|  Search: [___]   |  Items to Quote:      |
|                  |                       |
|  Results:        |  +---------------+    |
|  □ ITEM-001      |  | ITEM-001  x5  |    |
|  □ ITEM-002      |  | ITEM-003  x2  |    |
|  □ ITEM-003      |  +---------------+    |
|                  |                       |
|  Recent Items:   |  Subtotal: $1,250.00  |
|  • ITEM-005      |                       |
|  • ITEM-007      |  [Clear] [Post Order] |
+------------------------------------------+
```

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+F` | Focus search |
| `Enter` | Add selected item |
| `Ctrl+Q` | Change quantity |
| `Delete` | Remove selected line |
| `Ctrl+Enter` | Post to order |
| `Escape` | Close window |

## Technical Requirements

### Components to Create

1. **QuickQuoteWindow** - Main container component
2. **ItemSearchPanel** - Search and results display
3. **QuoteBuilder** - Scratch pad for building quote
4. **CustomerSelector** - Customer search and display
5. **QuickQuoteItem** - Individual line item component

### State Management

```typescript
interface QuickQuoteState {
  customerId: number | null;
  customerName: string;
  items: QuickQuoteItem[];
  searchQuery: string;
  searchResults: SearchResult[];
  recentItems: Item[];
  isLoading: boolean;
  selectedItemIndex: number | null;
}

interface QuickQuoteItem {
  itemId: number;
  itemCode: string;
  description: string;
  quantity: number;
  unitMeasure: string;
  unitPrice: number;
  notes: string;
  availability: 'in-stock' | 'low-stock' | 'out-of-stock' | 'special-order';
}
```

### API Endpoints Required

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/items/search` | GET | Search items |
| `/api/items/recent` | GET | Get recently used items |
| `/api/customers/{id}/pricing` | GET | Get customer-specific pricing |
| `/api/orders` | POST | Create new order from quote |
| `/api/orders/{id}/lines` | POST | Add lines to existing order |

### Integration Points

1. **Item Catalog** - Real-time search and availability
2. **Customer Records** - Pricing and credit status
3. **Inventory System** - Stock availability
4. **Order Processing** - Create/update orders

## Implementation Phases

### Phase 1: Core Functionality
- [ ] QuickQuoteWindow component
- [ ] Item search with basic filters
- [ ] Quote builder with add/remove/reorder
- [ ] Post to new order

### Phase 2: Enhanced Features
- [ ] Customer selection and pricing
- [ ] Recent/favorite items
- [ ] Availability indicators
- [ ] Keyboard shortcuts

### Phase 3: Advanced Features
- [ ] Barcode scanning
- [ ] Save as template
- [ ] Add to existing order
- [ ] Multi-window support

## Acceptance Criteria

1. User can search and find items in under 2 seconds
2. User can add items with single click or keyboard
3. User can reorder items via drag-and-drop
4. User can see running total update in real-time
5. User can post to order in 3 clicks or less
6. Window can be kept open while navigating app
7. Customer-specific pricing is reflected automatically

## Related Components

- [OrderDetail](../models/order/pages/OrderDetail.tsx)
- [OrderItemSearch](../models/order/components/OrderItemSearch.tsx)
- [TransactionDetailBase](../components/TransactionDetailBase.tsx)

## Notes

- Consider mobile responsiveness for tablet users
- Performance critical - cache search results
- Consider offline capability for trade shows
- Integrate with existing item search component where possible
