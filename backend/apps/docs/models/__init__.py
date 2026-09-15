"""Docs app models package.

Ensure Django loads model classes defined in submodules by importing them here.
This allows apps.get_model('docs', 'Document') and similar lookups to succeed.
"""

from .document import Document  # noqa: F401
from .question_answer import QuestionAnswer  # noqa: F401
from .tag import Tag  # noqa: F401
from .linkage_entry import LinkageEntry  # noqa: F401

__all__ = [
	"Document",
	"QuestionAnswer",
	"Tag",
	"LinkageEntry",
]
