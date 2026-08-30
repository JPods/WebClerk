# Hostinger — Configuration Notes for JPods.com

## Subdomain Redirects

When `library.jpods.com` shares the same Hostinger dashboard as `jpods.com`,
`.htaccess` exceptions on the root domain are **not sufficient** to prevent
the subdomain from intercepting requests. Use Hostinger's built-in Redirect
tool instead.

### How to Add a Redirect in Hostinger

1. Log into Hostinger dashboard
2. In the **left sidebar**, find the website name (e.g. `jpods.com`)
3. Click **Domain → Redirects**
4. Add source and destination URLs:

| Source (From) | Destination (To) |
|---|---|
| `https://library.jpods.com/70.html` | `https://jpods.com/70.html` |
| `https://library.jpods.com/citytool.html` | `https://jpods.com/citytool.html` |

5. Use **302 (temporary)** while testing
6. Switch to **301 (permanent)** once confirmed working

### When to Use This

Any new file served from the root `jpods.com` that was previously routed
through `library.jpods.com` will need a redirect entry here. This includes:
- New standalone HTML pages (e.g. `70.html`, `citytool.html`)
- Any path that existed on the old WordPress library site

---

## Root Domain .htaccess — Exceptions List

Files served directly from `jpods.com` root must be whitelisted in
`/public_html/.htaccess` **before** the catch-all redirect rule.

```apache
RewriteEngine On
# Allow direct access to landing page assets
RewriteRule ^index\.html$    - [L]
RewriteRule ^70\.html$       - [L]
RewriteRule ^citytool\.html$ - [L]
RewriteRule ^images/         - [L]
RewriteRule ^networks/       - [L]
RewriteRule ^favicon         - [L]
RewriteRule ^robots\.txt$    - [L]
RewriteRule ^sitemap         - [L]
# Redirect everything else to library subdomain
RewriteCond %{HTTP_HOST} ^(www\.)?jpods\.com$ [NC]
RewriteCond %{REQUEST_URI} !^/?$ [NC]
RewriteRule ^(.+)$ https://library.jpods.com/$1 [R=302,L]
# Redirect www → non-www
RewriteCond %{HTTP_HOST} ^www\.jpods\.com$ [NC]
RewriteRule ^(.*)$ https://jpods.com/$1 [R=301,L]
```

> **Note:** Use `R=302` on the library catch-all while actively making
> changes. Switch back to `R=301` once routing is stable to enable
> browser caching.

---

## Chrome Redirect Cache — Hard Reset

If Chrome keeps redirecting to a stale destination after `.htaccess` changes:

1. Open DevTools (`F12` or `Cmd+Option+I`)
2. Right-click the **refresh button**
3. Select **Empty Cache and Hard Reload**

Or clear HSTS/DNS cache:
- `chrome://net-internals/#hsts` → Delete domain security policies
- `chrome://net-internals/#dns` → Clear host cache

> Safari, Firefox, and incognito are unaffected by Chrome's cached 301s.
> If only Chrome shows the wrong redirect, this is always the fix.