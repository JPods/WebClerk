# ItemDetail Component

Enterprise-grade item detail page following UX research best practices for data-dense applications.

## Layout Philosophy

Based on Nielsen Norman Group enterprise form guidelines and Baymard Institute density studies:

- **Two-column label/value layout** for scannability
- **Logical field groupings** in collapsible sections
- **Consistent label widths** for vertical alignment
- **Compact but readable spacing**
- **Visual hierarchy** with section headers and icons

## Page Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  Header: Item Name, SKU, ID | Status Badges (Stock, Active)    │
├─────────────────────────────────────────────────────────────────┤
│  1. Basic Information (expanded)                                │
│     Row 1: name | sku | ida | uom                              │
│     Row 2: description (full width)                            │
│     Row 3: kind | specification_id                             │
├─────────────────────────────────────────────────────────────────┤
│  2. Pricing & Cost with Image (side-by-side)                   │
│  ┌─────────────────────────────┬───────────────────────────┐   │
│  │  Pricing (60%)              │  Product Image (40%)      │   │
│  │  ├─ .base: $XX.XX          │  ┌───────────────────┐    │   │
│  │  ├─ .retail: $XX.XX        │  │   [Hero Image]     │    │   │
│  │  ├─ .wholesale: $XX.XX     │  └───────────────────┘    │   │
│  │  └─ .sale: $XX.XX          │  Gallery: [+]             │   │
│  ├─────────────────────────────│  [thumb] [thumb] ...      │   │
│  │  Cost (collapsed)           │                           │   │
│  │  ├─ .average: $XX.XX       │  .images.primary: path    │   │
│  │  ├─ .last: $XX.XX          │                           │   │
│  │  └─ .standard: $XX.XX      │                           │   │
│  └─────────────────────────────┴───────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  4. Inventory Status (expanded, horizontal grid)               │
│  On Hand | Allocated | Available | On SO | On PO | On WO | ... │
├─────────────────────────────────────────────────────────────────┤
│  5. Bill of Materials (collapsed)                              │
│  6. Linkages Panel (collapsed)                                 │
│  7. Actions Panel (collapsed)                                  │
│  8. Comments Panel (collapsed)                                 │
│  9. Flags & Settings (collapsed)                               │
│  10. GL Accounts (collapsed)                                   │
│  11. Tax Information (collapsed)                               │
│  12. Metadata Panel (collapsed, admin only)                    │
│  13. Prefs Panel (collapsed)                                   │
│  14. Refs Panel (collapsed, admin only)                        │
│  15. Record Information (collapsed)                            │
│  16. Raw Data Panel (collapsed, admin only)                    │
└─────────────────────────────────────────────────────────────────┘
```

## Data Model Alignment

Maps to Django `Item` model in `webClerk3/apps/products/models/item.py`:

### Core Fields
| Field | Type | Description |
|-------|------|-------------|
| `id` | number | Primary key |
| `name` | string | Item name (160 chars) |
| `sku` | string | Stock keeping unit (80 chars, case-insensitive unique) |
| `kind` | string | `physical` \| `service` \| `bundle` |
| `uom` | string | Unit of measure (EA, HR, KG, etc.) |
| `description` | string | Full description |
| `specification_id` | number | Link to specification record |

### JSON Fields

#### `price` (JSONField)
```typescript
interface PriceData {
  base?: number;      // Primary sell price
  msrp?: number;      // Manufacturer suggested retail
  tiers?: Array<{level: string; price: number}>;
  qty_breaks?: Array<{min_qty: number; unit_price: number}>;
  currency?: string;  // ISO 3-letter code
  history?: Array<{dt_utc: string; field: string; old: any; new: any}>;
}
```

#### `cost` (JSONField)
```typescript
interface CostData {
  standard?: number;  // Standard cost (GL alignment)
  last?: number;      // Last receipt unit cost
  avg?: number;       // Moving average cost
  landed?: number;    // Landed cost with freight/duties
  currency?: string;
  components?: Record<string, number>;
  breaks?: Array<{min_qty: number; unit_cost: number}>;
  history?: Array<{...}>;
}
```

#### `quantity` (JSONField)
```typescript
interface QuantityData {
  on_hand?: number;
  allocated?: number;
  available?: number;  // Computed: on_hand - allocated
  on_so?: number;      // On sales orders
  on_po?: number;      // On purchase orders
  on_p?: number;       // On proposals
  on_wo?: number;      // On work orders
  on_reciept?: number; // In receiving
  on_in?: number;      // In inspection
}
```

#### `metadata.images` (in BaseModel metadata envelope)
```typescript
interface ImageData {
  primary: string;    // Hero image path
  gallery: string[];  // Additional view paths
  thumbnail: string;  // List/grid display path
}
```

## Component Architecture

### Helper Components

| Component | Purpose |
|-----------|---------|
| `FieldRow` | Horizontal label-input layout for edit mode |
| `Section` | Collapsible section with icon for edit forms |
| `DataField` | Horizontal label-value display (monospace labels) |
| `DataFieldGrid` | Responsive grid wrapper (2, 3, or 4 columns) |
| `DataSection` | Collapsible section for view mode |
| `InventoryGrid` | Horizontal quantity display with labels on top |
| `ImagePanel` | Image display/management with gallery support |
| `QuantityStatusBadge` | Stock level indicator badge |

### Field Naming Convention

Labels use exact field names in lowercase:
- Top-level fields: `name`, `sku`, `uom`
- Nested properties: `.base`, `.retail`, `.average` (dot prefix)
- Shows data path for debugging: `.images.primary: path/to/image.jpg`

## Modes

| Mode | Description |
|------|-------------|
| `view` | Read-only display with collapsible sections |
| `edit` | Form with validation, updates existing record |
| `add` | Form for creating new item |

## ID Resolution

Supports multiple ID sources (priority order):
1. Direct `id`/`recordId` prop
2. URL path params (`/item/22`)
3. Search params (`?id=22`)
4. Route state (`navigate({ state: { data: { id: 22 } } })`)
5. `dataProp?.id`

## Image Management

The `ImagePanel` component provides:

- **Primary image display** with placeholder fallback
- **Gallery thumbnails** (click to set as primary)
- **Add images via URL** (admin only)
- **Remove images** (admin only)
- **Auto-save** to `metadata.images` via API

Image paths can be:
- Relative: `products/sku-123/main.jpg` → `/images/products/sku-123/main.jpg`
- Absolute URLs: `https://cdn.example.com/image.jpg`

