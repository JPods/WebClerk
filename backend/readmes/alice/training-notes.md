# Training Notes & Guided Spotlight System

**Built:** 2026-09-04  
**Purpose:** Interactive training system — users give feedback, Alice guides them through workflows.

---

## Quick Reference — Keyboard Shortcuts

| Shortcut | What it does |
|----------|-------------|
| **Cmd+Shift+T** | Open Training Note dialog (`tn-` pre-populated) |
| **Cmd+Shift+S** | Flash/spotlight the element under your cursor |
| **Cmd+/** | Open Get Help dialog (paste element for context help) |
| **Cmd+Enter** | Submit (in any dialog textarea) |

---

## Part 1: Training Notes (tn-)

### How It Works

While watching a training video or working through a new feature, press **Cmd+Shift+T** to open the Training Note dialog. The textarea pre-populates with `tn- ` — type your observation and press **Cmd+Enter** to submit.

Alice receives every training note as an `AiMessage` record. She tracks frequency by page and element to identify **bramble bushes** — areas where users repeatedly get confused.

### Three Entry Points

| Method | What happens |
|--------|-------------|
| **Cmd+Shift+T** | Opens Training Note dialog with `tn-` pre-populated |
| **Help dropdown → Training Note** | Same dialog, same behavior |
| **Any feedback starting with `tn-`** | Regular Help dialog (Cmd+/) also tags it |

### What to Write

Keep notes short. Say what confused you, not what you think the fix should be:

```
tn- can't find where to add a new contact from this page
tn- expected the save button to be at the top, not bottom
tn- search didn't return the item I know exists — tried "widget"
tn- not clear which fields are required vs optional
tn- clicked the wrong thing — thought the label was a button
```

### How Alice Uses Training Notes

Every `tn-` message creates an `AiMessage` record:

| Field | Value |
|-------|-------|
| `kind` | `feedback` |
| `sender` | `user` |
| `receiver` | `alice` |
| `subject` | `Training Note: /current/page/path` |
| `context.training_note` | `true` |
| `context.page` | Current URL path |

Pattern detection:
- **5+ notes on one page in 2 weeks** → content review trigger
- **Same observation from multiple users** → systemic issue
- **Cluster after a deploy** → new feature may need better onboarding

---

## Part 2: Manual Spotlight (Cmd+Shift+S)

### For Training Videos

While recording a training video, hover over any UI component and press **Cmd+Shift+S**. The component flashes with a blue glow pulse for 1 second — visible on video, draws the viewer's eye to exactly what you're about to discuss.

The spotlight walks up from whatever element is under your cursor to the nearest `data-wc` ancestor, so it highlights the meaningful component (the search bar, not the input's inner span).

Every spotlight event is logged as an `AiMessage(kind='help_lookup', subject='spotlight:<wc-id>')` so Alice can track which components trainers emphasize most.

### From the Browser Console

Developers and Alice can flash any component programmatically:

```javascript
// Flash a single element
wcSpotlight.flash('db-search', 'Search here')

// Flash without a hint
wcSpotlight.flash('db-model-picker')
```

---

## Part 3: Alice-Guided Spotlight Sequences

### The Big Idea

Alice can lead new users through any workflow by flashing elements one at a time. Each step highlights the next element to interact with, shows a hint, and waits for the user to act before advancing.

No separate tutorial mode. No overlay. No popover walkthrough. The actual UI element glows — the user does real actions on real data with Alice guiding them.

### Running a Sequence

**From the Alice Dashboard (Training tab):**
- Open the **Guided Spotlight** section
- Click any sequence — Alice starts flashing elements in order
- Follow the highlights
- Click **Stop** to cancel

**From the browser console:**
```javascript
wcSpotlight.run([
  { wc: 'db-model-picker', hint: 'Pick a model', wait: 'click' },
  { wc: 'db-search', hint: 'Type to search', wait: 'input' },
  { wc: 'db-list-pane', hint: 'Click a row', wait: 'click' },
])

// Stop a running sequence
wcSpotlight.stop()
```

### Step Options

| Field | Type | Description |
|-------|------|-------------|
| `wc` | string | `data-wc` value of the element to flash |
| `hint` | string | Text shown above the element (optional) |
| `wait` | `'click'` / `'input'` / `'time'` | What advances to the next step (default: `'time'`) |
| `delay` | number | Milliseconds to wait if `wait='time'` (default: 3000) |

### Built-in Sequences

| Name | Steps |
|------|-------|
| Find a Record | Model picker → search → select row |
| Create a Record | + New → fill fields → save |
| Change Layout | List Order → rearrange → save layout |
| Get Help | Shift+hover → copy tag → paste in Help |

### Adding New Sequences

Create a Document record with `ida` prefix `SPOTLIGHT-*`. Store the steps array in the document body as JSON. Alice Dashboard will load them automatically (future enhancement).

---

## Part 4: Reward System (Planned)

Users who create training videos earn recognition based on measurable impact:

1. User submits a training video → Action record created
2. Alice measures `tn-` note frequency for that page before and after
3. Fewer bramble bushes after = effective training = reward earned

The reward is for making confusion go away, not for making a video.

---

## For Alice — Pattern Queries

Training notes:
```sql
SELECT * FROM ai_message
WHERE kind = 'feedback' AND context->>'training_note' = 'true'
ORDER BY dt_created DESC;
```

Bramble bushes (hotspots):
```sql
SELECT context->>'page' AS page, COUNT(*) AS notes
FROM ai_message
WHERE kind = 'feedback' AND context->>'training_note' = 'true'
GROUP BY context->>'page'
ORDER BY notes DESC;
```

Spotlight frequency (what trainers emphasize):
```sql
SELECT context->>'wc_id' AS component, context->>'mode' AS mode, COUNT(*) AS flashes
FROM ai_message
WHERE kind = 'help_lookup' AND context->>'spotlight' = 'true'
GROUP BY context->>'wc_id', context->>'mode'
ORDER BY flashes DESC;
```

---

## Connection to Onboarding Doctrine

The feature is not done until the trail is packed. Training notes tell us where the trail has bramble bushes. The spotlight shows users where to step. Alice watches both signals — confusion frequency and trainer emphasis — and uses the gap between them to identify where training exists but isn't working vs. where training doesn't exist at all.

This is the flight simulator doctrine: real UI, real data, real actions. Alice guides. Users learn by doing, not by reading.

---

## Files

| File | What |
|------|------|
| `frontend/src/utils/spotlight.ts` | Core spotlight utility — flash, guided sequences, logging |
| `frontend/src/App.tsx` | Enables manual spotlight globally, exposes `wcSpotlight` API |
| `frontend/src/components/common/GetHelpDialog.tsx` | TrainingNoteForm component |
| `frontend/src/components/common/HelpMenu.tsx` | Cmd+Shift+T and Cmd+Shift+S shortcuts |
| `frontend/src/pages/admin/AliceDashboard.tsx` | SpotlightPanel in Training tab |
| `frontend/src/apps/docs/models/document/services/documentApi.ts` | submitFeedback with training flag |
| `backend/readmes/alice/training-notes.md` | This file |
