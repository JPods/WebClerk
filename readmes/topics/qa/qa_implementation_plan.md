# Q&A Implementation Plan

## Overview

This document outlines the implementation plan for the Question/Answer (Q&A) system across webClerk3 (wc3) and React2025 (r25). The system allows users to attach Q&A entries to various records through the QAPanel component.

> **See also:** [Settings Reference](../settings/settings_reference.md) for general Setting model documentation and other purpose types.

---

## 1. Core Components

### 1.1 Data Models

#### Setting Record: `qa_counters` (Singleton)

A **single** Setting record tracks the maximum IDs for questions and answers globally:

```json
{
  "purpose": "qa_counters",
  "model_target": "question_answer",
  "role": "all",
  "name": "counters",
  "security_level": 1,
  "is_active": true,
  "data": {
    "question_max": 45,
    "answer_max": 124
  }
}
```

**Rules:**
- Only ONE record with `purpose = "qa_counters"` may exist
- Enforce via Django model validation or database constraint
- When a new Q&A is saved, atomically increment `question_max` or `answer_max`

#### Setting Records: `qa_questions` (Question Templates)

Each question group is stored as a Setting record with a `template` object defining group-level defaults:

```json
{
  "purpose": "qa_questions",
  "model_target": "all",  // or "app_name" or "model_name"
  "role": "all",
  "name": "Planning",
  "security_level": 1,
  "is_active": true,
  "data": {
    "template": {
      "allow_freeform": false,    // Group default: allow text input
      "allow_multiple": false,    // Group default: allow multiple answers
      "require_image": false,     // Group default: require image upload
      "image_max": 5,             // Max images per question (when images allowed)
      "image_types": ["jpg", "png", "webp"]  // Allowed image extensions
    },
    "questions": [
      {
        "id": 11,
        "question": "Imposition",
        "answers": [
          {"id": 124, "answer": "Divorced"},
          {"id": 125, "answer": "Married"}
        ]
        // Uses template defaults (no overrides)
      },
      {
        "id": 12,
        "question": "Site inspection notes",
        "allow_freeform": true,   // Override: enable freeform for this question
        "require_image": true,    // Override: require image for this question
        "answers": []             // No predefined answers, freeform only
      },
      {
        "id": 13,
        "question": "Select all that apply",
        "allow_multiple": true,   // Override: enable multi-select
        "answers": [
          {"id": 127, "answer": "Option A"},
          {"id": 128, "answer": "Option B"},
          {"id": 129, "answer": "Option C"}
        ]
      }
    ]
  }
}
```

**Template Schema (Group Defaults):**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `allow_freeform` | boolean | false | Allow free-text input |
| `allow_multiple` | boolean | false | Allow selecting multiple answers |
| `require_image` | boolean | false | Require image upload with answer |
| `image_max` | integer | 5 | Maximum images allowed per answer |
| `image_types` | string[] | ["jpg","png","webp"] | Allowed image file extensions |

**Question-Level Overrides:**

Individual questions inherit from `template` but can override any setting:

```
effective_value = question.option ?? template.option ?? default
```

| Override | Behavior |
|----------|----------|
| Not specified | Uses template default |
| `true` | Enables for this question only |
| `false` | Disables for this question only |

#### QuestionAnswer Model (Existing)

Records user answers linked to parent records:

| Field | Description |
|-------|-------------|
| `question` | The question text (snapshot) |
| `answer` | The answer text (for freeform or single select) |
| `answers` | JSON array of selected answer_ids (for multiple select) |
| `setting_id` | FK to Setting (question template) |
| `question_id` | ID of the question within Setting |
| `answer_id` | ID of selected answer option (single select) |
| `answered_by` | JSON: `{id, attention}` |
| `parent_type` | Model name of parent record |
| `parent_id` | ID of parent record |
| `status` | open/answered/closed |
| `sequence` | Display order |
| `metadata` | JSON: stores `images` array with uploaded image paths |

**Image Storage in metadata:**

When `require_image` is true (or user optionally uploads images), store paths in `metadata.images`:

```json
{
  "metadata": {
    "images": [
      {
        "path": "qa/<parent_type>/<parent_id>/<qa_id>_1.jpg",
        "filename": "inspection_photo.jpg",
        "uploaded_at": "2026-02-05T10:30:00Z",
        "uploaded_by": 123
      }
    ],
    "history": { ... }
  }
}
```

**Image Upload Path Convention:**
```
static/images/qa/<parent_type>/<parent_id>/<question_answer_id>_<sequence>.<ext>
```

