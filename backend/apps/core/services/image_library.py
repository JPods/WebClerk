"""
Image Library Service — Alice's image resolution pipeline.

Three sources, checked in order:
  1. Local library (MEDIA_ROOT/images/{model}/{ida}/{size}.png)
  2. Remote library (Connection with purpose='image_library' → supplier/WC_HQ)
  3. Placeholder (generated with initials/icon)

Standard sizes:
  tn.png      — 90x90 max (most 48x48), thumbnail for lists/cards
  display.png — 800x600 max, web display for detail pages
  hires.png   — original resolution, print/zoom

All PNG. Width adapts to height. No JPG.
"""

import hashlib
import io
import logging
from pathlib import Path

from django.conf import settings

logger = logging.getLogger('webclerk3.image_library')

# ── Standard sizes ──
SIZES = {
    'tn':      {'max_height': 90,  'max_width': 90},
    'display': {'max_height': 600, 'max_width': 800},
    'hires':   {'max_height': None, 'max_width': None},  # original
}

VALID_SIZES = set(SIZES.keys())


def get_image_root() -> Path:
    """Return the image library root directory."""
    root = Path(getattr(settings, 'MEDIA_ROOT', '')) / 'images'
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_image(model_name: str, ida: str, size: str = 'tn') -> dict:
    """
    Resolve an image through the three-source pipeline.

    Alice writes metadata.images on each record to cache the resolution:
      metadata.images = {
        "source": "local" | "remote:SupplierName" | "placeholder",
        "tn": true, "display": true, "hires": false
      }

    Once metadata.images.source is set, we skip the probe and go direct.
    Alice updates metadata.images when she learns about new image sources
    or when a supplier library changes.

    Returns {found: bool, path: str|None, bytes: bytes|None, source: str}
    """
    if size not in VALID_SIZES:
        return {'found': False, 'error': f"Invalid size '{size}'. Use: {', '.join(sorted(VALID_SIZES))}"}

    filename = f'{size}.png'

    # ── Fast path: check config.images on the record ──
    cached_source = _get_cached_source(model_name, ida)
    if cached_source:
        if cached_source == 'local':
            local = _check_local(model_name, ida, filename)
            if local:
                return local
        elif cached_source == 'placeholder':
            return _generate_placeholder(model_name, ida, size)
        # If cached source was remote but file is now local (cached), check local first
        local = _check_local(model_name, ida, filename)
        if local:
            return local

    # ── Full probe: local → remote → placeholder ──

    # 1. Local library
    local = _check_local(model_name, ida, filename)
    if local:
        _set_cached_source(model_name, ida, 'local', size)
        return local

    # 2. Remote library (Connection-based)
    remote = _check_remote_library(model_name, ida, filename)
    if remote:
        # Cache locally for next time
        _cache_locally(model_name, ida, filename, remote['bytes'])
        _set_cached_source(model_name, ida, remote['source'], size)
        return remote

    # 3. Placeholder — don't cache 'placeholder' as source so we re-probe
    #    next time (Alice may add images later)
    return _generate_placeholder(model_name, ida, size)


def _get_cached_source(model_name: str, ida: str) -> str | None:
    """Read metadata.images.source from the record.

    metadata.images structure: {source: str, tn: bool, display: bool, hires: bool}
    """
    try:
        Model = _resolve_model(model_name)
        if not Model:
            return None
        record = Model.objects.filter(ida=ida).values_list('metadata', flat=True).first()
        if record and isinstance(record, dict):
            images = record.get('images')
            if images and isinstance(images, dict):
                return images.get('source') or None
    except Exception:
        pass
    return None


def _set_cached_source(model_name: str, ida: str, source: str, size: str = None):
    """Write metadata.images on the record so future lookups skip the probe.

    Structure: {source, tn, display, hires}
    """
    try:
        Model = _resolve_model(model_name)
        if not Model:
            return
        record = Model.objects.filter(ida=ida).first()
        if record:
            metadata = record.metadata or {}
            images = metadata.get('images') or {'source': '', 'tn': False, 'display': False, 'hires': False}
            images['source'] = source
            if size:
                images[size] = True
            metadata['images'] = images
            Model.objects.filter(pk=record.pk).update(metadata=metadata)
    except Exception as e:
        logger.debug(f"Could not cache image source on {model_name}/{ida}: {e}")


