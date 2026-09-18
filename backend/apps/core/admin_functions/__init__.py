"""
Admin Functions Registry — JSON in, JSON out.

Every admin function follows one pattern:
    def fn(params: dict) -> dict

Naming convention:
    af_{verb}_{noun}_{qualifier}

    Prefix:  af_ (admin function — always, no exceptions)
    Verbs:   purge, update, set, copy, move, merge, split, export, import, count, check, fix, seed
    Nouns:   records, field, status, refs, config, selection, duplicates, orphans
    Qualifier: optional scope (e.g., _by_model, _from_fixture, _to_csv, _bulk)

Examples:
    af_purge_records_faker      — delete seed/faker data
    af_update_field_bulk        — set one field on selected records
    af_set_status_bulk          — change status on selected records
    af_merge_duplicates         — combine duplicate records
    af_count_records_by_status  — tally records grouped by status
    af_check_orphans            — find records with broken FK references
    af_fix_refs_keywords        — repair malformed refs.keywords arrays
    af_export_records_to_json   — dump records as JSON fixture
    af_import_records_from_json — load records from JSON fixture
    af_seed_demo_data           — create demo/training data set

Registry:
    ADMIN_FUNCTIONS — dict of all registered functions
    get_function(name) — lookup by name
    list_functions() — list all with metadata
    run_function(name, params) — execute with logging

Usage:
    from apps.core.admin_functions import run_function
    result = run_function('purge_records_faker', {'model': 'document', 'confirm': True})
"""

import logging
from typing import Dict, Any, Callable, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ADMIN_FUNCTIONS: Dict[str, Dict[str, Any]] = {}


def register(
    name: str,
    description: str,
    params_schema: Dict[str, Dict[str, Any]],
    fn: Callable[[dict], dict],
    category: str = 'general',
    requires_confirmation: bool = False,
    dangerous: bool = False,
):
    """Register an admin function."""
    ADMIN_FUNCTIONS[name] = {
        'name': name,
        'description': description,
        'params_schema': params_schema,
        'fn': fn,
        'category': category,
        'requires_confirmation': requires_confirmation,
        'dangerous': dangerous,
    }


def get_function(name: str) -> Optional[Dict[str, Any]]:
    """Lookup a function by name."""
    return ADMIN_FUNCTIONS.get(name)


def list_functions(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all registered functions (without the callable)."""
    result = []
    for name, entry in sorted(ADMIN_FUNCTIONS.items()):
        if category and entry['category'] != category:
            continue
        result.append({
            'name': entry['name'],
            'description': entry['description'],
            'params_schema': entry['params_schema'],
            'category': entry['category'],
            'requires_confirmation': entry['requires_confirmation'],
            'dangerous': entry['dangerous'],
        })
    return result


def run_function(name: str, params: dict) -> dict:
    """Execute an admin function by name with JSON params.

    Returns:
        {"success": bool, "message": str, "data": any}
    """
    entry = ADMIN_FUNCTIONS.get(name)
    if not entry:
        return {'success': False, 'message': f'Unknown function: {name}', 'data': None}

    # Validate required params
    schema = entry['params_schema']
    for param_name, param_def in schema.items():
        if param_def.get('required') and param_name not in params:
            return {'success': False, 'message': f'Missing required param: {param_name}', 'data': None}

    # Check confirmation for dangerous operations
    if entry['requires_confirmation'] and not params.get('confirm'):
        return {'success': False, 'message': 'Confirmation required. Set confirm: true.', 'data': None}

    try:
        logger.info(f'admin_function:{name} params={params}')
        result = entry['fn'](params)
        logger.info(f'admin_function:{name} result={result.get("message", "ok")}')
        return result
    except Exception as e:
        logger.exception(f'admin_function:{name} failed: {e}')
        return {'success': False, 'message': str(e), 'data': None}


# ---------------------------------------------------------------------------
# Auto-register all functions from this package
# ---------------------------------------------------------------------------
from apps.core.admin_functions import data_functions  # noqa: E402, F401
from apps.core.admin_functions import record_functions  # noqa: E402, F401
