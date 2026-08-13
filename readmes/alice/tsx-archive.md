# Alice — TSX Archive and Study Protocol

## The Principle

When a user replaces a .tsx file with a new version, Alice archives the
previous version before it's overwritten. She studies the differences to
learn how data entry, layout, and user interaction evolved.

The old version is not dead code — it's a learning artifact. The diff
between old and new reveals what users found valuable, what they rejected,
and why the replacement was needed.

## What Alice Does

### On replacement:
1. Copy the previous file to `archive/tsx/<filename>.<date>.tsx`
2. Generate a diff summary: what was added, removed, changed
3. Log the observation: which fields moved, which were dropped,
   how layout density changed, what user feedback drove the change

### What she studies:
- **Field density**: did the replacement pack more fields per row?
  Users want compact over spacious.
- **Removed features**: what was in the old version but dropped?
  That's what users didn't value.
- **Kept features**: what survived unchanged? That's what works.
- **Layout patterns**: inline labels vs stacked, selects vs buttons,
  single-row vs multi-row for related fields (dates, priority/difficulty)

### What she learns:
- User preference patterns for data entry density
- Which fields are always visible vs collapsible
- How the same data is presented differently in full-page vs panel views
- The cost of vertical space — every pixel scrolled is friction

## Example: ActionDetail → ActionDetailCompact

Old: Full-page, section headers, Arabic/Bengali fields, HorizontalField
components, icons on every label, column selector, separate date section.

New: 320px panel, all fields inline, status/priority/difficulty/% on one
row, dates on one row with computed duration, no section headers, no
icons, no translation fields, edit/save toggle.

Lesson: For quick-reference views (Gantt side panel), users want maximum
information density with minimum chrome. The full-page version is for
focused editing. The compact version is for context without leaving
the current view.
