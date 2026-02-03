# Contact Model

## Overview

The Contact model manages person/entity records in the system. Contacts can be associated with customers, vendors, employees, manufacturers, and more. The `ContactDetail` component provides a comprehensive view/edit interface with inline communication record management.

## Files

| File | Purpose |
|------|---------|
| `pages/ContactDetail.tsx` | Main detail/edit form component |
| `pages/ContactList.tsx` | List view with filtering |
| `services/contactApi.ts` | API service functions |
| `types/contactType.ts` | TypeScript interfaces |
| `utils/contactSchema.ts` | Zod validation schemas |

---

## ContactDetail Component

### Location
`src/apps/core/models/contact/pages/ContactDetail.tsx`

### Props

```typescript
interface ContactAddProps {
  modeProp?: "add" | "edit" | "view";  // Operation mode
  dataProp?: any;                       // Contact data for edit/view
  hideBreadcrumb?: boolean;             // Hide page breadcrumb
  onSaved?: () => void;                 // Callback after save
  inline?: boolean;                     // Render inline (no card wrapper)
  onCancelInline?: () => void;          // Cancel callback for inline mode
}
```

### Modes

| Mode | Description |
|------|-------------|
| `add` | Create new contact with password fields |
| `edit` | Update existing contact (no password fields) |
| `view` | Read-only display of contact data |

---

## Features

### 1. Contact Fields

The component manages these contact fields:

**Identity**
- `name_prefix`, `name_first`, `name_middle`, `name_last`, `name_suffix`
- `email` (login email)
- `company`, `title`, `department`

**Credentials** (add mode only)
- `password`, `cnf_password`

**Reference IDs**
- `customer_id`, `rep_id`, `vendor_id`
- `employee_id`, `manufacturer_id`, `other_id`

**Status**
- `role` (user, admin, manager, staff, guest)
- `is_active`, `is_staff`

### 2. Communication Tables

The component includes four inline-editable communication tables:

| Table | Icon | Fields |
|-------|------|--------|
| **Emails** | 📧 | id, address, name, type, is_primary |
| **Phones** | 📞 | id, number, name, type, is_primary |
| **Addresses** | 📍 | id, name, address_line1, city, state, postal_code |
| **Domains** | 🌐 | id, domain, name, is_primary |

Each table supports:
- ✅ Collapsible sections
- ✅ Add new records
- ✅ Inline editing
- ✅ Delete with confirmation
- ✅ Save to API

### 3. Admin Field Controls

Administrators can control field visibility and editability per-field:

- **Show/Hide Toggle** - Control which fields are visible to non-admin users
- **Read-Only Toggle** - Make fields read-only for non-admin users
- **Save/Reset** - Persist or revert configuration changes

Located at the bottom of the form (admin only).

---

## Component Architecture

### Generic CommunicationTable

```typescript
interface CommunicationTableProps<T> {
  title: string;
  icon: React.ReactNode;
  data: T[];
  columns: { key: keyof T; label: string; render?: (item: T) => React.ReactNode }[];
  onAdd: () => void;
  onEdit: (item: T) => void;
  onDelete: (item: T) => void;
  onSave: (item: T) => void;
  editingItem: T | null;
  onEditChange: (field: keyof T, value: any) => void;
  onCancelEdit: () => void;
  disabled?: boolean;
}
```

This generic component is reused for all four communication types.

### State Management

```typescript
// Communication records
const [emails, setEmails] = useState<EmailRecord[]>([]);
const [phones, setPhones] = useState<PhoneRecord[]>([]);
const [locations, setLocations] = useState<LocationRecord[]>([]);
const [domains, setDomains] = useState<DomainRecord[]>([]);

// Editing state (one at a time per type)
const [editingEmail, setEditingEmail] = useState<EmailRecord | null>(null);
const [editingPhone, setEditingPhone] = useState<PhoneRecord | null>(null);
const [editingLocation, setEditingLocation] = useState<LocationRecord | null>(null);
const [editingDomain, setEditingDomain] = useState<DomainRecord | null>(null);
```

### Form Validation

Uses Zod schemas with React Hook Form:

- `contactSchema` - For add mode (includes password validation)
- `updateContactSchema` - For edit mode (no password fields)

---

## API Integration

### Contact API

```typescript
createContact(payload: CreateContactRequest): Promise<ContactApiTask>
updateContact(payload: UpdateContactRequest): Promise<ContactApiTask>
```

### Communication APIs

Each communication type has its own API service:

```typescript
// Email
createEmail(payload: CreateEmailRequest): Promise<EmailApiTask>
updateEmail(payload: UpdateEmailRequest): Promise<EmailApiTask>
deleteEmail(model_name: string, id: number): Promise<any>

// Phone
createPhone(payload: CreatePhoneRequest): Promise<PhoneApiTask>
updatePhone(payload: UpdatePhoneRequest): Promise<PhoneApiTask>
deletePhone(id: number): Promise<any>

// Location
createLocation(payload: CreateLocationRequest): Promise<LocationApiTask>
updateLocation(payload: UpdateLocationRequest): Promise<LocationApiTask>
deleteLocation(id: number): Promise<any>

// Domain
createDomain(payload: CreateDomainRequest): Promise<DomainApiTask>
updateDomain(payload: UpdateDomainRequest): Promise<DomainApiTask>
deleteDomain(id: any): Promise<any>
```

---

## Data Flow

### Loading Contact Data

1. Contact data passed via `dataProp` or `location.state`
2. `useEffect` normalizes data and calls `reset()` on form
3. Communication records extracted from `data.refs.links`
4. Each communication array populates its respective state

### Saving Contact

1. Form submission triggers `onSubmit`
2. `mapRefsFormToApi()` transforms refs for API format
3. `createContact` or `updateContact` called based on mode
4. Success toast displayed, `onSaved` callback invoked

### Saving Communications

1. User clicks Add/Edit on communication table
2. `editingItem` state populated
3. Row switches to input mode
4. User edits and clicks Save
5. API called (`create*` for id=0, `update*` for existing)
6. Local state updated with response
7. `editingItem` cleared

---

## Hooks Used

| Hook | Purpose |
|------|---------|
| `useForm` | React Hook Form for contact fields |
| `useDetailFieldAccess` | Admin field visibility/readonly controls |
| `useDispatch` | Redux dispatch for toasts |
| `useLocation` | React Router state access |
| `useState` | Communication records and editing state |
| `useCallback` | Memoized handlers |
| `useMemo` | Memoized field names array |
| `useEffect` | Data loading and normalization |

---

## Related Components

- `ComponentCard` - Card wrapper
- `PageBreadcrumb` - Navigation breadcrumb
- `Input` / `DropDown` / `Checkbox` - Form inputs
- `Label` - Form field labels

---

## Usage Examples

### Add Mode (Page)
```tsx
<ContactDetail />
// or via route with state: { mode: 'add' }
```

### Edit Mode (Page)
```tsx
<ContactDetail modeProp="edit" dataProp={contactData} />
// or via route with state: { mode: 'edit', data: contactData }
```

### Inline Edit
```tsx
<ContactDetail
  modeProp="edit"
  dataProp={contactData}
  inline={true}
  hideBreadcrumb={true}
  onSaved={() => refetchContacts()}
  onCancelInline={() => setShowEdit(false)}
/>
```

### View Mode
```tsx
<ContactDetail 
  modeProp="view" 
  dataProp={contactData}
  hideBreadcrumb={true}
/>
```
