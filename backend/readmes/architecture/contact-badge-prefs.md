# Contact Badge Preferences

> Staff members can customize their badge appearance in Gantt charts and other UI components.

## Overview

The `contact.prefs.badge` object allows staff contacts to customize how their initials badge is displayed in:
- Gantt chart task bars
- Kanban cards (future)
- Any UI showing assignee badges

## Schema

```json
{
  "prefs": {
    "badge": {
      "bg_color": "#dbeafe",    // Hex color for badge background
      "text_color": "#1d4ed8",  // Hex color for badge text
      "initials": "WJ"          // Optional: custom initials (2-3 chars)
    }
  }
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `bg_color` | string | Yes* | Hex color code (e.g., `#dbeafe`) for background |
| `text_color` | string | Yes* | Hex color code (e.g., `#1d4ed8`) for text |
| `initials` | string | No | Override auto-generated initials (2-3 chars max) |

*Both `bg_color` and `text_color` must be provided together for custom colors to apply.

## How It Works

### Priority Order

Badge prefs are resolved in this order:

1. **Inline prefs** - From `action.assigned_to[].prefs.badge` (task-specific override)
2. **Contact prefs** - From `contact.prefs.badge` (user's default)
3. **Auto-assigned** - Staff get unique color from 8-color palette
4. **Default** - Non-staff get gray

### Frontend Loading

The React frontend loads staff badge prefs on app startup via `StaffBadgePrefsContext`:

```typescript
// Fetches all is_staff=true contacts
const response = await getRecords("contact", { is_staff: true });

// Caches prefs.badge for each contact
for (const contact of contacts) {
  if (contact?.prefs?.badge) {
    prefsMap.set(contact.id, contact.prefs.badge);
  }
}
```

## Setting Badge Prefs

### Via API

```bash
PATCH /wcapi/save/
{
  "model_name": "contact",
  "id": 123,
  "prefs": {
    "mode": "update",
    "value": {
      "badge": {
        "bg_color": "#dbeafe",
        "text_color": "#1d4ed8",
        "initials": "WJ"
      }
    }
  }
}
```

### Via Django Shell

```python
from apps.core.models import Contact

contact = Contact.objects.get(id=123)
prefs = contact.prefs or {}
prefs['badge'] = {
    'bg_color': '#dbeafe',
    'text_color': '#1d4ed8',
    'initials': 'WJ'
}
contact.prefs = prefs
contact.save()
```

## Suggested Color Palettes

### WCAG AA Compliant Combinations

| Style | bg_color | text_color | Preview |
|-------|----------|------------|---------|
| Blue | `#dbeafe` | `#1d4ed8` | Light blue bg, dark blue text |
| Violet | `#f3e8ff` | `#7c3aed` | Light purple bg, dark purple text |
| Cyan | `#cffafe` | `#0891b2` | Light cyan bg, dark cyan text |
| Fuchsia | `#fae8ff` | `#a21caf` | Light pink bg, dark magenta text |
| Lime | `#d9f99d` | `#4d7c0f` | Light green bg, dark green text |
| Yellow | `#fef9c3` | `#a16207` | Light yellow bg, dark amber text |
| Pink | `#fbcfe8` | `#be185d` | Light pink bg, dark pink text |
| Indigo | `#e0e7ff` | `#4338ca` | Light indigo bg, dark indigo text |

## Related Files

### Backend
- `common/models.py` - `PrefsMixin` with `prefs` JSONField
- `apps/core/models/contact.py` - Contact model inherits prefs

### Frontend
- `src/context/StaffBadgePrefsContext.tsx` - Context provider
- `src/apps/utils/gantt/GanttTaskTemplate.tsx` - Badge rendering
- `src/apps/utils/gantt/ganttDataMapper.ts` - `BadgePrefs` interface

## See Also

- [README-GANTT.md](../../../React2025/src/apps/utils/gantt/README-GANTT.md) - Gantt chart documentation
