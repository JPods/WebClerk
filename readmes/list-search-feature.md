# List Search Feature

## Overview

All List pages in the application support two search modes:

1. **Selection Search** (default): Filters the currently loaded data in-memory
2. **Database Search**: Queries the backend database with search terms

When **Database Search** is enabled (via the "Query DB" checkbox), comma-separated search terms create an **AND search** across all scalar fields and `refs.keywords`.

## Search Behavior

### Selection Search (Default)

- Filters the currently loaded records in the browser
- Fast, instant filtering
- Works with any text in the search box
- Searches all scalar fields and `refs.keywords`
- **Comma-separated terms use AND logic** - e.g., "red, shirt" finds rows containing BOTH "red" AND "shirt"

### Database Search (Query DB checked)

- Sends search terms to the backend API
- Backend performs search across database
- Useful for finding records not in current page/selection
- Same AND logic for comma-separated terms
- Backend should search all scalar fields and `refs.keywords`

## Search Term Parsing

Search terms are parsed using this logic:

- Input string is split by `,` or `, ` (comma with optional space)
- Each term is trimmed and lowercased
- Empty terms are filtered out
- All terms must match (AND logic)

**Examples:**

| Input | Parsed Terms | Match Requirement |
|-------|--------------|-------------------|
| `apple` | `["apple"]` | Contains "apple" |
| `apple, orange` | `["apple", "orange"]` | Contains BOTH "apple" AND "orange" |
| `red,shirt,cotton` | `["red", "shirt", "cotton"]` | Contains ALL three terms |
| `  blue ,  green  ` | `["blue", "green"]` | Contains BOTH (whitespace trimmed) |

## Field Search Scope

The search checks these fields on each row:

1. **All scalar fields** - strings, numbers, booleans (converted to string)
2. **refs.keywords** - if present, can be string or array of strings

```typescript
// Example row
{
  id: 123,
  display_name: "Acme Corp",
  status: "active",
  refs: {
    keywords: "manufacturing wholesale supplier acme"
  }
}
// Search "acme, wholesale" would match this row
```

## UI Components

### AdvancedDataTable Props

```typescript
interface AdvancedDataTableProps<T> {
  // ... other props
  
  /** Enable toggle between searching in current selection vs querying database */
  enableDatabaseSearch?: boolean;
  
  /** Current search mode: true = query database, false = search in selection */
  searchDatabase?: boolean;
  
  /** Callback when search mode changes */
  onSearchModeChange?: (searchDatabase: boolean) => void;
  
  /** Callback to perform database search with parsed terms */
  onDatabaseSearch?: (terms: string[]) => Promise<void> | void;
}
```

### Checkbox UI

When `enableDatabaseSearch={true}`, a checkbox labeled "Query DB" appears next to the search input:

```
[🔎 Search...                    ] ☐ Query DB
```

## Implementation

### For List Pages Using AdvancedDataTable Directly

```tsx
import AdvancedDataTable from "@/components/common/AdvancedDataTable";
import { useState, useCallback } from "react";

export default function MyModelList() {
  const [data, setData] = useState<MyModel[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);

  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    try {
      setLoading(true);
      const searchQuery = terms.join(",");
      const res = await fetchMyModels({ search: searchQuery });
      if (res.status === 200) {
        setData(res.data.items || []);
      }
    } catch (error) {
      console.error("Database search failed:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <AdvancedDataTable
      data={data}
      columns={columns}
      loading={loading}
      enableDatabaseSearch={true}
      searchDatabase={searchDatabase}
      onSearchModeChange={setSearchDatabase}
      onDatabaseSearch={handleDatabaseSearch}
      // ... other props
    />
  );
}
```

### For List Pages Using OrgEntityList

```tsx
import OrgEntityList from "@/apps/orgs/components/OrgEntityList";
import { useState, useCallback } from "react";

export default function MyOrgList() {
  const [searchDatabase, setSearchDatabase] = useState(false);

  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    const searchQuery = terms.join(",");
    await fetchMyOrgs({ search: searchQuery });
  }, []);

  return (
    <OrgEntityList
      modelKey="myorg"
      title="My Orgs"
      fetchFn={fetchMyOrgs}
      columns={columns}
      enableDatabaseSearch={true}
      searchDatabase={searchDatabase}
      onSearchModeChange={setSearchDatabase}
      onDatabaseSearch={handleDatabaseSearch}
      // ... other props
    />
  );
}
```

## Utility Function

The `parseSearchTerms` function is exported from AdvancedDataTable for use in custom implementations:

```typescript
import { parseSearchTerms } from "@/components/common/AdvancedDataTable";

const terms = parseSearchTerms("apple, orange, banana");
// Returns: ["apple", "orange", "banana"]
```

## Backend Integration

When database search is triggered, the `onDatabaseSearch` callback receives an array of parsed terms. The implementation should:

1. Join terms (e.g., with comma) or format as needed by your API
2. Send to backend API with search parameter
3. Update component state with results

### Backend Search Implementation (Django example)

The backend should implement AND search across relevant fields:

```python
# In your Django view/viewset
def get_queryset(self):
    queryset = super().get_queryset()
    search = self.request.query_params.get('search', '')
    
    if search:
        terms = [t.strip().lower() for t in search.split(',') if t.strip()]
        
        for term in terms:
            # AND search - each term must match somewhere
            queryset = queryset.filter(
                Q(display_name__icontains=term) |
                Q(status__icontains=term) |
                Q(refs__keywords__icontains=term) |
                # ... other searchable fields
            )
    
    return queryset
```

## Files Updated

All 55+ List pages in the following directories have database search enabled:

- `src/apps/orgs/models/*/pages/*List.tsx`
- `src/apps/transactions/models/*/pages/*List.tsx`
- `src/apps/products/models/*/pages/*List.tsx`
- `src/apps/accounts/models/*/pages/*List.tsx`
- `src/apps/core/models/*/pages/*List.tsx`
- `src/apps/docs/models/*/pages/*List.tsx`
- `src/apps/communications/models/*/pages/*List.tsx`
- `src/apps/sync/models/*/pages/*List.tsx`
- `src/apps/support/models/*/pages/*List.tsx`

## Notes

- The checkbox state is stored locally in each component (not persisted)
- When unchecked, search reverts to filtering in-memory data
- The search is case-insensitive
- Partial matches are supported (e.g., "app" matches "apple")
- Empty search terms are ignored
