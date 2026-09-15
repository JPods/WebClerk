"""Docs app serializers."""

from .question_answer_serializer import (
    QuestionAnswerSerializer,
    QuestionAnswerCreateSerializer,
    QuestionAnswerUpdateSerializer,
)
from .linkage_entry_serializer import (
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