# 68 — WebClerk.com Video Pages

**Created:** 2026-08-25
**Status:** Live — 5 video pages deployed

---

## What This Is

Self-hosted video pages on webclerk.com. Each page embeds a Vimeo video in the site's dark theme (matching wc-works, ecosystem, etc.). Linked from the Videos dropdown menu on the landing page.

---

## Live Pages

| Path | Title | Vimeo ID | Menu label |
|------|-------|----------|------------|
| /heresyouranswer/ | Here's Your Answer | 426810948 | Here's Your Answer |
| /qa/ | Q&A | 436423799 | Q&A Behaviors |
| /fileorganization/ | File Organization | 440429413 | File Organization |
| /webclerkpreferences/ | WebClerk Preferences | 440433328 | WebClerk Preferences |
| /spareparts/ | Spare Parts | 246386254 | Spare Parts |

---

## File Locations

| What | Where |
|------|-------|
| Source (local) | `~/Allie/sites/<pagename>/index.html` |
| Deployed | `andi:/var/www/webclerk-static/<pagename>/` |
| Nginx config | `/etc/nginx/sites-enabled/webclerk3` |
| Landing page | `andi:/opt/andi/apps/webclerk3/landing/index.html` |

---

## How to Add a New Video Page

### 1. Create the page locally

```bash
mkdir -p ~/Allie/sites/<pagename>
```

Write `index.html` using this template (change title, h1, and Vimeo ID):

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PAGE TITLE</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  :root {
    --bg: #0f172a; --surface: #1e293b; --surface2: #334155;
    --text: #f1f5f9; --muted: #94a3b8;
    --accent: #3b82f6;
    --sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }
  body { font-family: var(--sans); background: var(--bg); color: var(--text); min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px 20px; }
  h1 { font-size: 2.4rem; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 32px; text-align: center; }
  h1 span { color: var(--accent); }
  .video-wrapper { width: 100%; max-width: 960px; background: var(--surface); border-radius: 12px; border: 1px solid var(--surface2); overflow: hidden; }
  .video-container { position: relative; padding-bottom: 56.25%; height: 0; }
  .video-container iframe { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0; }
  .back { margin-top: 32px; color: var(--muted); font-size: 0.9rem; text-decoration: none; }
  .back:hover { color: var(--accent); }
</style>
</head>
<body>
  <h1>FIRST <span>WORD</span></h1>
  <div class="video-wrapper">
    <div class="video-container">
      <iframe src="https://player.vimeo.com/video/VIMEO_ID" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen></iframe>
    </div>
  </div>
  <a href="/" class="back">webclerk.com</a>
</body>
</html>
```

### 2. Deploy to Andi

```bash
# Rsync to staging (no sudo needed)
rsync -avz ~/Allie/sites/<pagename>/ andi:/tmp/<pagename>-staging/

# Copy to webclerk-static with correct ownership
ssh andi "sudo mkdir -p /var/www/webclerk-static/<pagename> && \
  sudo cp /tmp/<pagename>-staging/* /var/www/webclerk-static/<pagename>/ && \
  sudo chown -R www-data:www-data /var/www/webclerk-static/<pagename>/"
```

### 3. Add nginx location block

Add to `/etc/nginx/sites-enabled/webclerk3` (insert before the React app block):

```nginx
    # Page Name — static site
    location = /<pagename> {
        return 301 /<pagename>/;
    }
    location /<pagename>/ {
        alias /var/www/webclerk-static/<pagename>/;
        try_files $uri $uri/ /<pagename>/index.html;
    }
```

Then test and reload:

```bash
ssh andi "sudo nginx -t && sudo systemctl reload nginx"
```

### 4. Add to landing page Videos menu

Edit `andi:/opt/andi/apps/webclerk3/landing/index.html` — add a `<li>` in the Videos dropdown:

```html
<li><a class="dropdown-item" href="/<pagename>/">Menu Label</a></li>
```

### 5. Verify

```bash
curl -sL -o /dev/null -w "%{http_code}" https://www.webclerk.com/<pagename>/
```

---

## All Static Sites on Andi

These all follow the same pattern — source in `~/Allie/sites/`, served from `/var/www/webclerk-static/`:

| Path | Purpose |
|------|---------|
| /ecosystem/ | Ecosystem overview |
| /sort/ | Statement Sorter |
| /liferequiresenergy/ | Life Requires Energy |
| /wc-works/ | How WebClerk Works |
| /project_planner/ | Project Planner |
| /heresyouranswer/ | Video: Here's Your Answer |
| /qa/ | Video: Q&A |
| /fileorganization/ | Video: File Organization |
| /webclerkpreferences/ | Video: WebClerk Preferences |
| /spareparts/ | Video: Spare Parts |

---

## Notes

- All pages use the same dark theme (--bg: #0f172a, --accent: #3b82f6)
- Videos embed via Vimeo player iframe (responsive 16:9)
- No `.git` directories are deployed — exclude with `--exclude='.git'` on rsync
- The landing page Videos menu also links to webclerk.net/videos.html for older videos
- Nginx `server_name` is `webclerk.com www.webclerk.com` — both work
