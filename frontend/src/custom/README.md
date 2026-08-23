# Custom Pages & Components

Your code lives here. WebClerk updates never touch this directory.

## Structure

```
custom/
  pages/          <- your .tsx page components (routed via Report records)
  components/     <- your reusable .tsx components
  index.ts        <- auto-generated registry of custom pages
```

## How to add a custom page

1. **Create your .tsx file** in `custom/pages/`:

```tsx
// custom/pages/VendorScorecard.tsx
import { DataGrid } from '@/components/common/DataGrid';
import { getRecords } from '@/api/wcapi';
import { useEffect, useState } from 'react';

export default function VendorScorecard() {
  const [vendors, setVendors] = useState<any[]>([]);

  useEffect(() => {
    getRecords('vendor', { is_active: true }).then((res: any) => {
      setVendors(res?.results || []);
    });
  }, []);

  return (
    <div data-wc="vendor-scorecard">
      <h2>Vendor Scorecard</h2>
      <DataGrid records={vendors} columns={[
        { field: 'name', label: 'Vendor' },
        { field: 'health_rating', label: 'Rating' },
      ]} />
    </div>
  );
}
```

2. **Register it** as a Report record (via DataBrowser or Alice):
   - `model_name`: the primary model this page works with (e.g., `vendor`)
   - `name`: display name (e.g., `Vendor Scorecard`)
   - `output_type`: `screen`
   - `category`: `custom`
   - `purpose`: `custom-page`
   - `config.route`: URL path (e.g., `/custom/vendor-scorecard`)
   - `config.component`: filename without extension (e.g., `VendorScorecard`)

3. **The page is live** at the configured route. No rebuild needed if using dynamic imports.

## What you have access to

All of WebClerk's component library:

| Import | What it gives you |
|--------|------------------|
| `@/api/wcapi` | `getRecords`, `saveRecord`, `getRecord` — all CRUD through wcapi |
| `@/components/common/DataGrid` | Data lists with sort, filter, column config |
| `@/components/common/DynamicDetail` | JSON-driven form renderer |
| `@/components/fields/BaseField` | All field types (text, select, date, currency, etc.) |
| `@/components/common/ReportsDialog` | Print/export dialog |
| `@/components/print/SvgFormGenerator` | SVG form generation and population |
| `@/hooks/useListFieldConfig` | Column configuration with saved layouts |
| `@/hooks/usePrintLayout` | Print layout from Settings |
| `@/context/WindowManagerContext` | Multi-window management |
| `@/utils/fieldFormatters` | Date, currency, number formatting |

## Rules

- **All CRUD through wcapi** — never import models directly
- **Add `data-wc` attribute** to your root element — enables the help system
- **Don't modify files outside `custom/`** — those get overwritten on updates
- **Your pages, your responsibility** — Alice will flag issues but won't auto-fix custom code

## SVG Forms vs Custom Pages

- **SVG Forms** = print output. Customer designs the template, we merge data.
- **Custom Pages** = interactive screens. Developer writes React, uses our components.

Both register as Report records. Same system, different output types.
