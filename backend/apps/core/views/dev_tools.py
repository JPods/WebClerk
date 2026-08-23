"""
Dev Tools API - Development-only endpoints for managing dev environment.

WARNING: These endpoints should NEVER be enabled in production!
"""

import json
import os
import subprocess
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from decouple import config


def _is_dev_mode():
    """Check if we're in development mode."""
    return settings.DEBUG and config('DATA_SET_ID', default='').upper() in ('DEV', 'LOCAL')


def _get_dev_config_path():
    """Get path to dev-config.json."""
    base_dir = Path(settings.BASE_DIR)
    return base_dir / 'tools' / 'dev-config.json'


def _get_sync_status_path():
    base_dir = Path(settings.BASE_DIR)
    return base_dir / 'tools' / '.sync_status.json'


def _get_sync_status_path():
    base_dir = Path(settings.BASE_DIR)
    return base_dir / 'tools' / '.sync_status.json'


def _read_dev_config():
    """Read the dev configuration file."""
    config_path = _get_dev_config_path()
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {
        'db_mode': config('DB_MODE', default='remote'),
        'data_set_id': config('DATA_SET_ID', default='UNKNOWN'),
        'data_set_name': config('DATA_SET_NAME', default='Unknown'),
    }


def _write_dev_config(data):
    """Write to the dev configuration file."""
    config_path = _get_dev_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(data, f, indent=2)


def _update_env_file(new_mode):
    """Update the .env file with new DB_MODE."""
    env_path = Path(settings.BASE_DIR) / '.env'
    if not env_path.exists():
        return False
    
    lines = env_path.read_text().split('\n')
    updated_lines = []
    found = False
    
    for line in lines:
        if line.startswith('DB_MODE='):
            updated_lines.append(f'DB_MODE={new_mode}')
            found = True
        else:
            updated_lines.append(line)
    
    if not found:
        updated_lines.append(f'DB_MODE={new_mode}')
    
    env_path.write_text('\n'.join(updated_lines))
    return True


@require_http_methods(["GET"])
def dev_config_status(request):
    """
    GET /wcapi/dev/config/
    
    Returns current dev configuration. Only available in DEBUG mode.
    """
    if not _is_dev_mode():
        return JsonResponse({
            'status': 'error',
            'message': 'Dev tools are only available in development mode'
        }, status=403)
    
    dev_config = _read_dev_config()
    
    return JsonResponse({
        'status': 'success',
        'data': {
            'db_mode': config('DB_MODE', default='remote'),
            'data_set_id': config('DATA_SET_ID', default='UNKNOWN'),
            'data_set_name': config('DATA_SET_NAME', default='Unknown'),
            'available_modes': dev_config.get('available_modes', {
                'remote': {'label': 'Remote (Team)', 'description': 'Shared database for team collaboration'},
                'local': {'label': 'Local (Debug)', 'description': 'Local database for isolated debugging'}
            }),
            'restart_required': False,
        }
    })


@require_http_methods(["GET"])
def dev_sync_status(request):
    """
    GET /wcapi/dev/sync-status/

    Returns current remote->local sync status for dev tools progress UI.
    """
    if not _is_dev_mode():
        return JsonResponse({
            'status': 'error',
            'message': 'Dev tools are only available in development mode'
        }, status=403)

    status_path = _get_sync_status_path()
    data = {'state': 'idle', 'progress': 0, 'message': ''}
    if status_path.exists():
        try:
            with open(status_path, 'r') as handle:
                parsed = json.load(handle)
                if isinstance(parsed, dict):
                    data.update(parsed)
        except Exception:
            data = {'state': 'failed', 'progress': 100, 'message': 'Unable to parse sync status'}

    return JsonResponse({'status': 'success', 'data': data})


@require_http_methods(["GET"])
def dev_sync_status(request):
    """
    GET /wcapi/dev/sync-status/

    Returns current remote->local sync status for dev tools progress UI.
    """
    if not _is_dev_mode():
        return JsonResponse({
            'status': 'error',
            'message': 'Dev tools are only available in development mode'
        }, status=403)

    status_path = _get_sync_status_path()
    data = {'state': 'idle', 'progress': 0, 'message': ''}
    if status_path.exists():
        try:
            with open(status_path, 'r') as handle:
                parsed = json.load(handle)
                if isinstance(parsed, dict):
                    data.update(parsed)
        except Exception:
            data = {'state': 'failed', 'progress': 100, 'message': 'Unable to parse sync status'}

    return JsonResponse({'status': 'success', 'data': data})


