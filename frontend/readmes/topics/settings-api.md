# Settings API Reference

This document covers how to fetch, save, and use Setting records from the React2025 frontend.

> **Backend Reference:** See [webClerk3 Settings Reference](../../../webClerk3/readmes/topics/settings/settings_reference.md) for full schema documentation and purpose specifications.
>
> ⚠️ **Keep in Sync:** When modifying interfaces or adding API functions here, update the wc3 settings_reference.md accordingly.

---

## API Client

All settings calls use the standard wcapi client from `src/api/wcapi.ts`.

```typescript
import { apiClient } from '@/api/axios';
```

---

## Standard Settings Bridge (Recommended)

Use the shared bridge for all new settings flows (structure/format/selectlist/list column config).

Files:

- `src/api/settingsBridge.ts`
- `src/hooks/useSettingRecord.ts`

Scope contract:

```typescript
type SettingScope = {
  purpose: string;
  parent_model?: string;
  name?: string;
  role?: string;
};
```

Bridge API:

```typescript
import {
  fetchLatestSettingRecord,
  upsertSettingRecord,
} from '@/api/settingsBridge';

const scope = {
  purpose: 'list_column_config',
  parent_model: 'customer',
  name: 'list_column_config:customer',
};

const latest = await fetchLatestSettingRecord(scope);

await upsertSettingRecord({
  scope,
  data: columnLayoutObject,
});
```

Hook API:

```typescript
import { useSettingRecord } from '@/hooks/useSettingRecord';

const { data, loading, saving, refresh, save } = useSettingRecord({
  purpose: 'list_column_config',
  parent_model: 'customer',
  name: 'list_column_config:customer',
});

await save(columnLayoutObject);
```

Notes:

- `upsertSettingRecord` searches existing records using scope filters and updates the latest row if found; otherwise it creates one.
- For `list_column_config`, store the layout object directly in `setting.data`.
- This replaces one-off, purpose-specific query/save implementations for new work.

---

## Generic Settings Fetch

For any setting purpose, use the generic GET endpoint:

```typescript
interface SettingResponse<T = any> {
  id: number;
  name?: string;
  purpose: string;
  role?: string;
  model_target?: string;
  data: T;
}

async function fetchSetting<T>(params: {
  purpose: string;
  model_target?: string;
  name?: string;
  role?: string;
}): Promise<SettingResponse<T> | null> {
  const res = await apiClient.get('/wcapi/get/', {
    params: {
      model_name: 'setting',
      purpose: params.purpose,
      model_name_filter: params.model_target,
      name: params.name,
      role: params.role,
    },
  });
  const results = res.data.data.results || [];
  return results.length > 0 ? results[0] : null;
}
```

---

## Purpose-Specific APIs

### Workbench Fields

Controls which columns appear in list views.

```typescript
import {
  getWorkbenchFieldsSetting,
  saveWorkbenchFieldsSetting,
  getAllWorkbenchFieldsSettings,
  SettingRecord,
} from '@/api/wcapi';

// Fetch for a specific model
const setting = await getWorkbenchFieldsSetting('order');
// setting.data.list = ['id', 'customer_name', 'order_date', ...]
// setting.data.detail = ['id', 'customer_name', ...]

// Fetch all workbench settings
const allSettings = await getAllWorkbenchFieldsSettings();

// Save
await saveWorkbenchFieldsSetting({
  id: setting?.id,
  model_name: 'order',
  purpose: 'workbench_fields',
  data: {
    list: ['id', 'customer_name', 'order_date', 'total'],
    detail: ['id', 'customer_name', 'order_date', 'ship_date', 'total'],
  },
});
```

**Interface:**
```typescript
interface SettingRecord {
  id?: number;
  model_name: string;
  purpose: string;
  data: {
    list: string[];
    detail: string[];
  };
}
```

---

### Detail Field Access

Controls field visibility and editability in detail/edit views.

```typescript
import {
  getDetailFieldSetting,
  saveDetailFieldSetting,
  DetailFieldSettingRecord,
} from '@/api/wcapi';

// Fetch
const setting = await getDetailFieldSetting('order');
// setting.data.hidden = ['internal_notes', 'legacy_id']
// setting.data.readOnly = ['created_at', 'order_number']

// Save
await saveDetailFieldSetting({
  id: setting?.id,
  model_name: 'order',
  purpose: 'detail_field_access',
  data: {
    hidden: ['internal_notes'],
    readOnly: ['created_at', 'order_number'],
  },
});
```

**Interface:**
```typescript
interface DetailFieldSettingRecord {
  id?: number;
  model_name: string;
  purpose: string;
  data: {
    hidden: string[];
    readOnly: string[];
  };
}
```

---

### Q&A Counters (Singleton)

Tracks auto-increment IDs for QuestionAnswer records.

