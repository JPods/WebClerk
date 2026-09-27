"""The ratchet: no code names a field its model does not have (Bill, 2026-09-26).

"We should run a loop on all model.scalar fieldnames to see if we have more dangling." When
Invoice.total was removed (branch and leaf), month-end, YTD, reconcile and statements kept
"working" as zeros; a renamed OrgBase.display_name left 11 readers, one of which made every
vCard-created org nameless. This walks every non-migration module and checks, for each
``Model.objects…`` chain and each ``Model(...)`` / ``.create(...)``, that the names it uses
are fields (or attnames, reverse relations, properties) of that model. A rename or removal
that strands a reader turns this red.

Not seen (text, not ORM): ``getattr(obj, 'gone', default)``, a queryset held in a variable
and filtered later, values read out of JSON.
"""
import ast
import pathlib

from django.apps import apps

ROOT = pathlib.Path(__file__).resolve().parent.parent

#: Known and owned — each entry names who removes it.
ALLOWED = {
    # allie-82, plan §16b item 9: the InventoryReservation model and these callers are deleted.
    ('InventoryReservation', 'expires_at'), ('InventoryReservation', 'context'),
    ('InventoryReservation', 'quantity'),
}

QS = {'filter', 'exclude', 'get', 'get_or_create', 'update_or_create', 'values', 'values_list',
      'order_by', 'only', 'defer', 'select_related', 'prefetch_related', 'aggregate', 'annotate',
      'update', 'distinct', 'count', 'exists', 'first', 'last', 'all', 'select_for_update', 'using',
      'create'}
FIELD_ARG = {'values', 'values_list', 'order_by', 'only', 'defer', 'select_related',
             'prefetch_related', 'distinct'}
LOOKUP_KW = {'filter', 'exclude', 'get', 'get_or_create', 'update_or_create', 'update', 'create'}
EXPR = {'Sum', 'Count', 'Max', 'Min', 'Avg', 'F'}
NOT_FIELDS = {'defaults', 'create_defaults'}


def _names(model):
    names = {'pk'}
    for f in model._meta.get_fields():
        names.add(f.name)
        if getattr(f, 'attname', None):
            names.add(f.attname)
        rq = getattr(f, 'related_query_name', None)
        if callable(rq):
            try:
                names.add(rq())
            except Exception:  # noqa: BLE001
                pass
    names |= {n for n in dir(model) if isinstance(getattr(model, n, None), property)}
    return names


def _models_by_name():
    by = {}
    for m in apps.get_models():
        by.setdefault(m.__name__, []).append(_names(m))
    return by


def _chain_root(node):
    chain = []
    while isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        chain.append(node)
        node = node.func.value
    if (isinstance(node, ast.Attribute) and node.attr in ('objects', 'all_objects', '_base_manager',
                                                          '_default_manager')
            and isinstance(node.value, ast.Name)):
        return node.value.id, chain
    return None, chain


def _exprs(node, out):
    for n in ast.walk(node):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            if n.func.id in EXPR and n.args and isinstance(n.args[0], ast.Constant) \
                    and isinstance(n.args[0].value, str):
                out.append(n.args[0].value)
            if n.func.id == 'Q':
                out.extend(k.arg for k in n.keywords if k.arg)


def find_dangling():
    models = _models_by_name()
    found = []
    for py in list(ROOT.glob('apps/**/*.py')) + list(ROOT.glob('common/**/*.py')):
        path = str(py)
        if '/migrations/' in path or '/tests/' in path:
            continue
        try:
            tree = ast.parse(py.read_text())
        except SyntaxError:
            continue
        seen = set()
        # A name this file defines or imports from a non-models module is not a model here
        # (carriers/base.py has its own Address dataclass).
        local = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
        local |= {a.asname or a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
                  and 'models' not in (n.module or '') for a in n.names}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or id(node) in seen:
                continue
            used, name = [], None
            if isinstance(node.func, ast.Name) and node.func.id in models \
                    and node.func.id not in local:                            # Model(field=…)
                name = node.func.id
                used = [k.arg for k in node.keywords if k.arg]
            else:
                name, chain = _chain_root(node)
                if not name or name not in models or not chain:
                    continue
                seen.update(id(c) for c in chain)
                aliases = set()
                for call in reversed(chain):
                    meth = call.func.attr
                    if meth not in QS:
                        continue
                    if meth in ('annotate', 'aggregate'):
                        aliases |= {k.arg for k in call.keywords if k.arg}
                    if meth in LOOKUP_KW:
                        used += [k.arg for k in call.keywords if k.arg]
                    if meth in FIELD_ARG:
                        used += [a.value for a in call.args
                                 if isinstance(a, ast.Constant) and isinstance(a.value, str)]
                    _exprs(call, used)
                used = [u for u in used if u.lstrip('-').split('__')[0] not in aliases]
            for u in used:
                head = u.lstrip('-').split('__')[0]
                if not head or head in NOT_FIELDS or (name, head) in ALLOWED:
                    continue
                if not any(head in names for names in models[name]):
                    found.append(f"{path.split('/backend/')[-1]}:{node.lineno} {name}.{head} ({u})")
    return sorted(set(found))


def test_no_code_names_a_field_its_model_does_not_have():
    dangling = find_dangling()
    assert not dangling, 'Dangling field names (a rename or removal stranded these):\n' + '\n'.join(dangling)
