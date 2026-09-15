# Production Deployment — Dev Server vs Production Server

**Created:** 2026-08-09
**Audience:** WebClerk open-source deployers

---

## The Warning

When you run WebClerk locally with `runserver.sh` or `python manage.py runserver`, Django prints:

```
WARNING: This is a development server. Do not use it in a production setting.
Use a production WSGI or ASGI server instead.
```

This is correct behavior. **Keep runserver for local development. Use Gunicorn + Nginx for production.**

---

## Why Developers Keep `runserver` Locally

Django's development server provides three features that production servers do not:

| Feature | What it does | Why it matters |
|---------|-------------|----------------|
| **Auto-reload** | Watches every `.py` file; restarts the server on save | Change code → see the result instantly. No manual restart. |
| **Verbose error pages** | Full stack trace, local variables, SQL queries in browser | Debug in the browser instead of reading log files. |
| **Static file serving** | Serves `/static/` and `/media/` without Nginx | One command, everything works. No collectstatic step. |

Gunicorn does not auto-reload by default. You save a file, nothing happens until you restart the process. For development, that friction costs real time on every change.

**Rule: `runserver` on your Mac. Gunicorn on your server.**

---

## Production Architecture

```
Internet → Cloudflare (SSL termination)
    → Your Server (Nginx on :80)
        ├── /              → Landing page (static HTML)
        ├── /app/          → React SPA (databrowser, tools)
        ├── /sort          → Statement Sorter (static HTML)
        ├── /wcapi/        → Django API (Gunicorn on :8000)
        ├── /admin/        → Django admin (Gunicorn on :8000)
        ├── /static/       → Django collected static files
        └── /media/        → Django media uploads
```

Three services run on the production server, managed by systemd:

| Service | What | Restart command |
|---------|------|-----------------|
| `webclerk3.service` | Gunicorn — Django WSGI (3–4 workers, port 8000) | `sudo systemctl restart webclerk3` |
| `webclerk3-celery.service` | Celery worker + beat (background tasks) | `sudo systemctl restart webclerk3-celery` |
| `nginx` | Reverse proxy, static files, SSL headers | `sudo systemctl reload nginx` |

All three are `enabled` — they survive reboots.

---

## Setting Up Your Production Server

### 1. Install dependencies

```bash
sudo apt update && sudo apt install -y nginx postgresql python3-venv
```

### 2. Create the app directory

```bash
sudo mkdir -p /opt/yourserver/apps/webclerk3
sudo mkdir -p /opt/yourserver/logs
```

### 3. Rsync your code from your development Mac

```bash
# Sync WC3 code — NEVER use --delete (it destroys server-only files)
rsync -avz \
  --exclude='.git' --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='node_modules' --exclude='.env' --exclude='logs/' --exclude='media/' \
  ~/Documents/CommerceExpert/webClerk3/ \
  youruser@yourserver:/opt/yourserver/apps/webclerk3/

# Sync React frontend
rsync -avz --exclude='.git' --exclude='node_modules' \
  ~/Documents/CommerceExpert/React2025/dist/ \
  youruser@yourserver:/opt/yourserver/apps/react2025/dist/
```

**SSH setup:** If you haven't configured SSH key authentication:
```bash
# On your Mac — generate a key (skip if you already have one)
ssh-keygen -t ed25519

# Copy your public key to the server
ssh-copy-id youruser@yourserver

# Test — should connect without a password prompt
ssh youruser@yourserver "hostname"
```

### 4. Set up the virtualenv and .env on the server

```bash
ssh youruser@yourserver

cd /opt/yourserver/apps/webclerk3
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn

# Create .env
cat > .env << 'EOF'
DB_MODE=local
LOCAL_DATABASE_NAME=commerce_expert
LOCAL_DATABASE_USER=webclerk
LOCAL_DATABASE_PASS=your_password_here
LOCAL_DATABASE_HOST=localhost
LOCAL_DATABASE_PORT=5432
SECRET_KEY=your_secret_key_here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
EOF
```

