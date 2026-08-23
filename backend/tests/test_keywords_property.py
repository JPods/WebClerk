import unittest
import pytest

try:
    from hypothesis import given, strategies as st
    HAS_HYPOTHESIS = True
except ImportError:  # hypothesis not installed
    HAS_HYPOTHESIS = False
    # Provide no-op decorators so class body doesn't fail during collection
    def given(*a, **kw):
        def decorator(fn):
            return fn
        return decorator
    class st:
        @staticmethod
        def text(**kw):
            return None

pytestmark = pytest.mark.django_db


@unittest.skipUnless(HAS_HYPOTHESIS, 'hypothesis not installed')
class KeywordPropertyTests(unittest.TestCase):
    @given(st.text(min_size=0, max_size=60))
    def test_keywords_extraction_idempotent(self, txt):
        from django.db import models
        from common.models import BaseModel

        class TempKWModel(BaseModel):
            title = models.CharField(max_length=120, blank=True)
            class Meta:
                app_label = 'core'
                managed = False

        obj = TempKWModel(title=txt)
        obj.update_keywords()
        first = sorted(obj.refs['keywords'])
        obj.update_keywords()
        second = sorted(obj.refs['keywords'])
        self.assertEqual(first, second)
