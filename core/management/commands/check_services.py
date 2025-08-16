# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/management/commands/check_services.py
from django.core.management.base import BaseCommand
import subprocess
import socket
import importlib.metadata

REQUIRED_PACKAGES = [
    'Django',
    'celery',
    'redis',
    'djangorestframework',
    # Add any other critical packages here
]

class Command(BaseCommand):
    help = "Check if Docker, Redis, Celery, and critical Python dependencies are running/installed"

    def handle(self, *args, **kwargs):
        # Check Docker
        try:
            subprocess.check_output(['docker', 'info'])
            docker_status = "Docker: ✅ running"
        except Exception:
            docker_status = "Docker: ❌ NOT running"

        # Check Redis
        redis_status = "Redis: ❌ NOT running"
        try:
            sock = socket.create_connection(('localhost', 6379), timeout=1)
            redis_status = "Redis: ✅ running"
            sock.close()
        except Exception:
            pass

        # Check Celery (looks for running celery worker process)
        try:
            output = subprocess.check_output(['pgrep', '-fl', 'celery'])
            if b'worker' in output:
                celery_status = "Celery: ✅ running"
            else:
                celery_status = "Celery: ❌ NOT running"
        except Exception:
            celery_status = "Celery: ❌ NOT running"

        # Check Python dependencies
        missing = []
        for pkg in REQUIRED_PACKAGES:
            try:
                importlib.metadata.version(pkg)
            except importlib.metadata.PackageNotFoundError:
                missing.append(pkg)
        if missing:
            deps_status = f"Python dependencies: ❌ missing: {', '.join(missing)}"
        else:
            deps_status = "Python dependencies: ✅ all installed"

        self.stdout.write(self.style.SUCCESS("\n".join([
            docker_status, redis_status, celery_status, deps_status
        ])))