### 5. Set up PostgreSQL

```bash
sudo -u postgres createuser webclerk
sudo -u postgres createdb commerce_expert -O webclerk
sudo -u postgres psql -c "ALTER USER webclerk WITH PASSWORD 'your_password_here';"
```

### 6. Collect static files and migrate

```bash
cd /opt/yourserver/apps/webclerk3
source venv/bin/activate
python manage.py collectstatic --noinput
python manage.py migrate
```

### 7. Create systemd service — Gunicorn

Create `/etc/systemd/system/webclerk3.service`:
```ini
[Unit]
Description=WebClerk3 Gunicorn Server
After=network.target postgresql.service

[Service]
User=webclerk
Group=webclerk
WorkingDirectory=/opt/yourserver/apps/webclerk3
ExecStart=/opt/yourserver/apps/webclerk3/venv/bin/gunicorn \
    webclerk3_api.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile /opt/yourserver/logs/wc3-access.log \
    --error-logfile /opt/yourserver/logs/wc3-error.log
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 8. Create systemd service — Celery

Create `/etc/systemd/system/webclerk3-celery.service`:
```ini
[Unit]
Description=WebClerk3 Celery Worker + Beat
After=network.target redis.service

[Service]
User=webclerk
Group=webclerk
WorkingDirectory=/opt/yourserver/apps/webclerk3
ExecStart=/opt/yourserver/apps/webclerk3/venv/bin/celery \
    -A webclerk3_api worker -l info -B \
    --logfile=/opt/yourserver/logs/celery.log
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 9. Configure Nginx

