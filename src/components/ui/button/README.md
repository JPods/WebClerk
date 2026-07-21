# Button Style System

WebClerk 3 lets each deployment choose its toolbar button style. Four styles ship with the product. New styles can be added by dropping PNG files in a folder.

## Available Styles

| Style | Folder | Format | License | Look |
|-------|--------|--------|---------|------|
| **Glass** | `button_glass/` | PNG 3-state sprites | Review 4D IP | Warm chrome, WC2 heritage, metallic highlights |
| **OSX** | `OSX/` | PNG 3-state sprites | Review IP | Apple-native, photorealistic, aqua-era Mac |
| **Phosphor** | `phosphor/` | React SVG components | MIT | Modern duotone, scalable, hover animation |
| **Minimal** | `minimal/` | Text + emoji | Built-in | Compact, accessible, zero image weight |

## How It Works

1. User clicks the style picker in the top bar (next to App/Admin toggle)
2. Picker cycles through available styles: Glass → OSX → Phosphor → Minimal
3. All toolbar buttons update instantly — no page reload
4. Preference stored in `localStorage` as `wc3_button_style`

## For Deployments

Set the default style for your company in one line:

```javascript
localStorage.setItem('wc3_button_style', 'button_glass');
```

Or set it in your deployment startup script. No server configuration needed.

## Adding a New Button Style

### PNG-based style (like Glass or OSX)

1. Create a folder: `src/components/ui/button/{your_style_name}/`

2. Add PNG files — one per action. Each PNG is a **vertical sprite sheet** with 3 frames stacked top-to-bottom:
   - Frame 1 (top): Normal state
   - Frame 2 (middle): Hover state  
   - Frame 3 (bottom): Pressed state

3. Name the files to match the action mapping. Required files:

   | Action | Suggested Filename |
   |--------|--------------------|
   | Add Record | `AddRecord.png` or `NewRecord.png` |
   | Save | `OK.png` or `Save.png` or `Done.png` |
   | Discard | `Cancel.png` or `Undo.png` |
   | Delete Record | `DeleteRecord.png` |
   | Delete Selection | `DeleteSelection.png` |
   | Filter | `Query.png` or `Filter.png` |
   | Show All | `ShowAll.png` |
   | Show Subset | `ShowSubset.png` |
   | Omit Selection | `OmitSelection.png` |
   | Sort | `OrderBy.png` or `Sort.png` |
   | Print | `Print.png` |

4. Add a `README.md` in your folder describing the style, its origin, and license status.

5. Register the folder in `src/components/common/toolbarActions.ts`:
   - Add folder name to `AVAILABLE_PNG_STYLES`
   - Add filename mappings to each action in the `TB` object
   - Add folder name to `BUTTON_STYLES`

6. That's it. The picker automatically includes your new style.

### SVG/React-based style

Create a new renderer function in `src/components/common/ToolbarIcon.tsx` following the PhosphorRenderer pattern. Map it in the switch statement.

## File Structure

```
src/components/ui/button/
├── README.md              ← this file
├── button_glass/          ← WC2 glass chrome sprites
│   ├── README.md
│   ├── AddRecord.png
│   ├── OK.png
│   ├── Cancel.png
│   └── ... (11 action PNGs)
├── OSX/                   ← Apple-native photorealistic sprites
│   ├── README.md
│   ├── NewRecord.png
│   ├── Done.png
│   ├── Cancel.png
│   └── ... (19 action PNGs, including extras)
├── phosphor/              ← Phosphor duotone SVG (code-generated)
│   └── README.md
├── minimal/               ← Text + emoji (no files needed)
│   └── README.md
└── Button.tsx             ← Legacy button component
```

## Architecture

```
MacTopBar (picker)
  ↓ sets localStorage('wc3_button_style')
  ↓ dispatches 'wc3-button-style-changed' event
  
ToolbarIcon (renderer)
  ↓ reads style preference
  ↓ looks up action.png[style] for PNG folder name + filename
  ↓ renders: PngRenderer | PhosphorRenderer | MinimalRenderer

toolbarActions.ts (action definitions)
  TB.addRecord = { png: { button_glass: 'AddRecord', OSX: 'NewRecord' }, phosphor: FilePlus, minimal: 'Add' }
```

## Design Guidelines for New Button Sets

- **3-state sprites required** for PNG sets: normal (top), hover (middle), pressed (bottom)
- **Square aspect ratio** — buttons render at 56×56px, each sprite frame should be square
- **Consistent metaphor** — users should recognize the action from the icon alone
- **Personality matters** — flat/generic icons feel dead. Give them weight, shadow, or color
- **Test at 56px** — icons must be readable at toolbar size, not just at design size