## Field Access Control

Uses `useDetailFieldAccess` hook for role-based visibility:

```typescript
const { isAdmin, isFieldVisible, isFieldReadOnly } = useDetailFieldAccess("item", fieldNames);

// Admin-only sections
{isAdmin && <MetadataPanel ... />}
{isAdmin && <RefsPanel ... />}
{isAdmin && <RawDataPanel ... />}
```

## API Integration

| Function | Endpoint | Purpose |
|----------|----------|---------|
| `getRecord("item", id)` | `/wcapi/get/` | Fetch single item |
| `saveRecord("item", payload)` | `/wcapi/save/` | Create/update item |
| `createItem(data)` | Model-specific | Create new item |
| `updateItem(data)` | Model-specific | Update existing item |

## Panel Components

Reusable panels from `@/apps/common/components/panels`:

| Panel | Purpose |
|-------|---------|
| `CommentsPanel` | Public/process/partner comments |
| `MetadataPanel` | Universal metadata envelope |
| `RefsPanel` | Keywords, tags, links |
| `PrefsPanel` | User preferences |
| `ActionsPanel` | Next action tracking |
| `LinkagesPanel` | Cross-model relationships |
| `RawDataPanel` | JSON viewer for debugging |

## Styling

- Uses Tailwind CSS utility classes
- Dark mode support via `dark:` variants
- Responsive: mobile-first with `sm:`, `lg:` breakpoints
- Consistent color palette: slate grays, blue highlights

## Usage

```tsx
// View mode with URL-based ID
<ItemDetail modeProp="view" />

// Edit mode with passed data
<ItemDetail modeProp="edit" dataProp={itemData} />

// Add mode
<ItemDetail modeProp="add" onSaved={() => navigate('/items')} />

// Inline mode (in modal/drawer)
<ItemDetail 
  modeProp="edit" 
  dataProp={item} 
  inline={true}
  onCancelInline={() => setShowModal(false)}
  onSaved={handleSaved}
/>
```

## Related Files

- `itemSchema.ts` - Zod validation schema
- `itemType.ts` - TypeScript interfaces
- `itemApi.ts` - API service functions
- `BOMSection.tsx` - Bill of Materials component
- `item.py` - Django model (backend)
