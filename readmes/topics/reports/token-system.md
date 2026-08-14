# Token System — Handing Data to Better Tools

**Established:** 2026-08-13
**Flowchart:** `readmes/charts/flowcharts/wc3-token-system.dot` (.svg and .pdf)
**Scar #57:** Be expert in handing data to better tools.

---

## The Rule

WC3 provides `{{field.path}}` and data exports. Users format in their own tools. Their tools are better than anything we would build.

---

## Token Syntax

| Syntax | Example | Result |
|--------|---------|--------|
| `{{field}}` | `{{company}}` | `Acme Corp` |
| `{{field\|format}}` | `{{totals.total\|currency}}` | `$1,234.56` |
| `{{#each lines}}...{{/each}}` | Iterate line items | Repeated block |

Formats: `currency`, `date`, `number`, `percent`. No format = raw string.

Paths use dot-notation: `totals.total`, `config.ship_to.company`, `item.ida_item`.

---

## How Users Get Tokens

**Reports dialog → first row → {{Tokens}}**

| Action | Result |
|--------|--------|
| Click field | `{{field.path}}` → clipboard |
| Shift-click | Add to set |
| Copy All (Detail) | One token per line → paste into email |
| Copy All (List) | Tab-separated headers + tokens → paste into spreadsheet |

---

## Five Handoff Formats

| Format | What | Destination |
|--------|------|-------------|
| **Clipboard** | Resolved `{{tokens}}` | Gmail, Word, Pages — paste anywhere |
| **CSV** | Headers + rows | Google Sheets, Excel — mail merge |
| **JSON** | Structured data | Scripts, Zapier, API clients |
| **Populated SVG** | IDs → values, line panels cloned | Printer, PDF viewer |
| **Template Path** | Open user's .docx/.pages pre-populated | Word, Pages via AppleScript/terminal |

---

## One Resolution Function

All token resolution — MarkdownEditor, UniversalPrint, SvgFormGenerator — uses the same function:

```typescript
function resolve(data: any, path: string): unknown {
  return path.split('.').reduce((obj, key) => obj?.[key], data);
}
```

If a token works in one place, it works everywhere.

---

## Field Sources

`/wcapi/report-fields/?model=<name>` returns:

| Source | Fields |
|--------|--------|
| `direct` | ida, name, status, dt_created |
| `related` | contact.company, vendor.name |
| `json_paths` | config.ship_to.company, totals.subtotal |
| `lines` | item.ida_item, quantity.active, price.unit |

---

## File Map

| What | Where |
|------|-------|
| TokenBuilder | `React2025/src/components/common/TokenBuilder.tsx` |
| Token resolution | `MarkdownEditor.tsx`, `UniversalPrint.ts`, `SvgFormGenerator.ts` |
| Field registry | `/wcapi/report-fields/` |
| Flowchart | `readmes/charts/flowcharts/wc3-token-system.dot` |
