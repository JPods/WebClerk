import unittest
from django.test import SimpleTestCase
from django.db import models
from common.models import BaseModel

try:
    from hypothesis import given, strategies as st
    HAS_HYPOTHESIS = True
except ImportError:  # hypothesis not installed
    HAS_HYPOTHESIS = False

class TempKWModel(BaseModel):
    title = models.CharField(max_length=120, blank=True)
    class Meta:
        app_label = 'core'
        managed = False

@unittest.skipUnless(HAS_HYPOTHESIS, 'hypothesis not installed')
class KeywordPropertyTests(SimpleTestCase):
    @given(st.text(min_size=0, max_size=60))
    def test_keywords_extraction_idempotent(self, txt):
        obj = TempKWModel(title=txt)
        obj.update_keywords()
        first = sorted(obj.refs['keywords'])
        obj.update_keywords()
        second = sorted(obj.refs['keywords'])
        self.assertEqual(first, second)
