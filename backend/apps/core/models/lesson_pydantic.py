"""
Pydantic schemas for Lesson JSON envelopes.

Lesson — what was learned (core). Who it is about: contact_id; what it is about: subject_type /
subject_key; the lesson in one line: summary — never duplicated here.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from common.schemas.envelopes import (
    ActionsBase, CommentsBase, ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef,
)


class LessonConfig(ConfigBase):
    """The understanding: one typed leaf, so readers see it; its shape varies by subject_type
    (Lesson docstring). flow/qa_frequency: topics, top_questions, total_questions."""
    details: dict = Field(default_factory=dict)


class LessonMetadata(MetadataBase):
    pass


class LessonPrefs(RecordPrefsBase):
    pass


class LessonComments(CommentsBase):
    pass


class LessonActions(ActionsBase):
    pass


class LessonRefs(RefsBase):
    """links.log: the Log rows the lesson was drawn from (evidence)."""
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


class LessonSettingDefaults(BaseModel):
    status: str = "active"