Create `/etc/nginx/sites-available/webclerk3`:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # If behind Cloudflare — critical to prevent redirect loops
    # proxy_set_header X-Forwarded-Proto https;  # NOT $scheme

    location /static/ {
        alias /opt/yourserver/apps/webclerk3/staticfiles/;
    }

    location /media/ {
        alias /opt/yourserver/apps/webclerk3/media/;
    }

    location /app/ {
        alias /opt/yourserver/apps/react2025/dist/;
        try_files $uri $uri/ /app/index.html;
    }

    location /wcapi/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    location /admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    location / {
        root /opt/yourserver/apps/webclerk3/landing;
        index index.html;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/webclerk3 /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 10. Enable and start everything

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now webclerk3
sudo systemctl enable --now webclerk3-celery
sudo systemctl enable --now nginx
```

---

## Deploy Updates (after initial setup)

```bash
# 1. Rsync code (never --delete)
rsync -avz \
  --exclude='.git' --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='node_modules' --exclude='.env' --exclude='logs/' --exclude='media/' \
  ~/Documents/CommerceExpert/webClerk3/ \
  youruser@yourserver:/opt/yourserver/apps/webclerk3/

# 2. Collect static files
ssh youruser@yourserver "cd /opt/yourserver/apps/webclerk3 && \
  source venv/bin/activate && python manage.py collectstatic --noinput"

# 3. Run migrations (if any)
ssh youruser@yourserver "cd /opt/yourserver/apps/webclerk3 && \
  source venv/bin/activate && python manage.py migrate"

# 4. Restart services
ssh youruser@yourserver "sudo systemctl restart webclerk3 && \
  sudo systemctl restart webclerk3-celery"
```

---

## Cloudflare SSL — If You Use It

If Cloudflare terminates SSL (recommended), two settings prevent infinite redirect loops:

**Django settings.py:**
```python
SECURE_SSL_REDIRECT = not DEBUG
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

**Nginx** (hardcode `https`, not `$scheme` — Cloudflare forwards HTTP to your server):
```nginx
proxy_set_header X-Forwarded-Proto https;
```

Without both, Django sees HTTP, returns 301 to HTTPS, Cloudflare strips SSL, Django sees HTTP again — infinite loop.

---

## Verification

After any deploy:
```bash
curl -s -o /dev/null -w "%{http_code}" https://yourdomain.com/          # 200 landing
curl -s -o /dev/null -w "%{http_code}" https://yourdomain.com/app/      # 200 React
curl -s -o /dev/null -w "%{http_code}" https://yourdomain.com/wcapi/    # 401 (auth required = working)
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 502 Bad Gateway | Gunicorn not running | `sudo systemctl status webclerk3` → restart if needed |
| 404 on all pages | Server directory permissions too restrictive | `sudo chmod o+x /opt/yourserver` |
| Infinite redirect loop | Missing Cloudflare SSL headers | Add both `SECURE_PROXY_SSL_HEADER` and Nginx `X-Forwarded-Proto` |
| Static files 404 | Forgot `collectstatic` | Run `python manage.py collectstatic --noinput` |
| `runserver` warning | Using dev server locally | Expected — keep it for development, use Gunicorn on server |

---

## Running a Read-Only Demo Instance

WebClerk supports running a second instance as a read-only demo on the same server. Four layers of protection prevent any data modification:

| Layer | What it does | Setting |
|-------|-------------|---------|
| **1. Middleware** | Blocks all POST/PUT/PATCH/DELETE HTTP methods | `READ_ONLY_MODE=True` in `.env` |
| **2. Save view** | Returns 405 at the application layer before any processing | Same setting, checked in `SaveWcapiView.post()` |
| **3. Delete view** | Returns 405 for all delete requests | Same setting, checked in `WCAPIDeleteView._do_delete()` |
| **4. Database user** | PostgreSQL role with SELECT-only privileges | Separate DB user in `.env` |

Django admin is also automatically disabled when `READ_ONLY_MODE=True`.

### Demo .env

```env
DB_MODE=local
LOCAL_DATABASE_NAME=commerce_demo
LOCAL_DATABASE_USER=webclerk_demo_ro
LOCAL_DATABASE_PASS=your_readonly_password
LOCAL_DATABASE_HOST=localhost
LOCAL_DATABASE_PORT=5432
DEBUG=False
READ_ONLY_MODE=True
```

### Creating the read-only database user

```bash
sudo -u postgres psql -d commerce_demo << 'SQL'
CREATE ROLE webclerk_demo_ro WITH LOGIN PASSWORD 'your_readonly_password';
GRANT CONNECT ON DATABASE commerce_demo TO webclerk_demo_ro;
GRANT USAGE ON SCHEMA public TO webclerk_demo_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO webclerk_demo_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO webclerk_demo_ro;
SQL
```

### Seeding demo data

```bash
cd /opt/yourserver/apps/webclerk3-demo
source venv/bin/activate

# Use the read-write user temporarily for seeding
# (edit .env to use the full-privilege user, then switch back)
python manage.py seed_freshstart
python manage.py seed_demo
python manage.py seed_demo_transactions
```

### Nginx routing (same server, different port)

Add demo location blocks inside the existing server block:

```nginx
# Demo API (port 8001)
location /demo/wcapi/ {
    rewrite ^/demo/wcapi/(.*) /wcapi/$1 break;
    proxy_pass http://127.0.0.1:8001;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto https;
}
location /demo/static/ {
    alias /opt/yourserver/apps/webclerk3-demo/staticfiles/;
}
location /demo/app/ {
    alias /opt/yourserver/apps/react2025/dist/;
    try_files $uri $uri/ /demo/app/index.html;
}
```

---

## See Also

- [Deployment Architecture Flowchart](../../charts/flowcharts/wc3-deployment.pdf) — visual overview
- [Minimal Viable Install](minimal-viable-install.md) — seed commands and demo data
- [Production Database](production-db.md) — database setup and backup
- [Celery Architecture](../../../readmes/69-celery-architecture.md) — background task details
