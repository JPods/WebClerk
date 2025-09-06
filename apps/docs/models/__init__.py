"""Docs app models package.

Ensure Django loads model classes defined in submodules by importing them here.
This allows apps.get_model('docs', 'Document') and similar lookups to succeed.
"""

from .document import Document  # noqa: F401
from .qa import Qa  # noqa: F401
from .tag import Tag  # noqa: F401
from .linkage import Linkage  # noqa: F401

__all__ = [
	"Document",
	"Qa",
	"Tag",
	"Linkage",
]
