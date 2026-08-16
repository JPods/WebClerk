"""Model-specific envelope defaults.

Returns the correct default dict for any model's config/metadata/prefs/refs
by loading the Pydantic schema and calling model_dump().

The naming convention (common.schemas.{model_key}.{ClassName}{Suffix})
covers ~70 models mechanically. The match block handles exceptions.

Base defaults (universal, no model awareness) live in common/models.py:
    default_metadata(), default_refs(), default_prefs(), default_comments()

Usage:
    from common.schemas.defaults import get_envelope_default

    get_envelope_default('contact', 'metadata')  # -> ContactMetadata defaults
    get_envelope_default('serial', 'config')      # -> SerialConfig defaults
    get_envelope_default('touch', 'refs')          # -> RefsBase defaults (no schema file)
"""
from __future__ import annotations

import importlib
import logging

logger = logging.getLogger(__name__)


def _model_key_to_class(key: str) -> str:
    """Convert snake_case model key to PascalCase class prefix."""
    return ''.join(word.capitalize() for word in key.split('_'))


_ENVELOPE_SUFFIXES = {
    'config': 'Config',
    'metadata': 'Metadata',
    'prefs': 'Prefs',
    'refs': 'Refs',
}


def get_envelope_default(model_key: str, envelope: str) -> dict:
    """Return the default dict for a model's config/metadata/prefs/refs.

    Loads the Pydantic schema from common.schemas.{model_key}, instantiates
    with defaults, and returns model_dump().  Models without schema files
    fall back to the envelope base class.
    """
    if envelope not in _ENVELOPE_SUFFIXES:
        raise ValueError(f"envelope must be one of {list(_ENVELOPE_SUFFIXES)}")

    suffix = _ENVELOPE_SUFFIXES[envelope]

    # All models now have schema files — this match block reserved for future exceptions

    # Standard path — mechanical naming convention
    class_name = _model_key_to_class(model_key) + suffix
    try:
        module = importlib.import_module(f'common.schemas.{model_key}')
        cls = getattr(module, class_name)
        return cls().model_dump()
    except (ModuleNotFoundError, AttributeError) as exc:
        logger.warning(
            'get_envelope_default: no schema %s.%s — falling back to base (%s)',
            model_key, class_name, exc,
        )
        return _base_fallback(envelope)


def _base_fallback(envelope: str) -> dict:
    """Return base envelope defaults when no model-specific schema exists."""
    from common.schemas.envelopes import (
        ConfigBase, MetadataBase, RecordPrefsBase, RefsBase,
    )
    bases = {
        'config': ConfigBase,
        'metadata': MetadataBase,
        'prefs': RecordPrefsBase,
        'refs': RefsBase,
    }
    return bases[envelope]().model_dump()