```typescript
interface QACountersData {
  question_max: number;
  answer_max: number;
}

async function getQACounters(): Promise<QACountersData | null> {
  const res = await apiClient.get('/wcapi/get/', {
    params: {
      model_name: 'setting',
      purpose: 'qa_counters',
    },
  });
  const results = res.data.data.results || [];
  return results.length > 0 ? results[0].data : null;
}

// Usage
const counters = await getQACounters();
// counters.question_max = 45
// counters.answer_max = 124
```

> **Note:** Counter updates should be done server-side for atomicity. Frontend typically just reads.

---

### Q&A Questions (By Group)

Fetch question templates for a specific group (e.g., "Planning", "Prepress").

```typescript
interface QAQuestionTemplate {
  allow_freeform?: boolean;
  allow_multiple?: boolean;
  require_image?: boolean;
  image_max?: number;
  image_types?: string[];
}

interface QAQuestion {
  question_id: number;
  prompt: string;
  choices?: string[];
  allow_freeform?: boolean;
  allow_multiple?: boolean;
  require_image?: boolean;
}

interface QAQuestionsData {
  template: QAQuestionTemplate;
  questions: QAQuestion[];
}

async function getQAQuestions(groupName: string): Promise<QAQuestionsData | null> {
  const res = await apiClient.get('/wcapi/get/', {
    params: {
      model_name: 'setting',
      purpose: 'qa_questions',
      name: groupName,
    },
  });
  const results = res.data.data.results || [];
  return results.length > 0 ? results[0].data : null;
}

// Usage
const planningQuestions = await getQAQuestions('Planning');
// planningQuestions.template.allow_freeform = false
// planningQuestions.questions = [{ question_id: 1, prompt: 'Job Type?', ... }]
```

**Helper: Resolve Effective Options**

```typescript
const DEFAULTS: QAQuestionTemplate = {
  allow_freeform: false,
  allow_multiple: false,
  require_image: false,
  image_max: 3,
  image_types: ['jpg', 'png', 'pdf'],
};

function getEffectiveOptions(
  question: QAQuestion,
  template: QAQuestionTemplate
): Required<QAQuestionTemplate> {
  return {
    allow_freeform: question.allow_freeform ?? template.allow_freeform ?? DEFAULTS.allow_freeform!,
    allow_multiple: question.allow_multiple ?? template.allow_multiple ?? DEFAULTS.allow_multiple!,
    require_image: question.require_image ?? template.require_image ?? DEFAULTS.require_image!,
    image_max: template.image_max ?? DEFAULTS.image_max!,
    image_types: template.image_types ?? DEFAULTS.image_types!,
  };
}
```

---

### Admin Settings (Named Singletons)

Administrative settings are singletons keyed by `purpose='admin'` + `name`.
They hold shared configuration data for the frontend.

#### Popup Choices

Normalized legacy wc2 popup/choice lists for select dropdowns.

```typescript
interface PopupChoice {
  value: string;
  label: string;
  alternate: string;
  sequence: number;
}

interface PopupList {
  list_name: string;
  wc2_array_name: string;
  where_used: string;
  choices: PopupChoice[];
}

interface PopupChoicesData {
  meta: {
    source: string;
    created_at: string;
    total_lists: number;
    total_choices: number;
  };
  lists: Record<string, PopupList>;
}

async function getPopupChoices(): Promise<PopupChoicesData | null> {
  const res = await apiClient.get('/wcapi/get/', {
    params: {
      model_name: 'setting',
      purpose: 'admin',
      name: 'popup_choices',
    },
  });
  const results = res.data.data.results || [];
  return results.length > 0 ? results[0].data : null;
}

// Usage — populate a select list
const data = await getPopupChoices();
const statusOptions = data?.lists.status.choices ?? [];
// → [{ value: 'INVOICE', label: 'INVOICE' }, { value: 'APPROVED', ... }, ...]

const salutationOptions = data?.lists.salutation.choices ?? [];
// → [{ value: 'Ms', label: 'Ms' }, { value: 'Mrs.', ... }, ...]
```

**Key lists** (116 total, 209 choices): `status` (29), `actions` (12),
`type_sale` (6), `salutation` (4), `prospect` (5), `reasons` (4),
`activities` (4), `job_type` (7), `items_type` (6), `orders_profile1` (7)

#### Layout Status

Tracks which model layout files exist and their implementation status.

```typescript
interface LayoutEntry {
  app: string;
  model: string;
  detail_exists: boolean;
  list_exists: boolean;
  dialog_exists: boolean;
  panel_exists: boolean;
  detail_status: string;
  list_status: string;
  dialog_status: string;
  panel_status: string;
  assigned_to: string;
}

async function getLayoutStatus(): Promise<LayoutEntry[] | null> {
  const res = await apiClient.get('/wcapi/get/', {
    params: {
      model_name: 'setting',
      purpose: 'admin',
      name: 'layout_status',
    },
  });
  const results = res.data.data.results || [];
  return results.length > 0 ? results[0].data?.layouts : null;
}
```