---

## 2. WebClerk3 (wc3) Implementation

### 2.1 Uniqueness Constraint for `qa_counters`

Add validation in `Setting.clean()` and/or database constraint:

```python
# apps/core/models/setting.py

def clean(self):
    super().clean()
    
    # ... existing validation ...
    
    # Enforce singleton for qa_counters
    if self.purpose == 'qa_counters':
        existing = Setting.objects.filter(
            purpose='qa_counters', 
            is_active=True
        ).exclude(pk=self.pk)
        if existing.exists():
            raise ValidationError({
                'purpose': 'Only one active qa_counters setting record is allowed.'
            })
```

### 2.2 Auto-increment ID Logic

When saving new Q&A records with raw question/answer data:

```python
# apps/docs/models/question_answer.py or services/qa_service.py

from django.db import transaction
from apps.core.models import Setting
from apps.core.models import Pending
from django.db.models import F

def save_qa_with_counters(qa_instance, is_new_question=False, is_new_answer=False):
    """
    Atomically increment qa_counters and create pending signal.
    """
    with transaction.atomic():
        counter = Setting.objects.select_for_update().get(purpose='qa_counters')
        counter_data = counter.data or {}
        
        if is_new_question:
            new_q_id = counter_data.get('question_max', 0) + 1
            counter_data['question_max'] = new_q_id
            qa_instance.question_id = new_q_id
        
        if is_new_answer:
            new_a_id = counter_data.get('answer_max', 0) + 1
            counter_data['answer_max'] = new_a_id
            qa_instance.answer_id = new_a_id
        
        counter.data = counter_data
        counter.save()
        
        qa_instance.save()
        
        # Create pending record to notify R25
        Pending.objects.create(
            table_name='question_answer',
            record_id=qa_instance.id,
            action='update_qa_counters',
            data={
                'question_max': counter_data.get('question_max'),
                'answer_max': counter_data.get('answer_max'),
                'question_answer_id': qa_instance.id
            }
        )
        
        # Send signal (optional - for WebSocket/real-time updates)
        # qa_counters_updated.send(sender=Setting, counters=counter_data)
```

### 2.3 Add Purpose Choice

```python
# apps/core/choices.py

SETTING_PURPOSE_CHOICES = [
    # ... existing choices ...
    ('qa_counters', 'Q&A Counters'),
    ('qa_questions', 'Q&A Question Templates'),
]
```

### 2.4 API Endpoints

Create or update viewset to support:

```
GET  /api/settings/?purpose=qa_counters
GET  /api/settings/?purpose=qa_questions&model_target=<target>
POST /api/question_answers/  (auto-increments counters)
```

**Filter logic for qa_questions:**
- `model_target = "all"` → applies to all models
- `model_target = "<app_name>"` → applies to all models in that app
- `model_target = "<model_name>"` → applies only to that specific model

---

## 3. React2025 (r25) Implementation

### 3.1 QA Context/Store

Create a context or Zustand store to cache qa_counters:

```typescript
// src/apps/common/stores/qaStore.ts

interface QACounters {
  question_max: number;
  answer_max: number;
}

interface QAStore {
  counters: QACounters | null;
  questionTemplates: Record<string, QAQuestionTemplate[]>;
  isLoading: boolean;
  
  loadCounters: () => Promise<void>;
  loadQuestionsForModel: (modelTarget: string) => Promise<void>;
  refresh: () => Promise<void>;
}

export const useQAStore = create<QAStore>((set, get) => ({
  counters: null,
  questionTemplates: {},
  isLoading: false,
  
  loadCounters: async () => {
    set({ isLoading: true });
    const response = await apiClient.get('/api/settings/', {
      params: { purpose: 'qa_counters' }
    });
    const counterRecord = response.data.results?.[0];
    set({ 
      counters: counterRecord?.data || { question_max: 0, answer_max: 0 },
      isLoading: false 
    });
  },
  
  loadQuestionsForModel: async (modelTarget: string) => {
    // Fetch templates for: "all", app_name, and model_name
    const app = getAppFromModel(modelTarget);
    const targets = ['all', app, modelTarget].filter(Boolean);
    
    const response = await apiClient.get('/api/settings/', {
      params: { 
        purpose: 'qa_questions',
        model_target__in: targets.join(',')
      }
    });
    
    set(state => ({
      questionTemplates: {
        ...state.questionTemplates,
        [modelTarget]: response.data.results
      }
    }));
  },
  
  refresh: async () => {
    await get().loadCounters();
  }
}));
```

