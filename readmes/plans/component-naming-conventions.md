# Component Naming Conventions

> Plan for consistent component names, filenames, and exported utilities across `src/apps/common/components/panels/`.

---

## Problem

Component files and their exported symbols grew organically, producing inconsistent names that obscure what lives where. Example:

| Item | Current name | Issue |
|------|-------------|-------|
| File | `ContactPanel.tsx` | **Good** — matches the default-exported component |
| Default export | `ContactPanel` | **Good** — matches the filename |
| Helper function | `normalizeRefsLinksContact` | **Bad** — uses the old filename (`RefsLinksContactPanel`), not the current component name |
| Interface | `RefContact` | Acceptable shorthand, but inconsistent with file stem |
| Barrel alias | `ContactLinksPanel` (re-export of same default) | Confusing — suggests a different component |
| Deprecated alias | `RefsLinksContactPanel` (barrel re-export) | Legacy — should migrate callers then remove |

---

## Rules

### 1. Filename = Default Export = Component Name

```
{ComponentName}.tsx   →   export default {ComponentName}
```

The filename stem **is** the canonical component name. No other default export name is allowed.

| Correct | Wrong |
|---------|-------|
| `ContactPanel.tsx` → `export default ContactPanel` | `ContactPanel.tsx` → `export default RefsLinksContactPanel` |
| `FinancialsPanel.tsx` → `export default FinancialsPanel` | `FinancialsPanel.tsx` → `export default TransactionFinancialsPanel` |

### 2. Named exports use the component name as prefix

Utility functions, types, and interfaces exported from a panel file follow the pattern:

```
{verb}{ComponentName}{Noun?}
```

| Export kind | Pattern | Example (ContactPanel.tsx) |
|-------------|---------|--------------------------|
| Normalizer function | `normalize{ComponentName}Data` | `normalizeContactPanelData` |
| Props interface | `{ComponentName}Props` | `ContactPanelProps` |
| Data interface | `{ComponentName}Data` or domain noun | `ContactPanelContact` or `RefContact` |
| Hook | `use{ComponentName}` | `useContactPanel` |
| Constants | `{COMPONENT_NAME}_PURPOSES` | `CONTACT_PANEL_PURPOSES` |

### 3. Barrel file (`index.ts`) exports

```ts
// ✅ Canonical export — name matches file
export { default as ContactPanel } from "./ContactPanel";

// ✅ Named utility — prefixed with component name
export { normalizeContactPanelData } from "./ContactPanel";

// ✅ Type export — clear domain type
export type { RefContact } from "./ContactPanel";

// ❌ Avoid duplicate aliases for the same default
// export { default as ContactLinksPanel } from "./ContactPanel";

// ❌ Avoid legacy names without @deprecated + removal date
// export { default as RefsLinksContactPanel } from "./ContactPanel";
```

**Rule:** Each component file gets **one** default re-export in the barrel. Aliases are allowed only during a deprecation window (see §5).

### 4. Re-export stubs in app-specific directories

When `transactions/components/ContactPanel.tsx` re-exports the common panel:

```ts
/**
 * ContactPanel — re-exported from common panels
 * @see @/apps/common/components/panels/ContactPanel
 */
export { default } from "@/apps/common/components/panels/ContactPanel";
export { normalizeContactPanelData } from "@/apps/common/components/panels/ContactPanel";
```

The re-export file name **must** match the canonical component name.

### 5. Deprecation protocol

When renaming a symbol:

1. Add the new name as the primary export.
2. Keep the old name as a **named** re-export with `@deprecated` JSDoc and a target removal version/date.
3. Update all first-party callers in the same PR.
4. Remove the deprecated alias after one release cycle.

```ts
// ContactPanel.tsx
export default ContactPanel;

/** @deprecated Use ContactPanel instead — remove after v2.1 */
export { ContactPanel as RefsLinksContactPanel };

/** @deprecated Use normalizeContactPanelData instead — remove after v2.1 */
export { normalizeContactPanelData as normalizeRefsLinksContact };
```

---

## Action Items — ContactPanel.tsx

### Rename `normalizeRefsLinksContact` → `normalizeContactPanelData`

