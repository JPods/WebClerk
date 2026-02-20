#!/usr/bin/env bash
# Start Celery worker + beat for webclerk3
# Usage: ./start_celery.sh          (worker + beat combined)
#        ./start_celery.sh worker   (worker only)
#        ./start_celery.sh beat     (beat only)
#        ./start_celery.sh stop     (kill all celery processes)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
source bin/activate
export DB_MODE="${DB_MODE:-remote}"
export DJANGO_SETTINGS_MODULE=webclerk3_api.settings

MODE="${1:-combined}"

case "$MODE" in
  stop)
    echo "Stopping all Celery processes..."
    pkill -f "celery -A webclerk3_api" 2>/dev/null || true
    echo "Done."
    ;;
  worker)
    echo "Starting Celery worker..."
    celery -A webclerk3_api worker \
      -l info \
      --concurrency=2 \
      -P solo \
      --without-heartbeat
    ;;
  beat)
    echo "Starting Celery beat..."
    celery -A webclerk3_api beat \
      -l info \
      --pidfile= \
      -s /tmp/celerybeat-webclerk3-schedule
    ;;
  combined)
    echo "Starting Celery worker + beat..."
    celery -A webclerk3_api worker \
      -l info \
      --concurrency=2 \
      -P solo \
      --without-heartbeat \
      -B \
      -s /tmp/celerybeat-webclerk3-schedule
    ;;
  *)
    echo "Usage: $0 {worker|beat|combined|stop}"
    exit 1
    ;;
esac
