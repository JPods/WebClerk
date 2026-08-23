# Transaction Detail Components

Single-purpose components that compose to render any transaction document
(order, invoice, proposal, purchase, requisition, receipt, workorder).

## Architecture

```
TransactionDetail.tsx          <- Orchestrator (317 lines)
  Fetches data + layout Setting
  Manages edit state, save, auto-edit
  Renders sub-components with props

  detail/
    FieldRow.tsx               <- One field: label + input/select/display
    CustomerSearch.tsx          <- useCustomerSearch hook (keyword search)
    HeaderRenderer.tsx          <- Three-column card layout (Customer|ShipTo|Order)
    LineCardRenderer.tsx        <- DataGrid for line items + footer totals
    TabsRenderer.tsx            <- Tab bar + tab content panels
    TransactionToolbar.tsx      <- Edit/Add/Save/Cancel/Report/Order/Delete
    TransactionPrint.tsx        <- Standalone HTML print window builder
    index.ts                   <- Barrel re-exports
```

## The Rule

Each component does one thing. If it does two things, the second becomes its own file.

**How to check:** Can you describe what this component does in one sentence without "and"?
- FieldRow renders a label and its value. (OK - label + value is one concept)
- TransactionToolbar renders action buttons. (OK)
- HeaderRenderer renders customer data AND manages search state. (WRONG - extract search)

## Dependency Graph (no cycles)

```
FieldRow          <- leaf (no project imports)
TransactionPrint  <- leaf (takes data, builds HTML)
CustomerSearch    <- leaf (hook, returns state + handlers)

HeaderRenderer    <- imports FieldRow
LineCardRenderer  <- imports DataGrid, useLineCard, panels
TabsRenderer      <- imports DataGrid, CommentsPanel, etc.
TransactionToolbar <- imports TransactionPrint, WcModelMenu

TransactionDetail <- imports all of the above (orchestrator)
```

## How Models Inherit

The components are model-agnostic. The layout JSON (Setting record) tells them
what to render. To add a new transaction type:

1. Create a `detail_layout` Setting for the model
2. Define columns, fields, field types, options, help text
3. TransactionDetail reads the layout and renders - no code changes

The same FieldRow renders "Terms: n30" on an order and "PO Number: 4425" on a
purchase. The same LineCardRenderer shows sell-side columns (unit_price, disc_price)
on orders and cost-side columns (unit_cost) on purchases. The `family` field
in the layout controls this.

## Label Conventions

| Style | Meaning | Color (light) | Color (dark) |
|-------|---------|---------------|-------------|
| Blue | Select list (click opens dropdown) | #1e40af | #60a5fa |
| Green | Action (click triggers operation) | #166534 | #4ade80 |
| Bold | Searchable field | default + weight:700 | same |
| Italic | Read-only / calculated by system | #94a3b8 | #64748b |
| Normal | Editable text input | #64748b | #94a3b8 |

Underline on hover for all clickable labels. Shift+hover shows help tooltip.

## Print

`TransactionPrint.tsx` exports `openPrintWindow(data, companyInfo, logos, documentText, modelName)`.
Opens a new browser window with standalone HTML - no React, no app chrome.
Company header, three-column layout, line items, totals, conditions, terms.
The browser print dialog opens automatically.

## Alice's Role

Alice watches for:
- Components that grow beyond their single purpose (function bloat)
- Duplicate logic across components (extract to shared utility)
- Layout JSON fields that aren't documented in the schema map
- Search patterns that indicate missing keywords
