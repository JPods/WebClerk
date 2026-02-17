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
| `keywords`            | `model_target`                     | *(generic fetch)*             |

---

## Related Files

| File | Description |
|------|-------------|
| [src/api/wcapi.ts](../../src/api/wcapi.ts) | Existing setting helpers |
| [src/api/axios.ts](../../src/api/axios.ts) | API client configuration |
| [webClerk3 Settings Reference](../../../webClerk3/readmes/topics/settings/settings_reference.md) | Backend schema docs |
