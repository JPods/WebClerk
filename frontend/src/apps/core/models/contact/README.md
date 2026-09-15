# Contact Model

## Overview

The Contact model manages person/entity records in the system. Contacts can be associated with customers, vendors, employees, manufacturers, and more. The `ContactDetail` component provides a comprehensive view/edit interface following enterprise UX best practices with collapsible sections, reusable panel components, and an integrated layout selector for team design discussions.

## Files

| File | Purpose |
|------|---------|
| `pages/ContactDetail.tsx` | Main detail/edit form - Enterprise Best Practices layout |
| `pages/ContactDetailStart.tsx` | Alternative with layout selector switcher |
| `pages/ContactDetailTwoColumn.tsx` | Two-column card-based layout |
| `pages/ContactDetailHorizontal.tsx` | Horizontal 2-column layout |
| `pages/ContactDetailDense.tsx` | Ultra-compact inline layout |
| `pages/ContactList.tsx` | List view with filtering |
| `services/contactApi.ts` | API service functions |
| `types/contactType.ts` | TypeScript interfaces |
| `utils/contactSchema.ts` | Zod validation schemas |

---

## ContactDetail Component

### Location
`src/apps/core/models/contact/pages/ContactDetail.tsx`

### Design Philosophy

Based on UX research from Nielsen Norman Group, Luke Wroblewski, and Baymard Institute:
- **Two-column layout** with labels on the left for scannability
- **Collapsible sections** for logical field groupings
- **Consistent label widths** for vertical alignment
- **Visual hierarchy** with section headers and icons
- **Keyboard navigation** support

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
| `view` | Read-only display - Edit button toggles to edit mode |

---

## Features

### 1. Section Layout

The component organizes fields into collapsible sections:

| # | Section | Icon | Default | Contents |
|---|---------|------|---------|----------|
| 1 | Personal Information | 📇 | Expanded | Names (first, last, middle, prefix, suffix), Attention |
| 2 | Company Information | 🏢 | Expanded | Company, Title, Department |
| 3 | Communications | 📧 | Expanded | CommunicationsPanel (emails, phones, addresses, domains) |
| 4 | Actions | ⚡ | Expanded | ActionsPanel |
| 5 | Comments | 💬 | Collapsed | CommentsPanel |
| 6 | Metadata | 📋 | Collapsed | MetadataPanel |
| 7 | Preferences | ⚙️ | Collapsed | PrefsPanel |
| 8 | References | 🔗 | Collapsed | RefsPanel |
| 9 | Raw Data | 🗃️ | Collapsed | RawDataPanel (debug view) |
| 10 | System IDs | 🔧 | Collapsed | customer_id, rep_id, vendor_id, etc. |
| 11 | Account | 👤 | Collapsed | Email, Password (add mode only), Role, is_active, is_staff |

### 2. Layout Selector

A toolbar in the header allows selecting different layouts for team design discussions:

| Layout | Icon | Description |
|--------|------|-------------|
| **Best Practice** | ⭐ | Enterprise UX standard - collapsible sections |
| **Grid** | ⊞ | 3-column grid with labels above |
| **Compact** | ⊟ | Dense 3-column layout |
| **Dense** | ≡ | Ultra-compact inline labels |
| **Horizontal** | ☰ | 2-column with left labels |
| **Two Column** | ⧉ | Card-based layout |

### 3. View/Edit Mode Toggle

- **View mode**: Shows Edit button to switch to edit mode
- **Edit mode**: Shows Cancel (returns to view) and Save buttons
- **Add mode**: Shows Save button only
- Uses `effectiveMode` state to allow runtime mode switching without route changes

### 4. Panel Components

Reusable panels from `@/apps/common/components/panels`:

