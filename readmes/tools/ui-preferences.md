# UI Preferences — metadata.wcui

**Established:** 2026-07-25
**Applies to:** All WC3 installations

---

## Principle

UI preferences belong on the user's Contact record, not in the browser. Your preferences follow you across devices, browsers, and sessions because they're on YOUR record — same principle as MyCarryOn portable identity.

---

## Storage

```json
// Contact.metadata.wcui
{
  "font_size": 15,
  "theme": "dark",
  "phone_display": "local",
  "default_country": "US",
  "phone_separator": ".",
  "date_format": "MM/DD/YYYY",
  "currency_locale": "en-US",
  "detail_view_pref": "app",
  "button_style": "glass",
  "dedup_font_size": 15
}
```

---

## How It Works

1. **On login:** Load `metadata.wcui` from the user's Contact record into localStorage
2. **On preference change:** Save to both localStorage (instant) and Contact record (persistent)
3. **On page load (not logged in):** Fall back to localStorage values
4. **On first login (no wcui yet):** Initialize from current localStorage values → save to Contact

---

## Preference Registry

| Key | Type | Default | What it controls |
|-----|------|---------|-----------------|
| `font_size` | number | 12 | databrowser base font size (S=12, M=14, L=16) |
| `dedup_font_size` | number | 13 | Dedup panel font scale |
| `theme` | string | `"dark"` | databrowser color theme |
| `detail_view_pref` | string | `"app"` | Right panel: `"app"` = modelDetail.tsx, `"admin"` = field grid |
| `button_style` | string | `"glass"` | Toolbar button style variant |
| `phone_display` | string | `"local"` | `"local"` hides country code for domestic, `"international"` always shows |
| `phone_separator` | string | `"."` | Phone display separator: `"."` or `"-"` or `" "` |
| `default_country` | string | `"US"` | Default country for phone normalization and zip formatting |
| `date_format` | string | `"MM/DD/YYYY"` | Date display format |
| `currency_locale` | string | `"en-US"` | Currency formatting locale |

---

## API

### Read preferences (client)
```typescript
import { getWcuiPref, setWcuiPref } from '@/utils/wcuiPrefs';

const fontSize = getWcuiPref('font_size', 12);
setWcuiPref('font_size', 16); // saves to localStorage + server
```

### Read preferences (server)
```python
contact = Contact.objects.get(id=user_id)
wcui = contact.metadata.get('wcui', {})
font_size = wcui.get('font_size', 12)
```

---

## Migration from localStorage

These localStorage keys migrate to `metadata.wcui`:

| localStorage key | wcui key |
|-----------------|----------|
| `db-theme` | `theme` |
| `db-fontsize` | `font_size` |
| `wc3_detail_view_pref` | `detail_view_pref` |
| `wc3_button_style` | `button_style` |

On first login after migration: read all localStorage keys, write to `metadata.wcui`, keep localStorage as cache.

---

## Training Video Notes

1. Show the A-/A+ buttons in Dedup panel — font size changes instantly
2. Close browser, reopen — font size is remembered (saved to Contact)
3. Log in on different browser — same preferences appear
4. Show theme toggle (dark/light) — same persistence
5. Key message: "Your preferences follow you because they're on your record, not in your browser"
