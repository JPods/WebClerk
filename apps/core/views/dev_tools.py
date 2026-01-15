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
    
    # Update config files
    dev_config = _read_dev_config()
    dev_config['db_mode'] = new_mode
    _write_dev_config(dev_config)
    
    # Update .env file
    _update_env_file(new_mode)
    
    return JsonResponse({
        'status': 'success',
        'message': f'Switched to {new_mode} mode. Restart servers to apply.',
        'data': {
            'mode': new_mode,
            'changed': True,
            'restart_required': True,
            'restart_command': f'cd tools && ./switch-dataset.sh {new_mode}'
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
    
    # Spawn the restart script in background (it will kill this process)
    try:
        # Use nohup to detach from this process
        subprocess.Popen(
            ['bash', '-c', f'sleep 1 && {script_path} {current_mode} <<< "Y"'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Restart initiated. Servers will restart momentarily.',
            'data': {'restarting': True}
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Failed to initiate restart: {str(e)}'
        }, status=500)
