# Enhanced SVAR Gantt — Drop-in Upgrades

Production-tested enhancements for `@svar-ui/react-gantt` that add visual encoding, meeting-friendly interaction, font scaling, and project hierarchy — without forking the library.

**Before:** Plain colored bars with text.
**After:** Four-channel visual encoding, click emphasis, font scaling, text overflow, cascade project selection.

## Quick Start

```bash
npm install @svar-ui/react-gantt
```

Copy these files into your project:
- `EnhancedTaskTemplate.tsx` — Layered task bar
- `EnhancedGantt.tsx` — Wrapper with toolbar controls
- `ProjectSelector.tsx` — Hierarchical project list with cascade selection

```tsx
import { EnhancedGantt } from './EnhancedGantt';

function App() {
  return (
    <EnhancedGantt
      tasks={tasks}
      links={links}
      projects={projects}
    />
  );
}
```

## What You Get

### 1. Layered Task Bars — Four Dimensions, Zero Clutter

```
┌─ top stripe: priority ────────────────────────────────┐
│ [!] Task name                                   [JS]  │
└─ bottom bar: ████████░░░ % complete ──────────────────┘
│
left stripe: status
```

- **Top stripe** — priority (red/orange/blue/gray)
- **Left stripe** — status (blue=active, green=done, red=blocked)
- **Bottom bar** — percent complete
- **Badge** — assignee initials in their color

### 2. Meeting-Friendly Clicks

People click things to point at them while talking. Opening a detail panel every time is disruptive.

- **Single click** = 5-second blue outline emphasis, then fades
- **Double click** = opens detail editor

### 3. A+/A- Font Scaling

No artificial limits. Uses CSS custom properties to cross the SVAR component boundary:

```tsx
// Container sets the variable
<div style={{ fontSize: `${12 + scale}px`, '--gantt-text-overflow': overflow }}>
  <Gantt cellHeight={38 + scale} taskTemplate={EnhancedTaskTemplate} />
</div>

// Template reads it via inheritance
<span style={{ fontSize: "inherit" }}>{task.text}</span>
```

### 4. Text Overflow Toggle

Checkbox lets text run past bar edges. Useful for long task names in narrow time scales.

### 5. Frozen Header Rows

First two rows stay pinned while scrolling:

```css
.wx-content .wx-row:nth-child(1),
.wx-content .wx-row:nth-child(2) {
  position: sticky !important;
  top: 0; z-index: 5;
  background: var(--wx-background, #fff) !important;
}
```

### 6. Project Hierarchy

Click a parent project to select all children. Visual indicators show the tree:

```
▸ MOA Capital Campaign          ← click selects all below
  └ W31: Network Design
  └ W32: Specifications
  └ W33: Quality & Safety
```

## Key Technique: CSS Custom Properties Cross Component Boundaries

SVAR renders its own DOM — you can't pass props to `taskTemplate`. But CSS variables set on the container are inherited by everything inside, including the template.

```tsx
// Set on container (your code)
style={{ '--gantt-text-overflow': 'visible' }}

// Read in template (rendered inside SVAR's DOM)
style={{ overflow: 'var(--gantt-text-overflow, hidden)' }}
```

This pattern works for any React component library that renders its own DOM subtree.

## No Fork Required

Every enhancement uses SVAR's public API:

| Extension point | Enhancement |
|----------------|-------------|
| `taskTemplate` | Layered visual encoding |
| `onItemDoubleClick` | Meeting-friendly click behavior |
| `cellHeight` | Dynamic row height for font scaling |
| CSS overrides | Frozen rows, sticky headers |
| CSS custom properties | Font scale + text overflow through SVAR boundary |

## License

MIT — use freely. Originally built for [WebClerk3](https://webclerk.com), an open-source commerce platform.

Built by Bill James + Claude (JPods / WebClerk team), July 2026.