| Panel | Purpose |
|-------|---------|
| `CommunicationsPanel` | Emails, phones, addresses, domains with inline editing |
| `CommentsPanel` | Comments/notes with threading |
| `MetadataPanel` | System metadata (created, modified, etc.) |
| `RefsPanel` | References and relationships |
| `PrefsPanel` | User preferences |
| `ActionsPanel` | Action items and tasks |
| `RawDataPanel` | JSON view for debugging |

### 5. Admin Field Controls

Administrators can control field visibility and editability per-field using `useDetailFieldAccess` hook:

- **Show/Hide Toggle** - Control which fields are visible to non-admin users
- **Read-Only Toggle** - Make fields read-only for non-admin users

### 6. Auto-Created Account Email

When a Contact is saved, the backend automatically creates an Email record linked to the contact if the account email doesn't already exist in `refs.links.email`. The Email is created with `name="account"` and `is_primary=true`.

---

## Component Architecture

### Core UI Components

```typescript
// Enterprise-style field row with fixed-width left label
interface FieldRowProps {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
  error?: string;
  required?: boolean;
  hint?: string;
}

// Collapsible section with icon header
interface SectionProps {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  defaultExpanded?: boolean;
}
```

### State Management

```typescript
// Mode management (allows toggling view↔edit)
const [effectiveMode, setEffectiveMode] = useState<"add" | "edit" | "view">(mode);

// Layout selector for team discussion
const [selectedLayout, setSelectedLayout] = useState<LayoutStyle>("best-practice");
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

Communications are managed through the `CommunicationsPanel` component which handles:
- Emails, phones, addresses, and domains
- Inline add/edit/delete with modal forms
- Data stored in `refs.links.{email|phone|address|domain}`

---

## Data Flow

### Loading Contact Data

1. Contact data passed via `dataProp` or `location.state`
2. `useEffect` normalizes data and calls `reset()` on form
3. Communication records extracted from `data.refs.links`
4. Panels receive data via props

### Saving Contact

1. Form submission triggers `onSubmit`
2. `mapRefsFormToApi()` transforms refs for API format
3. `createContact` or `updateContact` called based on mode
4. Success toast displayed, `onSaved` callback invoked

### Mode Switching

1. View mode shows Edit button
2. Clicking Edit sets `effectiveMode` to "edit"
3. Cancel returns to "view" mode
4. Save persists changes and optionally returns to view

---

## Hooks Used

| Hook | Purpose |
|------|---------|
| `useForm` | React Hook Form for contact fields |
| `useDetailFieldAccess` | Admin field visibility/readonly controls |
| `useDispatch` | Redux dispatch for toasts |
| `useLocation` | React Router state access |
| `useState` | Mode and layout state |
| `useMemo` | Memoized field names array |
| `useEffect` | Data loading and mode sync |

---

## Related Components

### UI Components
- `ComponentCard` - Card wrapper
- `PageBreadcrumb` - Navigation breadcrumb
- `Input` / `DropDown` / `Checkbox` - Form inputs
- `Label` - Form field labels
- `FieldRow` - Enterprise-style label-left field row
- `Section` - Collapsible section container

### Panel Components
- `CommunicationsPanel` - Emails, phones, addresses, domains
- `CommentsPanel` - Notes and comments
- `MetadataPanel` - System metadata display
- `RefsPanel` - References viewer/editor
- `PrefsPanel` - Preferences editor
- `ActionsPanel` - Action items
- `RawDataPanel` - JSON debug view

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

### View Mode (with Edit toggle)
```tsx
<ContactDetail 
  modeProp="view" 
  dataProp={contactData}
/>
// User can click Edit button to switch to edit mode
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

---

## Backend Integration

### Auto-Created Account Email

When a Contact is saved on the backend, the `Contact.save()` method automatically:

1. Checks if `refs.links.email` contains the account email
2. If not found, creates an `Email` record with:
   - `email`: The contact's account email
   - `name`: "account"
   - `is_primary`: true
3. Links the Email to the contact via `refs.links.email`

This ensures every contact has their login email available in the communications list.
