# PartySelector Component

A unified, reusable dropdown component for selecting **Customers**, **Vendors**, and **Manufacturers** across all transaction types.

## Overview

The `PartySelector` provides a consistent interface for party selection throughout the application. It supports:
- Type-ahead search with debounced API calls
- Recent selections stored in localStorage
- Different configurations per party type (icons, labels, placeholders)
- Edit and view modes integration
- Validation error display

## Components

### Base Component

```tsx
import { PartySelector } from '@/apps/transactions/components';

<PartySelector
  partyType="customer"
  value={customerId}
  onChange={(party) => setCustomerId(party?.id ?? null)}
  label="Customer"
  required
/>
```

### Type-Specific Convenience Components

```tsx
import { 
  CustomerSelector, 
  VendorSelector, 
  ManufacturerSelector 
} from '@/apps/transactions/components';

// Customer (for sales transactions)
<CustomerSelector
  value={customerId}
  onChange={(party) => handleChange('customer_id', party?.id)}
  label="Customer"
  required
/>

// Vendor (for purchase transactions)
<VendorSelector
  value={vendorId}
  onChange={(party) => handleChange('vendor_id', party?.id)}
  label="Vendor"
/>

// Manufacturer
<ManufacturerSelector
  value={manufacturerId}
  onChange={(party) => handleChange('manufacturer_id', party?.id)}
  label="Manufacturer"
/>
```

### Transaction-Aware Selector

Automatically selects the correct party type based on transaction category:

```tsx
import { TransactionPartySelector } from '@/apps/transactions/components';

// For sales transactions (proposal, order, invoice) → selects Customer
// For purchase transactions (purchase_order, work_order) → selects Vendor
<TransactionPartySelector
  transactionType="sales"  // or "purchase"
  value={partyId}
  onChange={(party) => handleChange(party)}
/>
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `partyType` | `'customer' \| 'vendor' \| 'manufacturer'` | required | Type of party to select |
| `value` | `number \| null` | `null` | Currently selected party ID |
| `onChange` | `(party: SelectedParty \| null) => void` | required | Callback when selection changes |
| `label` | `string` | - | Label displayed above the selector |
| `placeholder` | `string` | Auto-generated | Placeholder text |
| `required` | `boolean` | `false` | Shows required indicator |
| `disabled` | `boolean` | `false` | Disables the selector |
| `error` | `string` | - | Error message to display |
| `size` | `'sm' \| 'md' \| 'lg'` | `'md'` | Size variant |
| `className` | `string` | `''` | Additional CSS classes |
| `showRecent` | `boolean` | `true` | Show recent selections |
| `maxRecent` | `number` | `5` | Maximum recent items |

## Types

### SelectedParty

The object returned via `onChange`:

```typescript
interface SelectedParty {
  id: number;       // Organization ID
  name: string;     // Display name
  ida?: string;     // Display ID (optional)
  type: PartyType;  // 'customer' | 'vendor' | 'manufacturer'
}
```

## Usage Examples

### In a Form

```tsx
const [formData, setFormData] = useState({
  customer_id: null as number | null,
  // ...
});

<CustomerSelector
  value={formData.customer_id}
  onChange={(party) => setFormData(prev => ({
    ...prev,
    customer_id: party?.id ?? null
  }))}
  label="Customer"
  required
  error={errors.customer_id}
/>
```

### In TransactionDetailBase

The component is already integrated into `TransactionDetailBase`. When in edit mode, the Parties section shows the selectors:

```tsx
// From TransactionDetailBase DefaultSummary
{isEditing ? (
  <div className="space-y-4">
    <CustomerSelector
      value={data.customer_id}
      onChange={(party) => onChange('customer_id', party?.id ?? null)}
      label="Customer"
    />
    <VendorSelector
      value={data.vendor_id}
      onChange={(party) => onChange('vendor_id', party?.id ?? null)}
      label="Vendor"
    />
    <ManufacturerSelector
      value={data.manufacturer_id}
      onChange={(party) => onChange('manufacturer_id', party?.id ?? null)}
      label="Manufacturer"
    />
  </div>
) : (
  // View mode - shows static text
)}
```

### Conditional Party Type

For transactions that could be either sales or purchase:

```tsx
const isSalesTransaction = ['proposal', 'order', 'invoice'].includes(transactionType);

{isSalesTransaction ? (
  <CustomerSelector value={data.customer_id} onChange={...} label="Customer" required />
) : (
  <VendorSelector value={data.vendor_id} onChange={...} label="Vendor" required />
)}
```

## Features

### Search

- **Debounced**: 300ms delay before API call
- **API Integration**: Uses `customerApi`, `vendorApi`, `manufacturerApi` from `@/apps/orgs/services/orgApi`
- **Active Only**: Searches only active organizations

### Recent Selections

- Stored in `localStorage` per party type
- Key format: `partySelector_recent_{partyType}`
- Maximum 5 items by default (configurable via `maxRecent`)
- Persists across sessions

### Keyboard Support

- Click to open dropdown
- Type to search
- Click result to select
- Click X to clear selection

## Styling

The component uses Tailwind CSS and supports:
- Dark mode via `dark:` prefixes
- Three size variants (`sm`, `md`, `lg`)
- Error state styling (red border)
- Disabled state styling (opacity reduction)
- Focus ring for accessibility

## Dependencies

- `@/apps/orgs/services/orgApi` - API functions
- `@/apps/orgs/types/orgTypes` - Organization type definitions
- `react-icons/fa` - Icons (FaSearch, FaUser, FaTruck, FaIndustry, etc.)

## Transaction Type Mapping

| Transaction | Primary Party | Secondary Party |
|-------------|---------------|-----------------|
| Proposal | Customer | - |
| Sales Order | Customer | Vendor (drop-ship) |
| Invoice | Customer | - |
| Purchase Order | Vendor | Manufacturer |
| Work Order | Vendor | - |

## Future Enhancements

- [ ] Create new party inline (modal)
- [ ] Multi-select support
- [ ] Keyboard navigation (arrow keys)
- [ ] Contact quick-view on hover
- [ ] Filter by status/category
