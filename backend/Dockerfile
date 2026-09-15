# WebClerk3 — Django backend
# React frontend is pre-built and copied into media/static/ before docker build.
# Run: cd ../React2025 && npm run build && cp -r dist/ ../webClerk3/media/static/
# Or use docker-build.sh which handles this automatically.
FROM python:3.13-slim

# System deps for psycopg2 and general use
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Application code
COPY . .

# Collect static files (React build should already be in media/static/)
RUN SECRET_KEY=build-only python manage.py collectstatic --no-input 2>/dev/null || true

# Entrypoint handles first-run detection
RUN chmod +x /app/tools/webclerk-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/tools/webclerk-entrypoint.sh"]
CMD ["gunicorn", "webclerk3_api.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
