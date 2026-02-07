# QA Question Groups

QA question groups are defined in the `Setting` model with `purpose='qa_questions'`. They support a 3-tier scoping system to control which models see which questions.

## Scope Levels

| Level | `model_target` Value | Example | Shows For |
|-------|---------------------|---------|-----------|
| **Global** | `null` or empty | Planning, Prepress | All models |
| **App-level** | App name (e.g., `"transactions"`) | Transaction Review | All models in that app |
| **Model-specific** | Model name (e.g., `"order"`) | Order Checklist | Only that specific model |

## App Registry

The following apps and their models are recognized:

| App | Models |
|-----|--------|
| `transactions` | order, purchase, workorder, invoice, estimate, quote, receipt, payment |
| `contacts` | customer, vendor, contact, employee, company |
| `inventory` | item, inventory, location, warehouse, bin |
| `projects` | project, task, milestone |
| `accounting` | journal, gl_account, ledger, tax |

## Creating Question Groups

### Global Group (all models)

```python
from apps.core.models.setting import Setting

Setting.objects.create(
    purpose='qa_questions',
    name='General Checklist',
    model_target=None,  # or omit entirely
    data={
        'template': {
            'allow_freeform': True,
            'allow_multiple': False,
            'require_image': False,
        },
        'questions': [
            {
                'id': 1,
                'question': 'Is this approved?',
                'answers': [
                    {'id': 101, 'answer': 'Yes'},
                    {'id': 102, 'answer': 'No'},
                    {'id': 103, 'answer': 'Pending'},
                ]
            },
        ]
    }
)
```

### App-level Group (all transaction models)

```python
Setting.objects.create(
    purpose='qa_questions',
    name='Transaction Review',
    model_target='transactions',  # Applies to order, purchase, workorder, etc.
    data={
        'template': {'allow_freeform': True},
        'questions': [
            {
                'id': 1,
                'question': 'Customer notified?',
                'answers': [
                    {'id': 101, 'answer': 'Yes'},
                    {'id': 102, 'answer': 'No'},
                ]
            },
        ]
    }
)
```

### Model-specific Group (orders only)

```python
Setting.objects.create(
    purpose='qa_questions',
    name='Order Checklist',
    model_target='order',  # Only shows for orders
    data={
        'template': {'allow_freeform': True},
        'questions': [
            {
                'id': 1,
                'question': 'Payment terms verified?',
                'answers': [
                    {'id': 101, 'answer': 'Yes'},
                    {'id': 102, 'answer': 'No'},
                    {'id': 103, 'answer': 'N/A'},
                ]
            },
        ]
    }
)
```

## Data Structure

### Setting.data Schema

```json
{
  "template": {
    "allow_freeform": true,
    "allow_multiple": false,
    "require_image": false,
    "image_max": 5,
    "image_types": ["jpg", "png", "webp", "pdf"]
  },
  "questions": [
    {
      "id": 1,
      "question": "Question text",
      "answers": [
        {"id": 101, "answer": "Answer choice 1"},
        {"id": 102, "answer": "Answer choice 2"}
      ],
      "allow_freeform": false,
      "allow_multiple": false,
      "require_image": false
    }
  ]
}
```

### Template Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `allow_freeform` | boolean | false | Allow text input in addition to choices |
| `allow_multiple` | boolean | false | Allow selecting multiple answers |
| `require_image` | boolean | false | Require image attachment |
| `image_max` | integer | 5 | Maximum images per question |
| `image_types` | string[] | ["jpg","png","webp","pdf"] | Allowed file extensions |

Question-level options override template defaults.

## API Endpoints

### Fetch Question Groups

```
GET /wcapi/get/?model_name=setting&purpose=qa_questions
GET /wcapi/get/?model_name=setting&purpose=qa_questions&name=Planning
GET /wcapi/get/?model_name=setting&purpose=qa_questions&model_target=order
```

### Fetch Answers for a Record

```
GET /wcapi/get/?model_name=question_answer&parent_type=order&parent_id=22
```

### Save Answer

```
POST /wcapi/save/
{
  "model_name": "question_answer",
  "record": {
    "question": "Payment terms verified?",
    "answer": "Yes",
    "setting_id": 119,
    "question_id": 1001,
    "answer_id": 10001,
    "parent_type": "order",
    "parent_id": 22,
    "status": "answered"
  }
}
```

## Existing Groups

Current question groups in the database:

| ID | Name | Scope | Questions |
|----|------|-------|-----------|
| 113 | Planning | Global | 12 |
| 114 | Prepress | Global | 4 |
| 115 | Press | Global | 7 |
| 116 | Finishing | Global | 1 |
| 117 | jitSetup | Global | 6 |
| 119 | order_qa | Global | 5 |

## Frontend Usage

The `QATab` component in React automatically:
1. Fetches all question groups
2. Filters by scope (model > app > global)
3. Displays grouped dropdown with optgroups
4. Auto-selects the most specific group available

```tsx
<QATab
  transactionType="order"
  transactionId={22}
  canEdit={true}
/>
```

Dropdown display:
```
-- Select Group --
▼ Order Only           (model_target = "order")
▼ All Transactions     (model_target = "transactions")  
▼ All Models           (model_target = null)
```

## Future Enhancements

### QA Template Editor UI

**Status:** Planned for future review

**Current Approach:** QA question groups are created via Django shell or direct database insert with JSON data. This is acceptable for now as template creation is a rare administrative task.

**Temporary Workaround:** Administrators can provide question group JSON which can be inserted via:
```python
Setting.objects.create(
    purpose='qa_questions',
    name='New Template',
    model_target='order',  # or app name or null for global
    data=provided_json
)
```

**Future Enhancement:** Build a Settings admin UI in React that allows:
- Creating new QA question groups
- Adding/editing/reordering questions
- Managing answer choices
- Setting scope (global/app/model)
- Configuring template options (freeform, multiple select, image requirements)
- Previewing the template before saving

**Priority:** Low - current manual process is adequate for rare template changes

**Related:** Consider integrating with existing Settings management when building admin tools
