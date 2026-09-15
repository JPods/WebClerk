# Phone / Clipboard Bridge — Onboarding Note

## What happens when you click a green label

WebClerk uses **green labels** for actionable fields: phone, email, address, website.

| Click on | What happens |
|----------|-------------|
| **phone** | Number copied to clipboard |
| **email** | Copied + opens email client |
| **address** | Copied + opens maps |
| **website** | Opens URL in new tab |

## How the number gets to your phone

### Apple users (Mac + iPhone)
Nothing to install. **Universal Clipboard** syncs automatically between your
Mac and iPhone when they share the same iCloud account, are on the same WiFi,
and have Bluetooth enabled.

1. Click the phone label in WebClerk — number is copied
2. Pick up your iPhone — paste into dialer, Messages, or any app
3. Works both directions (copy on phone, paste on Mac)

**Requirements:** Same Apple ID, WiFi on, Bluetooth on, Handoff enabled.

### Android / Windows / Linux users
Install **KDE Connect** — open source, no cloud account required.

- **Android:** [Google Play](https://play.google.com/store/apps/details?id=org.kde.kdeconnect_tp)
- **Windows/Mac/Linux:** [KDE Connect Downloads](https://kdeconnect.kde.org/download.html)

KDE Connect syncs clipboard over WiFi. Copy in WebClerk, paste on your phone.

### Self-hosted alternative
**ClipCascade** — self-hosted clipboard server with Android app.
No cloud dependency. Good for privacy-conscious organizations.

## Alice's role

When a user first clicks a phone label, Alice should check their profile:
- If `prefs.device.phone_bridge` is not set, show the onboarding note
- Once acknowledged, set `prefs.device.phone_bridge = true` so it doesn't repeat
- If the user is on a non-Apple platform (detected via `navigator.userAgent`),
  recommend KDE Connect specifically

## Training video reference

Bill's training video covers this workflow. Reference timestamp: TBD.