### 3.2 Resolve Effective Question Options

Helper to merge template defaults with question-level overrides:

```typescript
// src/apps/common/utils/qaUtils.ts

interface QATemplate {
  allow_freeform?: boolean;
  allow_multiple?: boolean;
  require_image?: boolean;
  image_max?: number;
  image_types?: string[];
}

interface Question {
  id: number;
  question: string;
  allow_freeform?: boolean;
  allow_multiple?: boolean;
  require_image?: boolean;
  answers?: { id: number; answer: string }[];
}

const DEFAULT_TEMPLATE: QATemplate = {
  allow_freeform: false,
  allow_multiple: false,
  require_image: false,
  image_max: 5,
  image_types: ['jpg', 'png', 'webp']
};

/**
 * Resolve effective options for a question by merging:
 * default → template → question override
 */
export function getEffectiveOptions(
  question: Question, 
  template?: QATemplate
): Required<QATemplate> {
  return {
    allow_freeform: question.allow_freeform ?? template?.allow_freeform ?? DEFAULT_TEMPLATE.allow_freeform!,
    allow_multiple: question.allow_multiple ?? template?.allow_multiple ?? DEFAULT_TEMPLATE.allow_multiple!,
    require_image: question.require_image ?? template?.require_image ?? DEFAULT_TEMPLATE.require_image!,
    image_max: template?.image_max ?? DEFAULT_TEMPLATE.image_max!,
    image_types: template?.image_types ?? DEFAULT_TEMPLATE.image_types!,
  };
}

// Usage in component:
// const options = getEffectiveOptions(question, settingRecord.data.template);
// if (options.allow_freeform) { /* show textarea */ }
```

### 3.3 Load on App Init

```typescript
// src/App.tsx or src/hooks/useAppInit.ts

useEffect(() => {
  // Load QA counters on app initialization
  useQAStore.getState().loadCounters();
}, []);
```

### 3.3 QAPanel Enhancements

Update QAPanel to:
1. **Require parent record ID** before allowing Q&A operations
2. **Load available question templates** based on model targeting
3. **Show template selector** when adding new Q&A

```tsx
// src/apps/common/components/panels/QAPanel.tsx

interface QAPanelProps extends Omit<BasePanelProps<QAEntry[]>, 'data'> {
  data?: QAEntry[];
  parent_id?: number | null;  // Required for saving
  modelName: string;          // e.g., 'contact', 'customer'
  appName?: string;           // e.g., 'accounts', 'transactions'
}

const QAPanel: React.FC<QAPanelProps> = ({
  parent_id,
  modelName,
  appName,
  data = [],
  onChange,
  ...props
}) => {
  const { counters, questionTemplates, loadQuestionsForModel } = useQAStore();
  const [templates, setTemplates] = useState<QAQuestionTemplate[]>([]);
  
  // Check if parent record is saved
  const canAddQA = parent_id != null && parent_id > 0;
  
  // Load question templates for this model
  useEffect(() => {
    if (modelName) {
      loadQuestionsForModel(modelName);
    }
  }, [modelName]);
  
  // Build merged template list (all + app + model)
  useEffect(() => {
    const allTemplates = questionTemplates[modelName] || [];
    setTemplates(allTemplates);
  }, [questionTemplates, modelName]);
  
  // Render warning if parent not saved
  if (!canAddQA) {
    return (
      <div className="bg-amber-50 dark:bg-amber-900/20 p-4 rounded-lg border border-amber-200">
        <p className="text-sm text-amber-700 dark:text-amber-300">
          Please save the record before adding Q&A entries.
        </p>
      </div>
    );
  }
  
  // ... rest of existing implementation with template selector
};
```

### 3.4 Template Selector Component

```tsx
// New component for selecting question templates

interface TemplateSelectProps {
  templates: QAQuestionTemplate[];
  onSelect: (template: QAQuestionTemplate, question: Question) => void;
}

const TemplateSelect: React.FC<TemplateSelectProps> = ({ templates, onSelect }) => {
  const [selectedGroup, setSelectedGroup] = useState<string>('');
  
  // Group templates by scope: all → app → model
  const groupedTemplates = useMemo(() => ({
    all: templates.filter(t => t.model_target === 'all'),
    app: templates.filter(t => t.model_target && !['all'].includes(t.model_target) && !isModelName(t.model_target)),
    model: templates.filter(t => isModelName(t.model_target))
  }), [templates]);
  
  return (
    <div className="space-y-2">
      <select 
        value={selectedGroup}
        onChange={(e) => setSelectedGroup(e.target.value)}
        className="w-full px-2 py-1.5 text-sm border rounded"
      >
        <option value="">-- Select Question Group --</option>
        <optgroup label="All Models">
          {groupedTemplates.all.map(t => (
            <option key={t.name} value={t.name}>{t.name}</option>
          ))}
        </optgroup>
        {/* Similar for app and model groups */}
      </select>
    </div>
  );
};
```