@csrf_exempt
@require_http_methods(["POST"])
def dev_switch_mode(request):
    """
    POST /wcapi/dev/switch/
    
    Switch database mode. Only available in DEBUG mode.
    Body: { "mode": "remote" | "local" }
    """
    if not _is_dev_mode():
        return JsonResponse({
            'status': 'error',
            'message': 'Dev tools are only available in development mode'
        }, status=403)
    
    try:
        body = json.loads(request.body)
        new_mode = body.get('mode', '').lower()
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON body'
        }, status=400)
    
    if new_mode not in ('remote', 'local'):
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid mode. Use "remote" or "local"'
        }, status=400)
    
    current_mode = config('DB_MODE', default='remote')
    
    if new_mode == current_mode:
        return JsonResponse({
            'status': 'success',
            'message': f'Already using {new_mode} mode',
            'data': {'mode': new_mode, 'changed': False, 'restart_required': False}
        })
    
    # Use the same script as CLI path so mode switch + restart behavior stays consistent
    script_path = Path(settings.BASE_DIR) / 'tools' / 'switch-dataset.sh'
    if not script_path.exists():
        return JsonResponse({
            'status': 'error',
            'message': 'Switch script not found'
        }, status=500)

    try:
        # Run script in headless mode from API context:
        # - config-only switch (no data sync)
        # - stop tracked processes
        # - DO NOT spawn detached server processes
        # User restarts servers in the same console terminals.
        env = os.environ.copy()
        env['SWITCH_HEADLESS'] = '1'
        env['SKIP_RESTART'] = '1'
        env['REQUEST_CONSOLE_RESTART'] = '1'
        env['FORCE_LOCAL_SYNC'] = '0'
        env['SKIP_LOCAL_SYNC'] = '1'
        subprocess.Popen(
            ['bash', str(script_path), new_mode],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )
    except Exception as exc:
        return JsonResponse({
            'status': 'error',
            'message': f'Failed to initiate switch: {str(exc)}'
        }, status=500)

    return JsonResponse({
        'status': 'success',
        'message': f'Switched to {new_mode}. Auto-restart signal sent to Django console runner.',
        'data': {
            'mode': new_mode,
            'changed': True,
            'restart_required': True,
            'restarting': False,
            'same_console_required': True,
            'sync_attempted': False,
            'instructions': {
                'note': 'Mode switched (config only, no data sync). Use /wcapi/dev/sync/ to download or upload data separately. If Django is running via `./runserver.sh`, restart is triggered automatically in the same terminal.'
            },
        }
    })


@csrf_exempt
@require_http_methods(["POST"])
def dev_sync_data(request):
    """
    POST /wcapi/dev/sync/

    Trigger data sync between remote and local databases.
    Independent of which mode is active.
    Body: { "direction": "download" | "upload" }
      - download: remote → local
      - upload: local → remote
    """
    if not _is_dev_mode():
        return JsonResponse({
            'status': 'error',
            'message': 'Dev tools are only available in development mode'
        }, status=403)

    try:
        body = json.loads(request.body)
        direction = body.get('direction', '').lower()
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON body'
        }, status=400)

    if direction not in ('download', 'upload'):
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid direction. Use "download" (remote→local) or "upload" (local→remote)'
        }, status=400)

    base_dir = Path(settings.BASE_DIR)
    sync_status_file = base_dir / 'tools' / '.sync_status.json'

    if direction == 'download':
        script = base_dir / 'tools' / 'sync_remote_to_local.py'
        label = 'remote → local'
    else:
        script = base_dir / 'tools' / 'sync_local_to_remote.py'
        label = 'local → remote'

    if not script.exists():
        return JsonResponse({
            'status': 'error',
            'message': f'Sync script not found: {script.name}'
        }, status=500)

    py_bin = base_dir / 'bin' / 'python'
    if not py_bin.exists():
        py_bin = 'python'
    else:
        py_bin = str(py_bin)

    # Reset sync status before starting
    try:
        sync_status_file.write_text(json.dumps({
            'state': 'running',
            'progress': 0,
            'message': f'Starting {label} sync...'
        }))
    except Exception:
        pass

    try:
        cmd = [py_bin, str(script), '--status-file', str(sync_status_file)]
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as exc:
        return JsonResponse({
            'status': 'error',
            'message': f'Failed to start sync: {str(exc)}'
        }, status=500)

    return JsonResponse({
        'status': 'success',
        'message': f'Data sync started ({label}). Poll /wcapi/dev/sync-status/ for progress.',
        'data': {
            'direction': direction,
            'label': label,
            'started': True,
        }
    })


@csrf_exempt
@require_http_methods(["POST"])
def dev_restart_servers(request):
    """
    POST /wcapi/dev/restart/
    
    Trigger server restart. Only available in DEBUG mode.
    This will restart the calling server - response may not complete.
    """
    if not _is_dev_mode():
        return JsonResponse({
            'status': 'error',
            'message': 'Dev tools are only available in development mode'
        }, status=403)
    
    # Get the switch script path
    script_path = Path(settings.BASE_DIR) / 'tools' / 'switch-dataset.sh'
    
    if not script_path.exists():
        return JsonResponse({
            'status': 'error',
            'message': 'Restart script not found'
        }, status=500)
    
    # Read current mode
    dev_config = _read_dev_config()
    current_mode = dev_config.get('db_mode', 'remote')
    
    # Run restart in headless mode from API context.
    # Stops tracked processes and requires restart in main consoles.
    try:
        env = os.environ.copy()
        env['SWITCH_HEADLESS'] = '1'
        env['SKIP_RESTART'] = '1'
        env['REQUEST_CONSOLE_RESTART'] = '1'
        env['FORCE_LOCAL_SYNC'] = '0'
        env['SKIP_LOCAL_SYNC'] = '1'
        subprocess.Popen(
            ['bash', str(script_path), current_mode],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Auto-restart signal sent to Django console runner.',
            'data': {
                'restarting': False,
                'same_console_required': True,
                'instructions': {
                    'note': 'If run via `./runserver.sh`, restart is triggered automatically in the same terminal.',
                },
            }
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Failed to initiate restart: {str(e)}'
        }, status=500)
