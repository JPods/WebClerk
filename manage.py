#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import socket
import subprocess
import time
import shutil

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')


def _redis_is_alive(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


class ServiceCheckError(RuntimeError):
    """Raised when a required service cannot be reached."""


def _emit(msg: str) -> None:
    sys.stdout.write(f'[redis] {msg}\n')
    sys.stdout.flush()


def ensure_redis_running() -> None:
    host = os.environ.get('REDIS_HOST', 'localhost')
    port = int(os.environ.get('REDIS_PORT', '6379'))
    if _redis_is_alive(host, port):
        _emit(f'reachable at {host}:{port}')
        return
    redis_bin = os.environ.get('REDIS_SERVER_BIN') or shutil.which('redis-server')
    if not redis_bin:
        raise ServiceCheckError('redis-server not found on PATH; please start Redis manually.')
    try:
        _emit(f'not reachable at {host}:{port}; attempting auto-start via {redis_bin}')
        # Daemonize to keep it alive after this process continues
        subprocess.run([redis_bin, '--daemonize', 'yes'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as exc:
        raise ServiceCheckError(f'failed to start redis-server automatically: {exc}') from exc
    for _ in range(10):
        if _redis_is_alive(host, port):
            _emit(f'auto-started and reachable at {host}:{port}')
            return
        time.sleep(0.2)
    raise ServiceCheckError('redis-server still unreachable after auto-start; please verify manually.')


def run_required_service_checks() -> None:
    if os.environ.get('DJANGO_SKIP_SERVICE_CHECKS') == '1':
        return
    ensure_redis_running()


def main():
    """Run administrative tasks."""
    if len(sys.argv) >= 2 and sys.argv[1] == 'runserver':
        try:
            run_required_service_checks()
        except ServiceCheckError as exc:
            sys.stderr.write(f'[runserver] aborting: {exc}\n')
            sys.exit(1)
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