### 3.5 Answer Input Component (Handles All Modes)

```tsx
// Component that renders appropriate input based on question options

interface AnswerInputProps {
  question: Question;
  value: AnswerValue;
  onChange: (value: AnswerValue) => void;
  images: ImageUpload[];
  onImageUpload: (files: File[]) => void;
  onImageRemove: (index: number) => void;
}

interface AnswerValue {
  answer_id?: number;           // Single select
  answer_ids?: number[];        // Multiple select (when allow_multiple)
  freeform_text?: string;       // Free text (when allow_freeform)
}

const AnswerInput: React.FC<AnswerInputProps> = ({
  question,
  value,
  onChange,
  images,
  onImageUpload,
  onImageRemove
}) => {
  const { allow_freeform, allow_multiple, require_image, answers } = question;
  
  return (
    <div className="space-y-3">
      {/* Predefined answers - radio or checkbox based on allow_multiple */}
      {answers?.length > 0 && (
        <div className="space-y-1">
          {answers.map(ans => (
            <label key={ans.id} className="flex items-center gap-2 text-sm">
              <input
                type={allow_multiple ? 'checkbox' : 'radio'}
                name={`q_${question.id}`}
                checked={allow_multiple 
                  ? value.answer_ids?.includes(ans.id)
                  : value.answer_id === ans.id
                }
                onChange={(e) => {
                  if (allow_multiple) {
                    const ids = value.answer_ids || [];
                    onChange({
                      ...value,
                      answer_ids: e.target.checked 
                        ? [...ids, ans.id]
                        : ids.filter(id => id !== ans.id)
                    });
                  } else {
                    onChange({ ...value, answer_id: ans.id });
                  }
                }}
              />
              {ans.answer}
            </label>
          ))}
        </div>
      )}
      
      {/* Free-form text input when allowed */}
      {allow_freeform && (
        <textarea
          value={value.freeform_text || ''}
          onChange={(e) => onChange({ ...value, freeform_text: e.target.value })}
          placeholder="Enter additional details..."
          className="w-full px-2 py-1.5 text-sm border rounded"
          rows={2}
        />
      )}
      
      {/* Image upload section */}
      {(require_image || images.length > 0) && (
        <div className="space-y-2">
          <label className="block text-xs text-slate-600">
            {require_image ? 'Image Required *' : 'Attach Images (optional)'}
          </label>
          
          {/* Display uploaded images */}
          {images.length > 0 && (
            <div className="flex gap-2 flex-wrap">
              {images.map((img, idx) => (
                <div key={idx} className="relative w-16 h-16">
                  <img src={img.preview || img.path} className="w-full h-full object-cover rounded" />
                  <button
                    onClick={() => onImageRemove(idx)}
                    className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full w-4 h-4 text-xs"
                  >×</button>
                </div>
              ))}
            </div>
          )}
          
          {/* Upload button */}
          <input
            type="file"
            accept="image/*"
            multiple
            onChange={(e) => e.target.files && onImageUpload(Array.from(e.target.files))}
            className="text-xs"
          />
        </div>
      )}
    </div>
  );
};
```

---

## 4. Database Migration

### 4.1 Create Initial qa_counters Record

```python
# Migration file: 0029_create_qa_counters.py

from django.db import migrations

def create_qa_counters(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    
    # Only create if doesn't exist
    if not Setting.objects.filter(purpose='qa_counters').exists():
        Setting.objects.create(
            purpose='qa_counters',
            model_target='question_answer',
            role='all',
            name='counters',
            security_level=1,
            is_active=True,
            data={
                'question_max': 45,  # From qa.json
                'answer_max': 124    # From qa.json
            }
        )

def reverse_qa_counters(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    Setting.objects.filter(purpose='qa_counters').delete()

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0028_previous_migration'),
    ]

    operations = [
        migrations.RunPython(create_qa_counters, reverse_qa_counters),
    ]
```

---

## 5. Validation Rules Summary

