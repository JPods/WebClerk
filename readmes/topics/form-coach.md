# FormCoach — Print Pre-Check & Data Completeness

**Status:** ✅ Implemented  
**Date:** March 8, 2026

---

## Overview

FormCoach validates transaction data completeness before printing. When a user
clicks **Print**, the system runs configurable rules and surfaces issues with
color-coded severity:

| Color | Severity | Meaning | Example |
|-------|----------|---------|---------|
| 🔴 Red | `error` | Required field is completely missing | No Bill-To contact assigned |
| 🟠 Orange | `warning` | Field exists but data is incomplete | Bill-To has no email address |
| 🔵 Blue | `info` | Suggestion for better data quality | Order status is still "planned" |

Issues appear both **above the form** (dismissible) and **inside the Print
Preview modal** (compact, hidden from actual print output via `print:hidden`).

---

## Files

| File | Purpose |
|------|---------|
| [useFormCoach.ts](../../src/hooks/useFormCoach.ts) | Core hook — rule engine + React state |
| [FormCoachAlert.tsx](../../src/apps/common/components/FormCoachAlert.tsx) | Visual component — renders issue list |
| [TransactionDetailBase.tsx](../../src/apps/transactions/components/TransactionDetailBase.tsx) | Integration point — wires hook + component into print flow |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  TransactionDetailBase                       │
│                                                             │
│  User clicks Print                                          │
│       │                                                     │
│       ▼                                                     │
│  guardAction(executePrint)                                  │
│       │                                                     │
│       ▼                                                     │
│  formCoach.runCheck()  ──► evaluates rules against data     │
│       │                                                     │
│       ├──► setShowPrintPreview(true)                        │
│       │                                                     │
│       ▼                                                     │
│  ┌──────────────────────────────────┐                       │
│  │  FormCoachAlert (above form)    │ ← dismissible          │
│  └──────────────────────────────────┘                       │
│                                                             │
│  ┌──────────────────────────────────┐                       │
│  │  PrintPreviewModal              │                        │
│  │  ┌────────────────────────────┐ │                        │
│  │  │ FormCoachAlert (compact)   │ │ ← print:hidden         │
│  │  └────────────────────────────┘ │                        │
│  │  ┌────────────────────────────┐ │                        │
│  │  │ OrderPrintDocument / etc.  │ │                        │
│  │  └────────────────────────────┘ │                        │
│  └──────────────────────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Hook API

```ts
const {
  issues,        // CoachIssue[]  — all issues found
  errors,        // CoachIssue[]  — severity === 'error'
  warnings,      // CoachIssue[]  — severity === 'warning'
  infos,         // CoachIssue[]  — severity === 'info'
  hasErrors,     // boolean
  hasWarnings,   // boolean
  hasIssues,     // boolean
  hasChecked,    // boolean — true after first runCheck()
  runCheck,      // () => CoachIssue[]  — evaluate all rules
  clearIssues,   // () => void  — reset (dismisses alert)
} = useFormCoach(data, modelType, extraRules?);
```

### Parameters

| Param | Type | Description |
|-------|------|-------------|
| `data` | `Record<string, unknown> \| null` | The transaction record (or `null` before load) |
| `modelType` | `TransactionModelType` | `'order'` · `'invoice'` · `'proposal'` · `'purchase'` · `'workorder'` · `'receipt'` · `'adjustment'` |
| `extraRules` | `CoachRule[]` | Optional additional rules merged with defaults |

### CoachIssue

```ts
interface CoachIssue {
  key: string;           // unique key for React rendering
  severity: CoachSeverity; // 'error' | 'warning' | 'info'
  field: string;         // human-readable label
  message: string;       // explanation shown to user
  section?: string;      // which tab/section (Header, Contacts, etc.)
}
```

---

## Built-in Rules (17)

Rules are scoped by `modelType` — a rule only fires for the transaction types
listed in its `models` array.

