"""
Statement Harvester API — JSON-based statement processing.

Statements live as JSON files on disk, not in the database.
Only promoted business lines become Payment records in psql.

Endpoints:
    POST /api/transactions/statements/harvest/    — harvest CSVs → JSON files
    GET  /api/transactions/statements/files/      — list JSON files with summaries
    GET  /api/transactions/statements/lines/      — load lines from a JSON file
    POST /api/transactions/statements/save/       — save classification changes back to JSON
    POST /api/transactions/statements/promote/    — promote business lines to Payment records
    POST /api/transactions/statements/export/     — export personal lines as CSV
"""
import json
import csv
import io
from pathlib import Path

from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET


def _safe_statement_path(filepath: str) -> Path | None:
    """Resolve filepath and ensure it stays inside the statements directory."""
    statements_dir = Path.home() / 'Allie' / 'statements'
    statements_dir.mkdir(parents=True, exist_ok=True)
    # If just a filename, resolve relative to statements dir
    p = Path(filepath)
    if not p.is_absolute():
        p = statements_dir / p
    resolved = p.resolve()
    if not resolved.is_relative_to(statements_dir.resolve()):
        return None
    return resolved


def _get_harvester():
    """Import statement_harvester from tools/."""
    import sys
    tools_dir = Path(__file__).resolve().parent.parent.parent.parent / 'tools'
    if str(tools_dir.parent) not in sys.path:
        sys.path.insert(0, str(tools_dir.parent))
    from tools.statement_harvester import (
        harvest_folder, harvest_file, save_json, load_json, save_json_changes,
        list_json_files, check_missing, learn_accounts, get_output_dir,
        promote_to_payments,
    )
    return {
        'harvest_folder': harvest_folder,
        'harvest_file': harvest_file,
        'save_json': save_json,
        'load_json': load_json,
        'save_json_changes': save_json_changes,
        'list_json_files': list_json_files,
        'check_missing': check_missing,
        'learn_accounts': learn_accounts,
        'get_output_dir': get_output_dir,
        'promote_to_payments': promote_to_payments,
    }


@login_required
@require_POST
def harvest_statements(request):
    """Harvest CSVs from a folder path → JSON files."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Staff access required'}, status=403)
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    folder_path = body.get('path', '').strip()
    if not folder_path:
        return JsonResponse({'error': 'path is required'}, status=400)

    p = Path(folder_path).expanduser()
    if not p.exists():
        return JsonResponse({'error': f'Path not found: {folder_path}'}, status=404)

    h = _get_harvester()

    if p.is_dir():
        lines, banks_found = h['harvest_folder'](str(p))
    elif p.is_file():
        file_lines, source, bank_name = h['harvest_file'](str(p))
        lines = file_lines
        banks_found = {bank_name: len(file_lines)} if file_lines else {}
    else:
        return JsonResponse({'error': f'Not a file or folder: {folder_path}'}, status=400)

    if not lines:
        return JsonResponse({
            'lines_saved': 0, 'lines_skipped': 0,
            'accounts': [], 'missing': [], 'files': [],
            'message': 'No lines parsed from the files in this folder.',
        })

    # Save to JSON files — one per source
    output_dir = h['get_output_dir']()
    by_source = {}
    for line in lines:
        by_source.setdefault(line['source'], []).append(line)

    files_created = []
    total_new = 0
    total_dup = 0
    for source, source_lines in sorted(by_source.items()):
        filepath, new, dup = h['save_json'](source_lines, source, output_dir)
        total_new += new
        total_dup += dup
        files_created.append({'filename': filepath.name, 'new': new, 'duplicates': dup})

    h['learn_accounts'](banks_found)
    missing = h['check_missing'](banks_found)

    accounts = [{'name': k, 'count': v} for k, v in sorted(banks_found.items())]

    return JsonResponse({
        'lines_saved': total_new,
        'lines_skipped': total_dup,
        'accounts': accounts,
        'missing': missing,
        'files': files_created,
        'message': f'Saved {total_new} new lines ({total_dup} duplicates) to {len(files_created)} files.',
    })


@login_required
@require_GET
def list_statement_files(request):
    """List all statement JSON files with summary info."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Staff access required'}, status=403)
    h = _get_harvester()
    files = h['list_json_files']()
    return JsonResponse({'files': files})


