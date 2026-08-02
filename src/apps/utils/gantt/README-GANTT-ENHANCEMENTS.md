# Gantt Chart Enhancements over @svar-ui/react-gantt

**Base library:** `@svar-ui/react-gantt` by SVAR (Svelte/React Gantt)
**Enhanced by:** WebClerk3 / JPods team, July 2026
**License:** Enhancements are open source, same terms as WebClerk3 (MIT)

These enhancements layer on top of the SVAR Gantt without forking or patching the library. They use the library's existing extension points (taskTemplate, event handlers, CSS overrides) to add capabilities that make the chart usable for real project management — not just display.

---

## 1. Layered Task Bar Template (`GanttTaskTemplate.tsx`)

The default SVAR task bar shows a colored rectangle with text. Our template encodes four dimensions simultaneously without adding clutter:

```
┌─ top stripe: priority color ──────────────────────────────────┐
│ █ Task name                                        J.Smith    │
│ █ status                                                      │
└─ bottom bar: ████████░░░░░ % complete ────────────────────────┘
  │
  left stripe: status color
```

**Four visual channels:**
- **Top stripe** — priority (red=critical, orange=high, light blue=medium, light gray=low)
- **Left stripe** — status (blue=active, green=done, red=blocked, gray=hold)
- **Bottom bar** — percent complete (filled portion, green at 100%)
- **Person badge** — right-aligned initials in assignee's color

**Additional badges:** Critical path (CP), priority letter (!, H, M, L)

### Staff badge colors

Assignee badges use a consistent color assignment:
- Staff badge preferences from `StaffBadgePrefsContext` (if configured)
- Inline `prefs.badge` on the user record
- Fallback: rotating palette of 8 distinguishable colors (blue, violet, cyan, fuchsia, lime, yellow, pink, indigo)

---

## 2. Color Mode Selector

Four ways to color the task bars, switchable via toolbar buttons:

| Mode | What determines bar color |
|------|--------------------------|
| **Priority** | critical=red, high=orange, medium=light blue, low=light gray |
| **Status** | Maps column/status to color (active=blue, done=green, blocked=red) |
| **Who** | Each assignee gets a consistent color from the palette |
| **Project** | Each project gets a color (from `project.prefs.action.color` or palette) |

Implementation: `colorMode` state drives a `useMemo` that recomputes bar colors. The task template's stripes remain independent of bar color, so you always see priority + status regardless of which color mode is active.

---

## 3. A+/A- Font Scaling

Toolbar buttons to increase/decrease font size across the entire Gantt:

- No artificial limits — users have reasons for any size
- Scales container `fontSize`, task bar text (`inherit`), badges (`em` units), and row height (`cellHeight`)
- Persists to `contact.metadata.wcui.gantt_font_scale` via server-synced preferences
- Gantt re-renders with new key on scale change (forces SVAR to recalculate layout)

```tsx
// Container passes font size; template inherits it
<div style={{ fontSize: `${12 + ganttFontScale}px` }}>
  <Gantt cellHeight={38 + ganttFontScale} ... />
</div>

// Template uses relative units
<span style={{ fontSize: "inherit" }}>{task.text}</span>
<span style={{ fontSize: "0.8em" }}>{percentComplete}%</span>
```

---

## 4. Text Overflow Toggle

Checkbox: **"Show full text"** — lets task text run past the right edge of the bar instead of truncating with ellipsis.

Uses CSS custom property `--gantt-text-overflow` set on the container, read by the template via `var(--gantt-text-overflow, hidden)`. No prop drilling needed — works through CSS inheritance across the SVAR component boundary.

---

## 5. Meeting-Friendly Click Behavior

**Problem:** In meetings, people click on things to point at them. Single-click opening a detail panel is disruptive when someone is just emphasizing a task while talking.

**Solution:**
- **Single click** = 5-second blue outline emphasis, then fades. Visual "I'm pointing at this" without navigation.
- **Double click** = opens the task detail editor (ActionDetail)

```tsx
const handleClick = useCallback((e: React.MouseEvent) => {
  e.stopPropagation();
  setEmphasized(true);
  setTimeout(() => setEmphasized(false), 5000);
}, []);
```

---

## 6. Hover Tooltip

Hovering over a task bar shows a native browser tooltip with:
- Task name
- Status, Priority
- Progress percentage
- Assigned person
- Start and end dates

Uses the `title` attribute — no custom tooltip component, works everywhere, respects OS accessibility settings.

---

## 7. Frozen Header Rows

CSS makes the first two rows sticky when scrolling the task list:

```css
.wx-content .wx-row:nth-child(1),
.wx-content .wx-row:nth-child(2) {
  position: sticky !important;
  top: 0 !important;
  z-index: 5 !important;
  background: var(--wx-background, #fff) !important;
  box-shadow: 0 1px 0 rgba(0,0,0,0.08);
}
```

The timeline header (`.wx-scale`) is also made sticky via Tailwind arbitrary selectors on the container.

---

## 8. Project Hierarchy with Cascade Selection

Project selector shows parent/child relationships:
- `▸` prefix for parent projects
- `└` prefix and left indent for children
- **Clicking a parent selects/deselects all descendants** (children, grandchildren)

```tsx
const getDescendantIds = (parentId: string): string[] => {
  const descendants: string[] = [];
  const queue = [parentId];
  while (queue.length > 0) {
    const current = queue.shift()!;
    for (const p of projects) {
      if (String(p.id_parent) === current) {
        descendants.push(p.id);
        queue.push(p.id);
      }
    }
  }
  return descendants;
};
```

---

## 9. Multi-Scale Presets

Toolbar buttons for time scale: Day, Week, Month, Quarter, Year. Each preset defines the scale bands (e.g., Week shows months + weeks, Quarter shows years + quarters).

---

## 10. Print / Export

Custom print layout and SVG export that render all tasks in a clean format independent of the SVAR component's scroll state.

---

## Architecture Notes

All enhancements use SVAR's public API — no monkey-patching, no fork:

| Extension point | What we use it for |
|----------------|-------------------|
| `taskTemplate` | Custom task bar rendering (layered template) |
| `onItemDoubleClick` | Open detail editor |
| `cellHeight` | Dynamic row height for font scaling |
| `columns` | Custom column configuration with exact field-path labels |
| CSS overrides | Frozen rows, sticky headers, emphasis borders |
| CSS custom properties | Font scale and text overflow passed through SVAR boundary |

The SVAR library handles: virtual scrolling, drag-to-resize, dependency links, timeline rendering, Gantt math. We handle: visual encoding, interaction design, accessibility, data mapping, persistence.

---

## Files

| File | What it does |
|------|-------------|
| `GanttTaskTemplate.tsx` | Layered task bar with 4-channel visual encoding |
| `UnifiedGantt.tsx` | Main component — toolbar, color modes, font scale, click handlers |
| `GanttProjectSelector.tsx` | Project list with hierarchy and cascade selection |
| `useGanttData.ts` | Data fetching, project parsing, action mapping |
| `ganttDataMapper.ts` | Transform WebClerk actions → SVAR Gantt tasks |

---

*These enhancements are part of WebClerk3, an open-source commerce platform. The Gantt improvements are independent of the commerce layer and can be adapted for any @svar-ui/react-gantt installation.*
