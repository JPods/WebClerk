# Form Layout Research for Enterprise Software

## Overview

This document summarizes UX research on form layouts for enterprise applications where users interact with the software daily.

---

## Key Research Findings

### 1. Label Placement Studies (Luke Wroblewski / UXMatters)

- **Labels above fields** (Grid layout) have the fastest completion times in eye-tracking studies because users scan in a single vertical path
- **Labels to the left** (Horizontal layout) are preferred for **data-dense enterprise apps** where users become experts - it's more scannable once learned

### 2. Enterprise Software Specific Research

The Nielsen Norman Group recommends for **heavy daily use**:

- **Horizontal/inline labels** - Power users prefer density over ease of first-use
- **Consistent field widths** - Reduces cognitive load when scanning
- **Grouping related fields** - Card-based layouts support logical organization

### 3. Density vs. Usability Tradeoff

Research from Baymard Institute shows:

- **Novice users**: Prefer more whitespace (Grid, Two-Column)
- **Expert users** (daily enterprise): Prefer **compact/dense layouts** - they want to see more data without scrolling

---

## Layout Recommendations

| Layout | Best For |
|--------|----------|
| **Horizontal** | ✅ Best for daily enterprise use - scannable, professional, efficient |
| **Compact** | ✅ Great for power users who value density |
| **Grid** | Good for occasional users or onboarding |
| **Two-Column** | Good for complex forms with logical groupings |
| **Dense** | Niche - data entry specialists, 4D-style apps |

---

## Why Horizontal (Label-Left) is the Enterprise Standard

**Horizontal layout** is generally considered the gold standard for enterprise software because:

1. **Muscle memory** - Users develop spatial memory for field locations
2. **Scannable labels** - Labels align cleanly in a column, easy to scan vertically
3. **Industry standard** - Used by SAP, Salesforce, Oracle, and most ERP systems
4. **Reduced scrolling** - Horizontal layouts are typically more vertically compact than label-above layouts

---

## Our Implementation

Contact Detail pages support 5 layout options:

| Value | Label | Description |
|-------|-------|-------------|
| `grid` | Grid | 3-column grid layout with labels above inputs |
| `compact` | Compact | Dense 3-column with tighter spacing |
| `dense` | Dense | Ultra-compact with inline labels - maximum density |
| `horizontal` | Horizontal | 2-column with label to the left of entry area |
| `two-column` | Two Column | Card-based two-column layout |

Users can select their preferred layout via the layout selector, and their choice is persisted to localStorage.

---

## References

- Luke Wroblewski - "Web Form Design: Filling in the Blanks" (2008)
- Nielsen Norman Group - "Form Design Guidelines" 
- UXMatters - "Label Placement in Forms"
- Baymard Institute - "Form Usability" research

---

## Related Files

- `src/apps/core/models/contact/pages/ContactDetail.tsx` - Main contact detail with layout selector
- `src/apps/core/models/contact/pages/ContactDetailHorizontal.tsx` - Horizontal layout component
- `src/apps/core/models/contact/pages/ContactDetailTwoColumn.tsx` - Two-column layout component
