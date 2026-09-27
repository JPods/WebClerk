"""Work folders — one secure sibling of the data folder (Bill, 2026-09-27).

    <install>/data/   backed up: what the company cannot recreate (database dumps, media, uploads)
    <install>/work/   everything else, one folder per job, owner-only; mostly junk, kept briefly

Code never builds a path under WORK_DIR by hand: it asks ``work_folder('logs')`` (or
``work_folder('bundles', 'journal')``). A name the manifest does not list is refused, so a new
folder is a manifest line, not a stray. ``WORK_DIR/manifest.json`` is the company's copy — its
keep_days and backup rule per folder, which Alice carries out (``scrub``); it is seeded from
``common/work_folders.json`` and gains any folder a newer WebClerk adds.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List

from django.conf import settings

_SEED = Path(__file__).with_name('work_folders.json')
_PART = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')     # one path part: no '..', no '/'


def work_root() -> Path:
    root = Path(settings.WORK_DIR)
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    return root


def _company_manifest() -> Dict[str, Any]:
    """The company's manifest file, seeded (and topped up) from the one shipped with WebClerk."""
    seed = json.loads(_SEED.read_text())
    path = work_root() / 'manifest.json'
    try:
        mine = json.loads(path.read_text())
    except (OSError, ValueError):
        mine = {}
    folders = mine.get('folders') or {}
    missing = {k: v for k, v in seed['folders'].items() if k not in folders}
    if missing or 'backup_targets' not in mine or not path.exists():
        mine = {'_about': seed['_about'], 'backup_targets': mine.get('backup_targets') or seed['backup_targets'],
                'folders': {**folders, **missing}}
        path.write_text(json.dumps(mine, indent=2) + '\n')
    return mine


def manifest() -> Dict[str, Dict[str, Any]]:
    """The folders and their rules (the company's copy)."""
    return _company_manifest()['folders']


def backup_targets() -> Dict[str, Path | None]:
    targets = _company_manifest().get('backup_targets') or {}
    local = targets.get('local')
    offsite = targets.get('offsite')
    return {'local': Path(os.path.expanduser(local)) if local else Path(settings.DATA_DIR) / 'work-backup',
            'offsite': Path(os.path.expanduser(offsite)) if offsite else None}


def _copy_new(src: Path, dst: Path) -> int:
    """Copy files that are new or changed; a backup never deletes."""
    import shutil
    copied = 0
    for f in src.rglob('*'):
        if not f.is_file():
            continue
        to = dst / f.relative_to(src)
        if to.exists() and to.stat().st_mtime >= f.stat().st_mtime and to.stat().st_size == f.stat().st_size:
            continue
        to.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, to)
        copied += 1
    return copied


def back_up(dry_run: bool = False) -> Dict[str, Any]:
    """Alice's copy of each folder by its backup rule. local → the local target; offsite → the
    local target and the offsite one (when the company named it). certs never go offsite."""
    root, targets = work_root(), backup_targets()
    copied: Dict[str, Dict[str, int]] = {}
    waiting: List[str] = []
    for name, rule in manifest().items():
        kind = rule.get('backup', 'none')
        src = root.joinpath(*name.split('/'))
        if kind == 'none' or not src.is_dir():
            continue
        places = {'local': targets['local']}
        if kind == 'offsite' and name != 'certs':
            if targets['offsite'] is None:
                waiting.append(name)
            else:
                places['offsite'] = targets['offsite']
        for where, base in places.items():
            n = 0 if dry_run else _copy_new(src, base.joinpath(*name.split('/')))
            copied.setdefault(name, {})[where] = n
    return {'copied': copied, 'offsite_waiting': waiting,
            'targets': {k: str(v) if v else None for k, v in targets.items()}}


def work_folder(name: str, *parts: str) -> Path:
    """The folder for this job, created on demand. Refused if the manifest does not name it,
    or if a part could climb out of it."""
    if name not in manifest():
        raise KeyError(f'"{name}" is not a work folder; add it to common/work_folders.json.')
    for part in parts:
        if not _PART.match(str(part)):
            raise ValueError(f'"{part}" is not a folder name.')
    path = work_root().joinpath(*name.split('/'), *map(str, parts))
    path.mkdir(parents=True, exist_ok=True)
    return path


def scrub(dry_run: bool = False) -> Dict[str, Any]:
    """Alice's pass over WORK_DIR: copy each folder by its backup rule, prune files past its
    keep_days, and name what no manifest entry owns (reported, never deleted)."""
    backed_up = back_up(dry_run)                 # copy first, so nothing is pruned before it is kept
    folders = manifest()
    root = work_root()
    now = time.time()
    pruned: Dict[str, int] = {}
    for name, rule in folders.items():
        days = rule.get('keep_days')
        base = root.joinpath(*name.split('/'))
        if days is None or not base.is_dir():
            continue
        cutoff = now - float(days) * 86400
        # A deeper manifest folder (imports/digest under imports) keeps its own rule.
        nested = [root.joinpath(*n.split('/')) for n in folders if n.startswith(name + '/')]
        for f in base.rglob('*'):
            if not f.is_file() or any(n in f.parents for n in nested):
                continue
            if f.stat().st_mtime < cutoff:
                pruned[name] = pruned.get(name, 0) + 1
                if not dry_run:
                    f.unlink()
    tops = {n.split('/')[0] for n in folders}
    strays: List[str] = sorted(p.name for p in root.iterdir()
                               if p.name not in tops and p.name != 'manifest.json')
    return {'pruned': pruned, 'strays': strays, 'dry_run': dry_run, 'backup': backed_up}