| Location | Current | Target |
|----------|---------|--------|
| `common/panels/ContactPanel.tsx` (definition) | `export function normalizeRefsLinksContact(...)` | `export function normalizeContactPanelData(...)` |
| `common/panels/ContactPanel.tsx` (bottom) | — | Add `export { normalizeContactPanelData as normalizeRefsLinksContact }` with `@deprecated` |
| `common/panels/index.ts` | `normalizeRefsLinksContact` | `normalizeContactPanelData` (+ deprecated re-export) |
| `transactions/components/ContactPanel.tsx` | `export { normalizeRefsLinksContact }` | `export { normalizeContactPanelData }` |
| `transactions/components/TransactionDetailBase.tsx` | `import { normalizeRefsLinksContact }` | `import { normalizeContactPanelData }` |
| `orgs/models/vendor/pages/VendorDetail.tsx` | `normalizeRefsLinksContact` | `normalizeContactPanelData` |
| `orgs/models/customer/pages/CustomerDetail.tsx` | `normalizeRefsLinksContact` | `normalizeContactPanelData` |

### Remove duplicate barrel aliases

| Current alias | Action |
|---------------|--------|
| `ContactLinksPanel` (alias of `ContactPanel`) | Remove — misleading name |
| `RefsLinksContactPanel` (alias of `ContactPanel`) | Keep with `@deprecated` tag, remove after v2.1 |

### Rename `ContactPanelProps` (already done ✅)

Renamed from `RefsLinksContactPanelProps` in the previous rename pass.

---

## Audit: Other Panels

Apply the same filename = component-name rule project-wide.

| File | Default export | Status | Notes |
|------|---------------|--------|-------|
| `ActionsPanel.tsx` | `ActionsPanel` | ✅ Correct | |
| `BasicInformationPanel.tsx` | `BasicInformationPanel` | ✅ Correct | |
| `CommentsPanel.tsx` | `CommentsPanel` | ✅ Correct | |
| `CommunicationsPanel.tsx` | `CommunicationsPanel` | ✅ Correct | |
| `ContactPanel.tsx` | `ContactPanel` | ✅ Correct | Helper function needs rename |
| `DocumentsPanel.tsx` | `DocumentsPanel` | ✅ Correct | |
| `FinancialsPanel.tsx` | `TransactionFinancialsPanel` | ⚠️ Mismatch | Default export should be `FinancialsPanel` |
| `LinkagesPanel.tsx` | `LinkagesPanel` | ✅ Correct | |
| `MetadataPanel.tsx` | `MetadataPanel` | ✅ Correct | |
| `ModelDataPanel.tsx` | `ModelDataPanel` | ✅ Correct | |
| `PrefsPanel.tsx` | `PrefsPanel` | ✅ Correct | |
| `QAPanel.tsx` | `QAPanel` | ✅ Correct | |
| `RawDataPanel.tsx` | `RawDataPanel` | ✅ Correct | |
| `RefsPanel.tsx` | `RefsPanel` | ✅ Correct | |
| `ShippingPanel.tsx` | `ShippingPanel` | ✅ Correct | |
| `TemplateQAPanel.tsx` | `TemplateQAPanel` | ✅ Correct | |

### Barrel alias audit (`index.ts`)

| Alias | Source file | Action |
|-------|-----------|--------|
| `ContactLinksPanel` | `ContactPanel.tsx` | Remove — misleading |
| `RefsLinksContactPanel` | `ContactPanel.tsx` | Deprecate → remove |
| `TransactionFinancialsPanel` | `FinancialsPanel.tsx` | Rename default export in file to `FinancialsPanel`, keep `TransactionFinancialsPanel` as deprecated alias |

---

## Reference: ContactPanel.tsx Layout (Template)

Use this as the canonical layout for any panel component file:

```tsx
/**
 * {ComponentName} — {one-line purpose}
 * {Data source or API path}
 */
import React from "react";

// ── Types ──────────────────────────────────────────────
export interface {ComponentName}Data { /* ... */ }

// ── Helpers ────────────────────────────────────────────
export function normalize{ComponentName}Data(raw: any[]): {ComponentName}Data[] {
  /* ... */
}

// ── Props ──────────────────────────────────────────────
interface {ComponentName}Props {
  data: {ComponentName}Data[];
  isEditing?: boolean;
  /* ... */
}

// ── Sub-components (not exported) ──────────────────────
const InternalWidget: React.FC<{ /* ... */ }> = () => { /* ... */ };

// ── Main Component ─────────────────────────────────────
const {ComponentName}: React.FC<{ComponentName}Props> = (props) => {
  /* ... */
};

// ── Exports ────────────────────────────────────────────
export default {ComponentName};

// Deprecated aliases (remove after v2.1)
// /** @deprecated Use {ComponentName} instead */
// export { {ComponentName} as OldName };
```
