# Training Video Scripts — DataBrowser Detail Pane

Scripts for short training videos showing the new field grouping and detail layout features. Each video is 60-90 seconds.

---

## Video 1: Field Groups — Finding What You Need Fast

**Title:** "Contact Detail in 3 Seconds"
**Duration:** ~60s

**[Screen: DataBrowser at /db/contact, Bill Smith selected]**

> Before field groups, a contact record was 50 fields in a flat wall. You had to scroll past password, last_login, and address_id just to find the phone number.

**[Point to IDENTITY (11) header]**

> Now fields are organized into labeled sections. Identity at the top — name, company, the fields that tell you who this is.

**[Point to COMMUNICATION (3)]**

> Communication is right below — email, address, phone. The fields you look up most are two clicks from the top, not buried in a 50-field grid.

**[Click STATUS chevron to collapse it]**

> Every section collapses. Click the header to toggle. Status, Dates, System — collapse the ones you don't use. Your choices stick between sessions.

**[Scroll to show DATES and SYSTEM collapsed]**

> System and Dates start collapsed by default. The internal IDs and timestamps are there when you need them — hidden when you don't.

**[End on the full view with groups visible]**

> Groups are data-driven. Each model gets its own grouping from a Setting record. No code changes needed to rearrange them.

---

## Video 2: Detail Order — Rearranging Your Detail View

**Title:** "Customize Your Detail Layout"
**Duration:** ~75s

**[Screen: DataBrowser at /db/order, record selected, detail toolbar visible]**

> The Detail Order button lets you control which fields appear and in what order — same as List Order does for columns.

**[Click "Detail Order" button in the detail toolbar]**

> Click Detail Order. You see every field for this model. Checked fields are visible in the detail pane. Unchecked fields are hidden.

**[Drag a field to reorder it]**

> Drag to reorder. Fields within each group follow the order you set here. Put the fields you use most at the top.

**[Point to the Layout dropdown in the dialog]**

> You can save named layouts. If you're doing accounting work, save a layout that shows financial fields first. Doing shipping? Save one with address and ship_via at the top.

**[Select "flat" from the Layout dropdown]**

> The "flat" layout removes all grouping — back to the original ungrouped view. Some users prefer the wall. That's fine.

**[Click Apply]**

> Click Apply. The detail pane updates immediately. Your layout is saved to your account — it follows you between browsers.

---

## Video 3: Shift-for-Help — Learning the Interface

**Title:** "Hold Shift to Learn"
**Duration:** ~45s

**[Screen: DataBrowser, detail pane with field groups]**

> One keyboard shortcut to learn the whole interface: hold Shift.

**[Hold Shift, hover over IDENTITY group header — tooltip appears]**

> Shift plus hover shows a tooltip on any element that has help text. Group headers tell you how many fields they contain and what clicking does.

**[Hold Shift, hover over a BehaviorField label]**

> Field labels show their type — readonly, lookup, email action. The colored labels already hint at this, but Shift-hover gives you the full story.

**[Hold Shift, click a field label]**

> Shift-click goes deeper — opens the help panel or jumps to documentation. One key, every element, every page in the system.

---

## Video 4: JSON Envelopes — Inspecting Complex Data

**Title:** "JSON Without Fear"
**Duration:** ~75s

**[Screen: DataBrowser, scroll to JSON ENVELOPES panel at bottom of detail]**

> Every record has JSON fields — metadata, prefs, config, refs. These used to be invisible walls of text. Now they're tree editors.

**[Click to expand the METADATA tree]**

> Click any key to expand it. You can see the structure, the values, the nesting. No need to copy JSON into an external tool.

**[Point to Expand/Collapse/+ controls]**

> Expand All opens every node. Collapse All folds it back. The plus button adds a new key.

**[Click a JSON field label in the tree]**

> Click the label to open the full floating editor — syntax highlighting, validation, format and minify buttons.

**[Scroll up to show the field groups above]**

> JSON Envelopes are separate from the field groups. Field groups organize the scalar fields — text, numbers, dropdowns. JSON Envelopes handle the structured data. Both are collapsible, both remember your state.

---

## Video 5: Layouts for Different Roles

**Title:** "One Model, Many Views"
**Duration:** ~60s

**[Screen: DataBrowser header, Layout dropdown visible]**

> Different people need different views of the same data. The Layout dropdown saves named configurations.

**[Click Layout dropdown, show saved views]**

> Each layout remembers which fields are visible, their order, and their column widths — for both the list and the detail pane.

**[Select "initial" layout]**

> "Initial" is the system default — a curated starting point for each model.

**[Select "flat" layout — groups disappear]**

> "Flat" removes field grouping entirely. Same fields, no sections. Choose whichever style works for you.

**[Click Layout dropdown, type a name, click Save]**

> Save your own layouts. Give them names that describe the task — "Accounting Review," "Quick Lookup," "Shipping."

**[Shift-click a saved layout — delete confirmation]**

> Shift-click a saved layout to delete it. No extra buttons, no context menus. Shift-click is the power-user pattern across all of WebClerk.

---

## Production Notes

- Record at 1920x1080, dark theme
- Use Bill Smith (DEV-10634) as the demo contact — has data in all groups
- Use DEV-34 order for transaction examples
- Font size M (14px) for readability on video
- Pause 1 second on each new visual element before narrating
- No background music — these are reference videos, not marketing
- Host on webclerk.com/learn alongside the JSON Tree applet
