"""Docs app serializers."""

from .question_answer import (
    QuestionAnswerSerializer,
    QuestionAnswerCreateSerializer,
    QuestionAnswerUpdateSerializer,
)
from .linkage_entry import (
    LinkageEntrySerializer,
    LinkageEntryCreateSerializer,
    LinkageEntryUpdateSerializer,
    LinkageGroupSerializer,
    LinkageGroupSummarySerializer,
)

__all__ = [
    # QuestionAnswer
    'QuestionAnswerSerializer',
    'QuestionAnswerCreateSerializer',
    'QuestionAnswerUpdateSerializer',
    # LinkageEntry
    'LinkageEntrySerializer',
    'LinkageEntryCreateSerializer',
    'LinkageEntryUpdateSerializer',
    'LinkageGroupSerializer',
    'LinkageGroupSummarySerializer',
]