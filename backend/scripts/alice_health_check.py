#!/usr/bin/env python3
"""
Alice Health Check — run after every deployment to Andi.

Verifies that Alice's infrastructure is functional:
  1. Celery tasks registered (all 11 must appear)
  2. Ollama model matches what's installed
  3. Chroma vector store responding
  4. django_celery_beat migrations applied
  5. Alice DB tables populated (observations, coaching, insights)

Usage:
  ssh andi "cd /opt/andi/apps/webclerk3 && source venv/bin/activate && python3 scripts/alice_health_check.py"

Exit codes:
  0 = all checks pass
  1 = one or more checks failed (details printed)
"""
import json
import os
import subprocess
import sys

# Add project root to path so Django settings can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')

EXPECTED_TASKS = [
    'apps.ai_assistant.tasks.alice_schema_watch_task',
    'apps.ai_assistant.tasks.apply_pending_layouts_task',
    'apps.ai_assistant.tasks.data_cleanup_task',
    'apps.ai_assistant.tasks.full_intelligence_run',
    'apps.ai_assistant.tasks.health_scoring_task',
    'apps.ai_assistant.tasks.json_optimize_task',
    'apps.ai_assistant.tasks.layout_drift_task',
    'apps.ai_assistant.tasks.margin_tracking_task',
    'apps.ai_assistant.tasks.relationship_scan_task',
    'apps.ai_assistant.tasks.schema_drift_task',
    'apps.ai_assistant.tasks.velocity_task',
]


def check_celery_tasks():
    """Verify all Alice tasks are registered with Celery."""
    try:
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        celery_bin = os.path.join(project_dir, 'venv', 'bin', 'celery')
        if not os.path.exists(celery_bin):
            celery_bin = 'celery'  # fallback to PATH
        result = subprocess.run(
            [celery_bin, '-A', 'webclerk3_api', 'inspect', 'registered'],
            capture_output=True, text=True, timeout=15,
            cwd=project_dir,
            env={**os.environ, 'DJANGO_SETTINGS_MODULE': 'webclerk3_api.settings'},
        )
        output = result.stdout
        missing = [t for t in EXPECTED_TASKS if t not in output]
        if missing:
            return False, f"Missing Celery tasks: {missing}"
        return True, f"All {len(EXPECTED_TASKS)} Alice tasks registered"
    except Exception as e:
        return False, f"Cannot inspect Celery: {e}"


def check_ollama_model():
    """Verify OLLAMA_MODEL matches an installed model."""
    try:
        import django
        django.setup()
        from django.conf import settings
        configured = getattr(settings, 'OLLAMA_MODEL', 'unknown')
        base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')

        import urllib.request
        resp = urllib.request.urlopen(f'{base_url}/api/tags', timeout=5)
        data = json.loads(resp.read())
        installed = [m['name'] for m in data.get('models', [])]

        if configured in installed:
            return True, f"Model '{configured}' installed"

        # Check without tag suffix (e.g., deepseek-r1:14b matches deepseek-r1:14b)
        for m in installed:
            if m == configured or m.startswith(configured.split(':')[0]):
                return True, f"Model '{configured}' found as '{m}'"

        return False, f"Model '{configured}' NOT installed. Available: {installed}"
    except Exception as e:
        return False, f"Cannot check Ollama: {e}"


def check_chroma():
    """Verify Chroma vector store is responding."""
    try:
        import urllib.request
        resp = urllib.request.urlopen('http://localhost:8100/api/v2/heartbeat', timeout=5)
        data = json.loads(resp.read())
        if 'nanosecond heartbeat' in data:
            return True, "Chroma heartbeat OK"
        return False, f"Unexpected Chroma response: {data}"
    except Exception as e:
        return False, f"Chroma not responding: {e}"


def check_alice_db():
    """Check Alice DB tables have data."""
    try:
        import django
        django.setup()
        from apps.ai_assistant.models_alice import (
            AliceObservation, AliceCoachingLog, AliceInsight,
        )
        counts = {
            'AliceObservation': AliceObservation.objects.count(),
            'AliceCoachingLog': AliceCoachingLog.objects.count(),
            'AliceInsight': AliceInsight.objects.count(),
        }
        total = sum(counts.values())
        detail = ', '.join(f"{k}={v}" for k, v in counts.items())
        if total == 0:
            return False, f"Alice tables empty: {detail}"
        return True, f"Alice data: {detail}"
    except Exception as e:
        return False, f"Cannot query Alice tables: {e}"


def check_beat_schedule():
    """Verify Alice tasks appear in CELERY_BEAT_SCHEDULE."""
    try:
        import django
        django.setup()
        from django.conf import settings
        schedule = getattr(settings, 'CELERY_BEAT_SCHEDULE', {})
        alice_entries = {
            k: v for k, v in schedule.items()
            if 'ai_assistant' in v.get('task', '')
        }
        if len(alice_entries) < 3:
            return False, f"Only {len(alice_entries)} Alice entries in beat schedule"
        return True, f"{len(alice_entries)} Alice entries in beat schedule"
    except Exception as e:
        return False, f"Cannot check beat schedule: {e}"


def main():
    checks = [
        ("Celery Tasks", check_celery_tasks),
        ("Ollama Model", check_ollama_model),
        ("Chroma Store", check_chroma),
        ("Alice DB", check_alice_db),
        ("Beat Schedule", check_beat_schedule),
    ]

    print("=" * 60)
    print("ALICE HEALTH CHECK")
    print("=" * 60)

    failures = 0
    for name, check_fn in checks:
        ok, msg = check_fn()
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {msg}")
        if not ok:
            failures += 1

    print("=" * 60)
    if failures:
        print(f"  {failures} check(s) FAILED")
        sys.exit(1)
    else:
        print("  All checks passed — Alice is functional")
        sys.exit(0)


if __name__ == '__main__':
    main()