### Error Rules (red — missing required fields)

| Key | Field | Models | Condition |
|-----|-------|--------|-----------|
| `customer_missing` | Customer | order, invoice, proposal | No `customer_id` and no `refs.links.customer` |
| `billto_missing` | Bill-To Contact | order, invoice | No contact with `purpose: "billto"` |
| `shipto_missing` | Ship-To Contact | order, invoice | No contact with `purpose: "shipto"` |
| `vendor_missing` | Vendor | purchase, workorder | No `vendor_id` |
| `no_lines` | Line Items | all | Empty `lines` array |

### Warning Rules (orange — incomplete data)

| Key | Field | Models | Condition |
|-----|-------|--------|-----------|
| `billto_no_address` | Bill-To Address | order, invoice | Bill-To exists but `address1` is blank |
| `billto_no_email` | Bill-To Email | order, invoice | Bill-To exists but `email` is blank |
| `billto_no_phone` | Bill-To Phone | order, invoice | Bill-To exists but `phone` is blank |
| `shipto_no_address` | Ship-To Address | order, invoice | Ship-To exists but `address1` is blank |
| `lines_zero_price` | Line Prices | all | Any line has `unit_price ≤ 0` |
| `no_terms` | Payment Terms | order, invoice | `terms` is blank |
| `no_due_date` | Due Date | invoice | `due_date` is blank |
| `no_po_number` | PO Number | order | `po_number` is blank |
| `zero_total` | Order Total | all | `totals.grand_total ≤ 0` |

### Info Rules (blue — suggestions)

| Key | Field | Models | Condition |
|-----|-------|--------|-----------|
| `status_planned` | Status | all | `status` is `"planned"` (not yet confirmed) |

---

## Extending with Custom Rules

Any detail page can pass additional rules via the `extraRules` parameter:

```ts
const customRules: CoachRule[] = [
  {
    key: 'custom_shipping_method',
    field: 'Shipping Method',
    section: 'Header',
    severity: 'warning',
    message: 'No shipping method selected — carrier may default.',
    models: ['order'],
    check: (data) => isBlankString(dig(data, 'shipping_method')),
  },
];

const coach = useFormCoach(data, 'order', customRules);
```

Rules must implement:

```ts
interface CoachRule {
  key: string;
  field: string;
  section?: string;
  severity: CoachSeverity;
  message: string;
  models: TransactionModelType[] | '*';  // '*' = all types
  check: (data: Record<string, unknown>) => boolean; // true = issue found
}
```

---

## FormCoachAlert Component

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `issues` | `CoachIssue[]` | — | Issues to display |
| `onDismiss` | `() => void` | — | Callback when user clicks X (clears issues) |
| `compact` | `boolean` | `false` | Fewer visual elements (used inside print modal) |
| `title` | `string` | auto | Override the header text |
| `formSourcePath` | `string` | — | Relative path to the form source file; shown at the top with an **Open in VS Code** button (`vscode://file/…`) |
| `className` | `string` | `''` | Additional CSS classes |

### Styling

The component uses the dominant severity to pick its outer border/background:

- **Error-dominant:** red border + light red background
- **Warning-dominant:** orange border + light orange background
- **Info-only:** blue border + light blue background

Each individual issue row is colored according to its own severity, with an icon
prefix (`FaExclamationCircle`, `FaExclamationTriangle`, `FaInfoCircle`).

Dark mode is fully supported via Tailwind's `dark:` variants.

---

## Future Enhancements

- **Block print on errors:** optionally prevent the print preview from opening
  when critical fields are missing (configurable per org).
- **Per-model rule overrides:** load rule config from `settings` API so admins
  can enable/disable specific checks.
- **Email pre-check:** run the same coach before sending email (same hook, different trigger point).
- **Save-time coaching:** show warnings inline on the form while editing, not just at print time.
- **Rule severity customization:** allow admins to promote warnings to errors or demote as needed.
