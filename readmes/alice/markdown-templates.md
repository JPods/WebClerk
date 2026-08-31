# Markdown Templates — Alice Guide

> **Last updated**: 2026-08-05
> **Owner**: Alice
> **Component**: `React2025/src/components/common/MarkdownEditor.tsx`

---

## What This Is

A markdown editor with field token insertion. Users write markdown that
includes `{{field.path}}` tokens. When rendered, tokens are replaced with
values from a record or list. The same component handles:

- Print templates (packing slips, pick lists, invoices)
- Email templates
- Per-record documentation
- Readmes with live data
- Any document that mixes prose with record data

Users can submit their templates to WC_HQ — the Wisdom of the Many.
Better templates flow upstream for all installations to benefit from.

---

## Token Syntax

### Simple field tokens

```markdown
**Customer:** {{name}}
**Order Total:** {{totals.total|currency}}
**Ship Date:** {{metadata.shipping.ship_date|date}}
```

Tokens use dot-notation to reach into JSON envelopes:
- `quantity.active` — the quantity being acted on (ordered, shipped, etc.)
- `cost.unit` — unit cost
- `price.extended` — extended price
- `totals.margin_pc` — margin percentage

### Format hints

| Hint | What it does | Example |
|------|-------------|---------|
| `currency` | USD formatting | `{{price.unit\|currency}}` → $12.50 |
| `date` | Locale date | `{{dt_created\|date}}` → 8/5/2026 |
| `number` | 2-decimal | `{{quantity.active\|number}}` → 10.00 |
| `percent` | ×100 + % | `{{totals.margin_pc\|percent}}` → 32.0% |

### List iteration

```markdown
{{#each lines}}
| {{item.ida_item}} | {{item.description}} | {{quantity.active}} | {{price.unit|currency}} |
{{/each}}
```

The `{{#each field}}` block iterates over an array field on the record.
Inside the block, tokens resolve against each array element.

---

## quantity.active — The Verb of the Document

The most important field path to understand:

| Document | `{{quantity.active}}` means |
|----------|---------------------------|
| Order template | quantity **ordered** |
| Invoice template | quantity **shipped** |
| Purchase template | quantity **purchased** |
| Receipt template | quantity **received** |
| Proposal template | quantity **proposed** |

There is no `{{quantity.shipped}}` token. The document type gives
`quantity.active` its meaning. One token, every document type.

`{{quantity.remaining}}` = what hasn't transferred downstream yet.
On an order, `remaining` = not yet shipped. On a purchase, `remaining` = not yet received.

---

## Available Object Paths by Model

### All transaction lines (order, invoice, proposal, purchase, receipt)

| Path | What | Format |
|------|------|--------|
| `item.ida_item` | Item ID | |
| `item.description` | Description | |
| `item.unit_measure` | UOM | |
| `quantity.active` | The verb quantity | number |
| `quantity.remaining` | Available for downstream | number |
| `quantity.staged` | Allocated from parent | number |
| `price.unit` | Unit price | currency |
| `price.extended` | Extended price | currency |
| `price.discount_percent` | Discount % | percent |
| `cost.unit` | Unit cost | currency |
| `cost.extended` | Extended cost | currency |
| `cost.tax_rate` | Tax rate | percent |
| `physical.weight.value` | Weight | number |
| `physical.is_hazmat` | Hazmat flag | |
| `line_number` | Line sequence | |
| `line_type` | product/tax/shipping/discount | |

### Transaction headers

| Path | What | Format |
|------|------|--------|
| `ida` | Document ID | |
| `name` | Document name | |
| `status` | Status | |
| `dt_created` | Created date | date |
| `sell.total` | Sell total | currency |
| `cost.total` | Cost total | currency |
| `totals.total` | Grand total | currency |
| `totals.margin` | Margin | currency |
| `totals.margin_pc` | Margin % | percent |
| `totals.balance` | Balance due | currency |
| `ship_via` | Carrier | |

### Contacts

| Path | What | Format |
|------|------|--------|
| `name` | Full name | |
| `ida` | Contact ID | |
| `config.communication.email` | Email | |
| `config.communication.phone` | Phone | |
| `config.addresses.billing` | Billing address | |
| `config.addresses.shipping` | Shipping address | |

---

## Submit to WC_HQ

When a user clicks "Submit to WC_HQ":

1. An Action record is created with the template content in `config.template_content`
2. Action status = `pending`, destination = `wc_hq`
3. Alice reviews the submission — quality, correctness, appropriate for distribution
4. If approved, Alice includes it in the next WC_HQ sync bundle
5. WC_HQ reviews and may distribute to all installations

This is the Wisdom of the Many: users who build better templates contribute
them upstream. Every installation benefits. The user who submitted sees their
template marked as `accepted` or gets feedback.

---

## Alice's Role

Alice helps users build templates:

1. User describes what they want ("I need a packing slip with item weights")
2. Alice drafts the markdown template with appropriate `{{tokens}}`
3. User previews with real record data
4. User tweaks and submits

Alice can also apply the markdown editor to specific fields on request —
she knows which fields on which models would benefit from rich text.

### Alice's Capability Boundaries

Alice runs on a smaller model (8B or 20B). She can:
- Draft simple templates from descriptions
- Suggest field paths for a given model
- Review template syntax
- Explain what tokens are available

She should escalate to Claude Code when:
- Template logic requires complex conditional rendering
- The user needs a new field path that doesn't exist yet (schema change)
- Multi-model joins or cross-record resolution is needed
- The user asks for architectural changes to the template system

**The rule:** When Alice hits her limit, she tells the user honestly:
"This needs Claude Code — let me flag it for the next session."
No pretending. No degraded output. The service is free — there is no
subscription barrier to escalation. Alice creates an Action record
tagged for Claude Code, and the work gets done right.

---

## Component API

```tsx
import MarkdownEditor from '@/components/common/MarkdownEditor';

<MarkdownEditor
  value={markdownContent}
  onChange={setMarkdownContent}
  record={orderData}              // populates {{tokens}}
  modelName="order"               // enables Submit + field picker
  fieldPaths={orderFieldPaths}    // autocomplete list
  templateName="packing_slip"     // saved with submission
  height={500}
/>
```

### Props

| Prop | Type | Default | What |
|------|------|---------|------|
| `value` | string | required | Markdown content |
| `onChange` | (v: string) => void | — | Edit callback |
| `record` | object | — | Record data for token resolution |
| `listData` | object[] | — | List data for {{#each}} |
| `modelName` | string | — | Model name (enables Submit) |
| `fieldPaths` | FieldPath[] | [] | Available fields for picker |
| `templateName` | string | '' | Template identifier |
| `readOnly` | boolean | false | No edit toggle |
| `height` | number | 500 | Editor height in px |
| `darkMode` | boolean | true | Dark theme |

### Token resolution function (standalone use)

```tsx
import { resolveTokens } from '@/components/common/MarkdownEditor';

const rendered = resolveTokens(template, recordData);
```