def _resolve_model(model_name: str):
    """Find the Django model class by name — works for any model in the registry."""
    from django.apps import apps
    model_lower = model_name.lower()
    for model in apps.get_models():
        if model.__name__.lower() == model_lower:
            return model
    return None


def _check_local(model_name: str, ida: str, filename: str) -> dict | None:
    """Check local image library."""
    root = get_image_root()
    # Try: images/{model}/{ida}/{size}.png
    path = root / model_name / ida / filename
    if path.exists():
        return {
            'found': True,
            'path': str(path),
            'bytes': path.read_bytes(),
            'source': 'local',
            'content_type': 'image/png',
        }
    return None


def _check_remote_library(model_name: str, ida: str, filename: str) -> dict | None:
    """Check remote image libraries via Connection records."""
    try:
        from apps.sync.models import Connection
    except ImportError:
        return None

    # Find connections with purpose='image_library'
    connections = Connection.objects.filter(
        purpose='image_library',
        is_active=True,
    ).order_by('sequence')

    for conn in connections:
        base_url = (conn.config or {}).get('base_url', '')
        if not base_url:
            continue

        url = f"{base_url.rstrip('/')}/{model_name}/{ida}/{filename}"
        try:
            import requests as req
            resp = req.get(url, timeout=5)
            if resp.status_code == 200 and resp.headers.get('content-type', '').startswith('image/'):
                logger.info(f"Image found at remote library: {url}")
                return {
                    'found': True,
                    'bytes': resp.content,
                    'source': f'remote:{conn.name}',
                    'content_type': 'image/png',
                }
        except Exception as e:
            logger.debug(f"Remote library {conn.name} failed for {url}: {e}")
            continue

    return None


def _cache_locally(model_name: str, ida: str, filename: str, image_bytes: bytes):
    """Cache a remotely-fetched image locally."""
    root = get_image_root()
    dir_path = root / model_name / ida
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / filename
    path.write_bytes(image_bytes)
    logger.info(f"Cached image locally: {path}")


def _generate_placeholder(model_name: str, ida: str, size: str) -> dict:
    """Generate a simple SVG placeholder with initials."""
    dims = SIZES[size]
    h = dims['max_height'] or 200
    w = dims['max_width'] or 200
    side = min(w, h)

    # Extract initials from ida
    initials = ida[:2].upper() if ida else '??'

    # Color from ida hash
    hue = int(hashlib.md5(ida.encode()).hexdigest()[:2], 16) % 360
    bg = f'hsl({hue}, 25%, 85%)'
    fg = f'hsl({hue}, 30%, 35%)'

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{side}" height="{side}" viewBox="0 0 {side} {side}">
  <rect width="{side}" height="{side}" rx="4" fill="{bg}"/>
  <text x="50%" y="54%" dominant-baseline="middle" text-anchor="middle"
        font-family="Helvetica,Arial,sans-serif" font-size="{side * 0.35}" fill="{fg}">{initials}</text>
</svg>'''

    return {
        'found': False,
        'bytes': svg.encode('utf-8'),
        'source': 'placeholder',
        'content_type': 'image/svg+xml',
    }


def store_image(model_name: str, ida: str, size: str, image_bytes: bytes) -> dict:
    """Store an image in the local library."""
    if size not in VALID_SIZES:
        return {'error': f"Invalid size '{size}'. Use: {', '.join(sorted(VALID_SIZES))}"}

    filename = f'{size}.png'
    root = get_image_root()
    dir_path = root / model_name / ida
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / filename
    path.write_bytes(image_bytes)

    return {
        'stored': True,
        'path': str(path),
        'size_bytes': len(image_bytes),
        'model_name': model_name,
        'ida': ida,
        'image_size': size,
    }


def list_images(model_name: str, ida: str) -> dict:
    """List all images for a record."""
    root = get_image_root()
    dir_path = root / model_name / ida
    images = {}
    for size_name in VALID_SIZES:
        path = dir_path / f'{size_name}.png'
        if path.exists():
            images[size_name] = {
                'exists': True,
                'size_bytes': path.stat().st_size,
                'path': str(path),
            }
        else:
            images[size_name] = {'exists': False}

    return {
        'model_name': model_name,
        'ida': ida,
        'images': images,
    }