See [layout-maintenance.md](../layout-maintenance.md) for full specification.

---

### Constants (Singleton)

Global user-defined constants.

```typescript
interface ConstantsData {
  tax_rate_default?: number;
  shipping_markup?: number;
  payment_terms_days?: number;
  [key: string]: any;
}

async function getConstants(): Promise<ConstantsData | null> {
  const res = await apiClient.get('/wcapi/get/', {
    params: {
      model_name: 'setting',
      purpose: 'constants',
    },
  });
  const results = res.data.data.results || [];
  return results.length > 0 ? results[0].data : null;
}

// Usage
const constants = await getConstants();
const taxRate = constants?.tax_rate_default ?? 0.0825;
```

---

### Database Defaults (Singleton)

Platform-wide defaults.

```typescript
interface DbDefaultsData {
  currency?: string;
  date_format?: string;
  timezone?: string;
}

async function getDbDefaults(): Promise<DbDefaultsData | null> {
  const res = await apiClient.get('/wcapi/get/', {
    params: {
      model_name: 'setting',
      purpose: 'db_defaults',
    },
  });
  const results = res.data.data.results || [];
  return results.length > 0 ? results[0].data : null;
}
```

---

### View/Edit Matrix (Per Model + Role)

Field-level permissions by role.

```typescript
interface FieldPermission {
  view: boolean;
  edit: boolean;
}

interface ViewEditData {
  fields: Record<string, FieldPermission>;
}

async function getViewEditMatrix(
  modelTarget: string,
  role: string
): Promise<ViewEditData | null> {
  const res = await apiClient.get('/wcapi/get/', {
    params: {
      model_name: 'setting',
      purpose: 'view_edit',
      model_name_filter: modelTarget,
      role: role,
    },
  });
  const results = res.data.data.results || [];
  return results.length > 0 ? results[0].data : null;
}

// Usage
const userPerms = await getViewEditMatrix('order', 'user');
if (userPerms?.fields.discount_pct?.edit === false) {
  // Disable discount field editing
}
```

---

## Generic Save

For saving any setting type:

```typescript
async function saveSetting(setting: {
  id?: number;
  purpose: string;
  model_target?: string;
  name?: string;
  role?: string;
  data: any;
}): Promise<any> {
  const res = await apiClient.post('/wcapi/save/', {
    model_name: 'setting',
    ...setting,
  });
  return res.data.data;
}

// Example: Save a new constants setting
await saveSetting({
  purpose: 'constants',
  data: {
    tax_rate_default: 0.0825,
    shipping_markup: 1.15,
  },
});
```

---

## Caching Strategy

Settings rarely change during a session. Consider caching:

```typescript
const settingsCache = new Map<string, any>();

async function getCachedSetting<T>(
  cacheKey: string,
  fetcher: () => Promise<T>
): Promise<T> {
  if (settingsCache.has(cacheKey)) {
    return settingsCache.get(cacheKey);
  }
  const result = await fetcher();
  settingsCache.set(cacheKey, result);
  return result;
}

// Usage
const constants = await getCachedSetting('constants', getConstants);
```

For React, use `@tanstack/react-query` with a long `staleTime`:

```typescript
import { useQuery } from '@tanstack/react-query';

function useConstants() {
  return useQuery({
    queryKey: ['settings', 'constants'],
    queryFn: getConstants,
    staleTime: 1000 * 60 * 30, // 30 minutes
  });
}
```

---

## Quick Reference

| Purpose               | Lookup Keys                        | Function                      |
|-----------------------|------------------------------------|-------------------------------|
| `workbench_fields`    | `model_target`                     | `getWorkbenchFieldsSetting()` |
| `detail_field_access` | `model_target`                     | `getDetailFieldSetting()`     |
| `view_edit`           | `model_target` + `role`            | `getViewEditMatrix()`         |
| `constants`           | *(singleton)*                      | `getConstants()`              |
| `db_defaults`         | *(singleton)*                      | `getDbDefaults()`             |
| `qa_counters`         | *(singleton)*                      | `getQACounters()`             |
| `qa_questions`        | `name` (group)                     | `getQAQuestions()`            |
| `admin`               | `name` (named singleton)           | `getPopupChoices()` / `getLayoutStatus()` |
| `keywords`            | `model_target`                     | *(generic fetch)*             |

---

## Related Files

| File | Description |
|------|-------------|
| [src/api/wcapi.ts](../../src/api/wcapi.ts) | Existing setting helpers |
| [src/api/axios.ts](../../src/api/axios.ts) | API client configuration |
| [webClerk3 Settings Reference](../../../webClerk3/readmes/topics/settings/settings_reference.md) | Backend schema docs |
| [layout-maintenance.md](../layout-maintenance.md) | Layout status detailed docs |
