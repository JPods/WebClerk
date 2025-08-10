#!/bin/bash

echo "Checking Docker..."
docker info >/dev/null 2>&1 && echo "Docker: ✅ running" || echo "Docker: ❌ NOT running"

echo "Checking Redis..."
nc -z localhost 6379 && echo "Redis: ✅ running" || echo "Redis: ❌ NOT running"

echo "Checking Celery..."
pgrep -fl celery | grep worker && echo "Celery: ✅ running" || echo "Celery: ❌ NOT running"

echo "Checking Python dependencies..."
missing=0
for pkg in Django celery redis djangorestframework; do
    pip show $pkg >/dev/null 2>&1 || { echo "❌ $pkg not installed"; missing=1; }
done
[ $missing -eq 0 ] && echo "Python dependencies: ✅ all installed"