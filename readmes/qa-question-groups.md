# QA Question Groups

QA question groups are template-based Q&A systems fetched from backend Settings. They support a 3-tier scoping system.

## Scope Levels

| Level | `parent_model` Value | Example | Shows For |
|-------|---------------------|---------|-----------|
| **Global** | `null` or empty | Planning, Prepress | All models |
| **App-level** | App name (e.g., `"transactions"`) | Transaction Review | All models in that app |
| **Model-specific** | Model name (e.g., `"order"`) | Order Checklist | Only that specific model |

## App Registry

Defined in `src/apps/common/components/panels/qaUtils.ts`:

```typescript
export const APP_MODEL_REGISTRY: Record<string, string[]> = {
  transactions: ['order', 'purchase', 'workorder', 'invoice', 'estimate', 'quote', 'receipt', 'payment'],
  contacts: ['customer', 'vendor', 'contact', 'employee', 'company'],
  inventory: ['item', 'inventory', 'location', 'warehouse', 'bin'],
  projects: ['project', 'task', 'milestone'],
  accounting: ['journal', 'gl_account', 'ledger', 'tax'],
};
```

## Components

### QATab

Transaction-specific tab component with group selector:

```tsx
import QATab from '@/apps/transactions/components/QATab';

<QATab
  transactionType="order"
  transactionId={22}
  canEdit={true}
/>
```

Features:
- Fetches groups scoped to the model
- Dropdown with optgroups (Model Only → All App → All Models)
- Auto-selects most specific group
- Persists answers to backend

### QAPanel

Reusable panel component for any context:

```tsx
import { QAPanel } from '@/apps/common/components/panels';

// Template mode with API persistence
<QAPanel
  questionGroup="Planning"
  parentModel="order"
  parentId={22}
  readOnly={false}
/>

// Freeform mode with local state
<QAPanel
  data={qaEntries}
  onChange={setQaEntries}
/>

// Hybrid mode (template + freeform)
<QAPanel
  questionGroup="Planning"
  parentModel="order"
  parentId={22}
  readOnly={false}
/>
```

## API Functions

### Fetching Groups

```typescript
import { 
  getAllQAQuestionGroups,
  getScopedQAQuestionGroups,
  getQAQuestions,
  getAppForModel,
} from '@/apps/common/components/panels';

// All groups
const allGroups = await getAllQAQuestionGroups();

// Scoped groups for a model
const scopedGroups = await getScopedQAQuestionGroups('order');
// Returns: { global: [...], appLevel: [...], modelSpecific: [...], all: [...] }

// Specific group by name
const planning = await getQAQuestions('Planning');

// Get app for a model
const app = getAppForModel('order'); // 'transactions'
```

### Fetching & Saving Answers

```typescript
import { getQAAnswers, saveQAAnswer, deleteQAAnswer, applyQuestionGroup } from '@/apps/common/components/panels';

// Apply a question group (create QA records for all questions)
const result = await applyQuestionGroup('Planning', 'order', 22);
// Returns: { success: true, created_count: 5, existing_count: 0, records: [...] }

// Get answers for a record
const answers = await getQAAnswers('order', 22);

// Save an answer
const saved = await saveQAAnswer({
  question: 'Payment terms verified?',
  answer: 'Yes',
  setting_id: 119,
  question_id: 1001,
  answer_id: 10001,
  parent_model: 'order',
  parent_id: 22,
  status: 'answered',
});

// Delete an answer
await deleteQAAnswer(answerId);
```

## Types

```typescript
interface QAQuestionsSetting {
  id: number;
  purpose: string;
  name: string;
  parent_model?: string;
  role?: string;
  data: QAQuestionsData;
}

interface QAQuestionsData {
  template: QAQuestionTemplate;
  questions: QAQuestionDef[];
}

interface QAQuestionTemplate {
  allow_freeform?: boolean;
  allow_multiple?: boolean;
  require_image?: boolean;
  image_max?: number;
  image_types?: string[];
}

interface QAQuestionDef {
  id: number;
  question: string;
  answers?: QAAnswerChoice[];
  allow_freeform?: boolean;
  allow_multiple?: boolean;
  require_image?: boolean;
}

interface QAAnswerChoice {
  id: number;
  answer: string;
}

interface QAAnswerRecord {
  id?: number;
  question: string;
  answer?: string;
  answers?: number[];  // For multiple select
  setting_id?: number;
  question_id?: number;
  answer_id?: number;
  parent_model: string;  // Model name of parent (e.g., 'order', 'customer')
  parent_id: number;
  status?: 'open' | 'answered' | 'closed';
}

interface ScopedQAGroups {
  global: QAQuestionsSetting[];
  appLevel: QAQuestionsSetting[];
  modelSpecific: QAQuestionsSetting[];
  all: QAQuestionsSetting[];
}
```

## UI Behavior

### Dropdown Organization

When viewing an order, the dropdown displays:

```
-- Select Group --
▼ Order Only           (groups with parent_model = "order")
    Order Checklist
▼ All Transactions     (groups with parent_model = "transactions")
    Transaction Review
▼ All Models           (groups with parent_model = null)
    Planning
    Prepress
    Press
    Finishing
    jitSetup
```

### Auto-Selection Priority

1. Model-specific groups (most specific)
2. App-level groups
3. Global groups (fallback)

### Answer Persistence

- **With `parentModel` + `parentId`**: Answers saved to `QuestionAnswer` model via API
- **Without**: Answers managed in local state via `onChange` callback

## Files

| File | Purpose |
|------|---------|
| `src/apps/common/components/panels/qaUtils.ts` | API functions, types, app registry |
| `src/apps/common/components/panels/QAPanel.tsx` | Reusable Q&A panel component |
| `src/apps/transactions/components/QATab.tsx` | Transaction-specific tab with group selector |
| `src/apps/common/components/panels/index.ts` | Barrel exports |

## Backend Setup

See `webClerk3/readmes/qa-question-groups.md` for:
- Creating question groups in Django
- Setting model data structure
- API endpoint details

## Future Enhancements

### QA Template Editor UI

**Status:** Planned for future review

**Current Approach:** QA question groups are created via backend Django shell or direct database operations. This is acceptable as template creation is a rare administrative task.

**Future Enhancement:** Build a React-based template editor that allows administrators to:
- Create new QA question groups visually
- Add/edit/delete/reorder questions via drag-and-drop
- Manage answer choices inline
- Set scope (global → app → model) with helper UI
- Configure template options with toggles/selects
- Live preview of the template
- Import/export JSON for backup

**Potential Location:** `src/apps/admin/settings/QATemplateEditor.tsx`

**Priority:** Low - manual JSON approach works for rare template changes

**When to Revisit:**
- When non-technical users need to create templates
- When template creation becomes frequent
- When building broader Settings management UI
