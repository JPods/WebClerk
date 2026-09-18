#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')


def main():
    """Run administrative tasks."""

    # Ensure log directory and file exist
    log_dir = os.path.join(os.path.dirname(__file__), '.local', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'webclerk3.log')
    if not os.path.exists(log_file):
        with open(log_file, 'w') as f:
            pass
    # Celery and Redis initialization removed for synchronous execution
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
