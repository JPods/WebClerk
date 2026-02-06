# Static Images Directory

This directory stores static image assets for the webClerk3 application.

## Structure

Images are organized by **model type** and **ida** (external/alternate ID):

```
static/images/
├── item/              # Product/item images
│   ├── {ida}/         # Folder named by item's ida (e.g., "243")
│   │   ├── primary.jpg
│   │   ├── thumb.jpg
│   │   ├── 01.jpg     # Gallery images
│   │   ├── 02.jpg
│   │   └── ...
│   └── ...
├── contact/           # Contact avatars/photos
│   ├── {ida}/
│   │   ├── avatar.jpg
│   │   └── ...
│   └── ...
├── customer/          # Customer/org logos
│   ├── {ida}/
│   │   ├── logo.jpg
│   │   └── ...
│   └── ...
├── vendor/            # Vendor logos
│   └── {ida}/...
├── document/          # Document thumbnails/previews
│   └── {ida}/...
└── placeholder.png    # Default fallback image
```

## Path Convention

**Pattern:** `{model}/{ida}/{filename}`

| Model    | ida   | Example Path                    |
|----------|-------|---------------------------------|
| item     | 243   | `item/243/primary.jpg`          |
| item     | 243   | `item/243/01.jpg` (gallery)     |
| contact  | 1052  | `contact/1052/avatar.jpg`       |
| customer | 87    | `customer/87/logo.png`          |

## metadata.images Storage

Images are referenced in `metadata.images` with relative paths from `/static/images/`:

```json
{
  "metadata": {
    "images": {
      "primary": "item/243/primary.jpg",
      "gallery": ["item/243/01.jpg", "item/243/02.jpg"],
      "thumbnail": "item/243/thumb.jpg"
    }
  }
}
```

The frontend prepends the base URL (`/static/images/` or CDN) automatically.

## Why ida instead of id?

- **ida** is the external/alternate identifier, often matching legacy systems
- More human-readable in file paths (e.g., SKU-based ida for items)
- Stable across database migrations/imports
- Easier to manually organize files

## Django Static Files Configuration

In `settings.py`:

```python
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# For production with whitenoise or external CDN:
# STATIC_URL = 'https://cdn.example.com/static/'
```

## Serving in Development

Django's `runserver` automatically serves static files in DEBUG mode.

## Serving in Production

Use a web server (nginx, Apache) or CDN:

```nginx
location /static/images/ {
    alias /path/to/webClerk3/static/images/;
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

## Image Guidelines

| Type      | Dimensions    | Format | Notes                        |
|-----------|---------------|--------|------------------------------|
| primary   | 800×800 min   | JPEG   | Hero/detail view             |
| thumbnail | 200×200       | JPEG   | List/grid display            |
| gallery   | 800×800 min   | JPEG   | Additional angles/views      |
| avatar    | 200×200       | JPEG/PNG | Contact photos             |
| logo      | 400×400 max   | PNG    | Transparent background OK    |

## Naming Conventions

- **Lowercase** filenames only
- **Hyphens** for spaces (not underscores)
- **No special characters** except hyphen and dot
- **Descriptive names**: `front-view.jpg`, `packaging.jpg`, `detail-closeup.jpg`

## Creating Folders

```bash
# For a new item with ida 500
mkdir -p static/images/item/500

# For a new contact with ida 1200
mkdir -p static/images/contact/1200
```
