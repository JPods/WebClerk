"""Tests for optional Pydantic integration on BaseModel.
Small step: ensure helper methods work with and without pydantic installed.
"""
from django.test import SimpleTestCase
from django.db import models

from common.models import BaseModel, PydanticBaseModel, UniversalAPISchema  # type: ignore


class TempModel(BaseModel):  # Unmanaged test-only model
    name = models.CharField(max_length=50, blank=True)

    class Meta:
        app_label = 'core'   # attach to existing app to satisfy Django
        managed = False      # no table creation needed


class BaseModelPydanticTests(SimpleTestCase):
    def test_to_universal_dict_keys(self):
        obj = TempModel(name='Example')
        data = obj.to_universal_dict()
        for key in ['id', 'uuid', 'metadata', 'refs', 'prefs', 'comments', 'health_rating']:
            self.assertIn(key, data)
        self.assertIn('history', data['metadata'])
        self.assertIn('created', data['metadata']['history'])
        # comments structure
        self.assertIn('notes', data['comments'])

    def test_keywords_pending_flag(self):
        obj = TempModel(name='Flag Test')
        self.assertFalse(obj.keywords_pending)
        obj.mark_keywords_dirty()
        self.assertTrue(obj.keywords_pending)
        obj.update_keywords()
        self.assertFalse(obj.keywords_pending)

    def test_as_pydantic_optional(self):
        obj = TempModel(name='Example 2')
        if PydanticBaseModel:
            schema = obj.as_pydantic()
            self.assertIsInstance(schema, UniversalAPISchema)
            again = obj.as_pydantic()
            self.assertIs(again, schema)
            dumped = obj.pydantic_dump()
            self.assertIsInstance(dumped, dict)
            self.assertIn('metadata', dumped)
        else:
            raw_any = obj.as_pydantic()
            # runtime guarantee: fallback returns dict
            self.assertIsInstance(raw_any, dict)
            raw: dict = raw_any  # type: ignore[assignment]
            self.assertIn('metadata', raw)
            dumped = obj.pydantic_dump()
            self.assertIsInstance(dumped, dict)
