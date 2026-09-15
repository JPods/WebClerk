# Unsaved Changes Guard

**Status:** ✅ Implemented  
**Date:** March 5, 2026

---

## Overview

Prevents data loss by warning users before performing actions on forms with unsaved changes.

**Features:**
- Shows browser warning on page close/refresh
- Guards specific actions (print, load new record, etc.)
- Offers "Save First" option before proceeding

> **Note:** This app uses a custom window management system rather than standard React Router navigation for record changes, so navigation blocking is handled via the `guardAction` wrapper rather than React Router's `useBlocker`.

---

## Files

| File | Purpose |
|------|---------|
| [useUnsavedChangesGuard.ts](../../src/hooks/useUnsavedChangesGuard.ts) | Core hook for action guards and beforeunload |
| [UnsavedChangesDialog.tsx](../../src/components/common/UnsavedChangesDialog.tsx) | Modal dialog component |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Detail Page Component                     │
│                                                             │
│  useForm() ─────────► isDirty                               │
│                          │                                  │
│                          ▼                                  │
│  useUnsavedChangesGuard(isDirty) ──────────────────────────│
│       │                                                     │
│       ├─► guardAction() wrapper for print, etc.            │
│       └─► beforeunload (browser close/refresh)             │
│                                                             │
│  UnsavedChangesDialog ◄─── isActionPending                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Usage

### Basic Integration

```tsx
import { useForm } from 'react-hook-form';
import useUnsavedChangesGuard from '@/hooks/useUnsavedChangesGuard';
import UnsavedChangesDialog from '@/components/common/UnsavedChangesDialog';

function MyDetail() {
  const { formState: { isDirty }, handleSubmit } = useForm();
  
  const {
    guardAction,
    isActionPending,
    pendingAction,
    confirmAction,
    cancelAction,
  } = useUnsavedChangesGuard(isDirty);

  // Wrap actions that should warn about unsaved changes
  const handlePrint = guardAction(() => window.print(), 'printing');
  const handleLoadNew = guardAction(() => loadNewRecord(), 'loading new record');

  const handleSave = async () => {
    // ... save logic
  };

  return (
    <div>
      {/* Your form content */}
      <button onClick={handlePrint}>Print</button>
      
      {/* Action blocking dialog */}
      <UnsavedChangesDialog
        isOpen={isActionPending}
        type="action"
        actionName={pendingAction?.name}
        onConfirm={confirmAction}
        onCancel={cancelAction}
        onSaveFirst={handleSave}
      />
    </div>
  );
}
```

### Without react-hook-form

For components that track dirty state manually:

```tsx
const [originalData, setOriginalData] = useState(null);
const [editData, setEditData] = useState(null);

const isDirty = useMemo(() => {
  return JSON.stringify(originalData) !== JSON.stringify(editData);
}, [originalData, editData]);

const guard = useUnsavedChangesGuard(isDirty);
```

---

## Hook API

### `useUnsavedChangesGuard(isDirty, options?)`

**Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `isDirty` | `boolean` | Whether the form has unsaved changes |
| `options.message` | `string` | Custom message for browser warning (browsers may ignore) |
| `options.enableBeforeUnload` | `boolean` | Enable browser close/refresh warning (default: `true`) |

**Returns:**
| Property | Type | Description |
|----------|------|-------------|
| `isActionPending` | `boolean` | Whether a guarded action is awaiting confirmation |
| `pendingAction` | `{ name: string; callback: () => void } \| null` | Details of pending action |
| `confirmAction` | `() => void` | Proceed with pending action |
| `cancelAction` | `() => void` | Cancel pending action |
| `guardAction` | `(action, name?) => wrappedAction` | Wrap an action with unsaved changes check |
| `showDialog` | `boolean` | Whether dialog should be shown |

---

## Component API

### `UnsavedChangesDialog`

**Props:**
| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `isOpen` | `boolean` | ✅ | Whether dialog is visible |
| `type` | `'navigation' \| 'action'` | ✅ | Type affects messaging |
| `actionName` | `string` | - | Name of action (for `type="action"`) |
| `onConfirm` | `() => void` | ✅ | Called when user discards changes |
| `onCancel` | `() => void` | ✅ | Called when user stays on page |
| `onSaveFirst` | `() => Promise<void>` | - | Optional save handler |
| `isSaving` | `boolean` | - | Shows loading state on Save button |

---

## Integration Status

### Transaction Pages (via TransactionDetailBase)
All transaction detail pages automatically have unsaved changes protection:
- ✅ OrderDetail
- ✅ InvoiceDetail
- ✅ ProposalDetail
- ✅ PurchaseDetail
- ✅ WorkOrderDetail
- ✅ RequisitionDetail

**Protected actions:**
- ✅ Print (header button + toolbar)
- ✅ Browser close/refresh

### Org & Other Detail Pages
Requires manual integration (see Usage section above):
- ⬜ CustomerDetail
- ⬜ VendorDetail
- ⬜ ContactDetail
- ⬜ AddressDetail
- ⬜ etc.

---

## Dialog Behavior

### Action Dialog (`type="action"`)
- **Title:** "Unsaved Changes - {actionName}"
- **Message:** "You have unsaved changes. Would you like to save before {actionName}?"
- **Buttons:**
  - "Cancel" - Cancel the action
  - "Save First" - Save then execute action (if `onSaveFirst` provided)
  - "Discard & Continue" - Execute action without saving

---

## Browser Behavior

The `beforeunload` event shows a browser-native dialog when:
- Closing the tab/window
- Refreshing the page
- Navigating to external URLs

**Note:** Modern browsers ignore custom messages for security reasons and show generic text like "Changes you made may not be saved."

---

## See Also

- [TransactionDetailBase.tsx](../../src/apps/transactions/components/TransactionDetailBase.tsx) - Example integration
