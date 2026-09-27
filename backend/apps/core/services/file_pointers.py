"""Records that point at a file which is not there (Bill, 2026-09-27).

"People will move folders without changing links" — so Alice looks every night. A stored path
is a pointer like any BigInt id: when its target goes, nothing cascades and nothing complains.
This finds them; it never deletes or repairs. The findings go to the work folder 'audits' for
Alice to coach from (who moved what, and which records now point at nothing).

    document   path.key under DATA_DIR              (upload_view.document_file)
    bundle     config.payload_path under WORK_DIR   (bundle_storage.load_payload_by_path)
    item       metadata.images.source == 'local'    → MEDIA_ROOT/images/item/<ida>/<size>.jpg
               (an ida renamed, or media/ moved, leaves the flag and loses the file)
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from django.conf import settings

SAMPLE = 20                                  # examples kept per kind; the count is always complete


def _document_misses() -> Dict[str, Any]:
    from apps.docs.models import Document
    from apps.docs.views.upload_view import document_file
    checked, missing = 0, []
    for doc in Document.objects.exclude(path={}).only('pk', 'name', 'path').iterator():
        path = doc.path if isinstance(doc.path, dict) else {}
        if path.get('storage', 'local') != 'local' or not path.get('key'):
            continue
        checked += 1
        f = document_file(doc)
        if not f or not os.path.exists(f):
            missing.append({'id': doc.pk, 'name': doc.name, 'key': path.get('key')})
    return {'checked': checked, 'missing': len(missing), 'examples': missing[:SAMPLE]}


def _bundle_misses() -> Dict[str, Any]:
    from apps.sync.models import Bundle
    from common.work_folders import work_root
    root = work_root().resolve()
    checked, missing = 0, []
    for b in Bundle.objects.exclude(config__payload_path='').filter(config__has_key='payload_path') \
            .only('pk', 'config').iterator():
        rel = (b.config or {}).get('payload_path') or ''
        if not rel:
            continue
        checked += 1
        f = (root / rel).resolve()
        if root not in f.parents or not f.exists():
            missing.append({'id': b.pk, 'payload_path': rel})
    return {'checked': checked, 'missing': len(missing), 'examples': missing[:SAMPLE]}


def _item_image_misses() -> Dict[str, Any]:
    from apps.products.models import Item
    root = Path(settings.MEDIA_ROOT) / 'images' / 'item'
    checked, missing = 0, []
    for item in Item.objects.filter(metadata__images__source='local').only('pk', 'ida', 'metadata').iterator():
        images = (item.metadata or {}).get('images') or {}
        sizes = [s for s in ('tn', 'md', 'hr') if images.get(s)]
        checked += 1
        gone = [s for s in sizes if not (root / str(item.ida) / f'{s}.jpg').exists()]
        if gone:
            missing.append({'id': item.pk, 'ida': item.ida, 'sizes': gone})
    return {'checked': checked, 'missing': len(missing), 'examples': missing[:SAMPLE]}


def audit(write: bool = True) -> Dict[str, Any]:
    """Every kind of stored path, checked against the disk. With write, the result is kept in
    work/audits/file-pointers-<UTC date>.json (the folder's own keep rule prunes old ones)."""
    result: Dict[str, Any] = {
        'dt': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'document': _document_misses(), 'bundle': _bundle_misses(), 'item_image': _item_image_misses(),
    }
    result['missing'] = sum(v['missing'] for v in result.values() if isinstance(v, dict))
    if write:
        from common.work_folders import work_folder
        out = work_folder('audits') / f'file-pointers-{result["dt"][:10]}.json'
        out.write_text(json.dumps(result, indent=2) + '\n')
        result['path'] = str(out)
    return result