@login_required
@require_GET
def get_statement_lines(request):
    """Load lines from a specific JSON file. Supports pagination."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Staff access required'}, status=403)
    filepath = request.GET.get('file', '')
    if not filepath:
        return JsonResponse({'error': 'file parameter required'}, status=400)

    safe_path = _safe_statement_path(filepath)
    if safe_path is None:
        return JsonResponse({'error': 'Invalid file path'}, status=400)

    h = _get_harvester()
    lines = h['load_json'](str(safe_path))

    # Optional filters
    classification = request.GET.get('classification', '')
    if classification:
        lines = [l for l in lines if l.get('classification') == classification]

    source = request.GET.get('source', '')
    if source:
        lines = [l for l in lines if l.get('source') == source]

    promoted = request.GET.get('promoted', '')
    if promoted == 'true':
        lines = [l for l in lines if l.get('promoted')]
    elif promoted == 'false':
        lines = [l for l in lines if not l.get('promoted')]

    # Pagination
    offset = int(request.GET.get('offset', 0))
    limit = int(request.GET.get('limit', 100))
    total = len(lines)
    page_lines = lines[offset:offset + limit]

    return JsonResponse({
        'lines': page_lines,
        'total': total,
        'offset': offset,
        'limit': limit,
    })


@login_required
@require_POST
def save_statement_changes(request):
    """Save classification/category changes back to the JSON file."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Staff access required'}, status=403)
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    filepath = body.get('file', '')
    updates = body.get('updates', [])  # [{uuid, field, value}, ...]

    if not filepath or not updates:
        return JsonResponse({'error': 'file and updates required'}, status=400)

    safe_path = _safe_statement_path(filepath)
    if safe_path is None:
        return JsonResponse({'error': 'Invalid file path'}, status=400)

    h = _get_harvester()
    lines = h['load_json'](str(safe_path))

    # Build UUID lookup
    by_uuid = {l['uuid']: l for l in lines if 'uuid' in l}

    updated = 0
    for upd in updates:
        line = by_uuid.get(upd.get('uuid'))
        if not line:
            continue
        field = upd.get('field')
        value = upd.get('value')
        if field in ('classification', 'category', 'ledger', 'merchant'):
            line[field] = value
            updated += 1

    h['save_json_changes'](str(safe_path), lines)

    return JsonResponse({'updated': updated, 'message': f'Updated {updated} lines.'})


@login_required
@require_POST
def promote_statements(request):
    """Promote business lines from JSON to Payment records in psql."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Staff access required'}, status=403)
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    filepath = body.get('file', '')
    if not filepath:
        return JsonResponse({'error': 'file parameter required'}, status=400)

    safe_path = _safe_statement_path(filepath)
    if safe_path is None:
        return JsonResponse({'error': 'Invalid file path'}, status=400)

    h = _get_harvester()
    result = h['promote_to_payments'](str(safe_path))

    return JsonResponse({
        'created': result['created'],
        'skipped': result['skipped'],
        'already_promoted': result['already_promoted'],
        'message': f"Promoted {result['created']} lines to Payment records.",
    })


@login_required
@require_GET
def export_personal(request):
    """Export personal lines from a JSON file as CSV download."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Staff access required'}, status=403)
    filepath = request.GET.get('file', '')
    if not filepath:
        return JsonResponse({'error': 'file parameter required'}, status=400)

    safe_path = _safe_statement_path(filepath)
    if safe_path is None:
        return JsonResponse({'error': 'Invalid file path'}, status=400)

    h = _get_harvester()
    lines = h['load_json'](str(safe_path))
    personal = [l for l in lines if l.get('classification') == 'personal']

    if not personal:
        return JsonResponse({'error': 'No personal lines to export'}, status=404)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['date', 'description', 'amount', 'source', 'category'])
    for l in personal:
        writer.writerow([
            l.get('dt_transaction', '')[:10],
            l.get('description', ''),
            l.get('amount', 0),
            l.get('source', ''),
            l.get('category', ''),
        ])

    response = HttpResponse(output.getvalue(), content_type='text/csv')
    filename = Path(filepath).stem + '_personal.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
