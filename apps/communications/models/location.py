"""Compatibility shim: the real implementation lives in `apps.communications.models.address`.

This module re-exports `Address` as `Location` to preserve imports during the transition; it's deprecated and will be removed in a later release.
"""
import warnings
from apps.communications.models.address import Address  # type: ignore

warnings.warn(
    "apps.communications.models.location.Location is deprecated; import Address from apps.communications.models.address instead",
    DeprecationWarning,
)

# Re-export for backward compatibility
Location = Address
__all__ = ["Location", "Address"]
