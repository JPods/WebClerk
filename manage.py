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
    # Only run initialization in the main Django process, not the reloader
    if os.environ.get('RUN_MAIN') != 'true':
        # Check if Redis is running and start if not
        if len(sys.argv) > 1 and sys.argv[1] == 'runserver':
            import socket
            def is_redis_running(host='localhost', port=6379):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    result = sock.connect_ex((host, port))
                    sock.close()
                    return result == 0
                except:
                    return False

            if not is_redis_running():
                import subprocess
                import platform
                system = platform.system().lower()

                if system == 'darwin':  # macOS
                    try:
                        brew_prefix = subprocess.run(['brew', '--prefix'], capture_output=True, text=True).stdout.strip()
                        config_path = f"{brew_prefix}/etc/redis.conf"
                        subprocess.Popen(['redis-server', config_path])
                        print("Redis server started (macOS)")
                    except Exception as e:
                        print(f"Failed to start Redis on macOS: {e}")
                        print("Please start Redis manually: redis-server")
                        return
                elif system == 'linux':
                    # Try common Linux Redis config locations
                    config_paths = ['/etc/redis/redis.conf', '/etc/redis.conf']
                    config_path = None
                    for path in config_paths:
                        if os.path.exists(path):
                            config_path = path
                            break

                    if config_path:
                        subprocess.Popen(['redis-server', config_path])
                        print("Redis server started (Linux)")
                    else:
                        print("Redis config not found. Please start Redis manually: redis-server /path/to/redis.conf")
                        return
                else:
                    print(f"Unsupported OS: {system}. Please start Redis manually: redis-server")
                    return

                # Wait for Redis to be ready
                import time
                for _ in range(10):  # Wait up to 10 seconds
                    if is_redis_running():
                        print("Redis is now running")
                        break
                    time.sleep(1)
                else:
                    print("Warning: Redis may not have started properly")
            else:
                print("Redis is already running")

            # Test Celery connection to Redis
            try:
                import redis
                r = redis.Redis(host='localhost', port=6379, db=0)
                r.ping()
                print("Celery can connect to Redis successfully")
            except Exception as e:
                print(f"Warning: Celery cannot connect to Redis: {e}")

            # Check and remove .celery_started file if running runserver
            celery_started_path = os.path.join(os.path.dirname(__file__), '.celery_started')
            if os.path.exists(celery_started_path):
                print("Removing celery previous PID file...")
                os.remove(celery_started_path)
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
