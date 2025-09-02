#!/bin/bash
# Start Redis server
redis-server &

# Start Django server
python manage.py runserver &

# Start Celery worker
celery -A webClerk3 worker --loglevel=info &