| Rule | Location | Enforcement |
|------|----------|-------------|
| Only one `qa_counters` record | Setting.clean() | ValidationError |
| parent_id must exist (record saved) | QAPanel (R25) | UI gate + API validation |
| Question/Answer IDs auto-increment | qa_service.py | Atomic transaction |
| model_target must be valid | Setting.clean() | Existing validation |
| Image required when `require_image=true` | API + QAPanel | 400 error if missing |
| Image count ≤ `template.image_max` | API + QAPanel | Reject excess uploads |
| Image type in `template.image_types` | API + QAPanel | 400 error if invalid type |
| Multiple answers stored as array | QuestionAnswer.answers | JSON array of answer_ids |
| Options resolve: question → template → default | getEffectiveOptions() | Utility function |

---

## 6. Implementation Checklist

### WebClerk3

- [ ] Add `qa_counters` and `qa_questions` to `SETTING_PURPOSE_CHOICES`
- [ ] Add singleton validation in `Setting.clean()`
- [ ] Validate `data.template` schema for `qa_questions` purpose
- [ ] Create `qa_service.py` with auto-increment logic
- [ ] Add `parent_type` and `parent_id` fields to QuestionAnswer model if missing
- [ ] Add `answers` JSON field for multiple selections
- [ ] Add image upload endpoint for QA images
- [ ] Validate image count and types on upload
- [ ] Store image paths in `metadata.images`
- [ ] Create migration for initial `qa_counters` record
- [ ] Update API viewsets for QA operations
- [ ] Add tests for counter increment and singleton constraint

### React2025

- [ ] Create `qaStore.ts` with counters and template management
- [ ] Create `qaUtils.ts` with `getEffectiveOptions()` helper
- [ ] Update QAPanel to require `parent_id`
- [ ] Add "save record first" warning message
- [ ] Implement template selector component
- [ ] Support freeform text input when `allow_freeform=true`
- [ ] Support multi-select checkboxes when `allow_multiple=true`
- [ ] Implement image upload component when `require_image=true`
- [ ] Validate image count against `image_max`
- [ ] Validate image types against `image_types`
- [ ] Display uploaded images in QA item view
- [ ] Load counters on app initialization
- [ ] Add refresh mechanism for counters
- [ ] Update QAEntry types with parent_type/parent_id

---

## 7. QA.json Reference

The existing `qa.json` provides the initial question bank. Each top-level key (Planning, Prepress, etc.) contains:

1. A `setting` object defining the template metadata
2. A `template` object with group-level defaults (optional)
3. An array of question objects with nested answer arrays
4. Pre-assigned `id` values for both questions and answers

**Complete Setting Structure:**
```json
{
  "Planning": [
    {
      "setting": {
        "purpose": "qa_questions",
        "model_target": "all",
        "role": "all",
        "name": "Planning",
        "security_level": 1,
        "is_active": true
      },
      "template": {
        "allow_freeform": false,
        "allow_multiple": false,
        "require_image": false,
        "image_max": 5,
        "image_types": ["jpg", "png", "webp"]
      }
    },
    {
      "id": 11,
      "question": "Imposition",
      "answers": [{"id": 124, "answer": "Divorced"}, ...]
    },
    ...
  ]
}
```

**Current max values from qa.json:**
- `question_max`: 45
- `answer_max`: 124 (approximately)

---

## 8. Signal/Event Flow

```
User adds Q&A in R25
        ↓
API POST /api/question_answers/
        ↓
wc3: qa_service.save_qa_with_counters()
        ↓
┌───────────────────────────────────────┐
│ Transaction:                          │
│  1. SELECT FOR UPDATE qa_counters     │
│  2. Increment question_max/answer_max │
│  3. Save Setting record               │
│  4. Save QuestionAnswer record        │
│  5. Create Pending record             │
└───────────────────────────────────────┘
        ↓
WebSocket/Polling picks up Pending
        ↓
R25: useQAStore.refresh()
```

---

## 9. Notes

- The `qa.json` file serves as the source of truth for question templates
- Import `qa.json` to create initial Setting records via migration or management command
- Consider caching question templates in R25 to reduce API calls
- The parent_id requirement applies to ALL panels that relate records (comments, attachments, etc.)
- Images are stored on disk at `static/images/qa/<parent_type>/<parent_id>/`
- Image metadata (path, filename, upload info) stored in `QuestionAnswer.metadata.images[]`
- When a QuestionAnswer is deleted, associated images should also be cleaned up
