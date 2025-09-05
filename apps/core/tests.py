# Django Test Suite for Universal API BaseModel and Contact
#
# To run all tests in this file:
#     python manage.py testclee core
#
# Summary:
# - Verifies all models inherit BaseModel and have metadata, refs, prefs fields.
# - Checks keyword generation, history timestamps, size limits, and metadata access.
# - Validates dt_verified property and string representation.
# - Simulates admin field editing.
# - Ensures codebase consistency and Universal API compatibility.

from django.test import TestCase
from django.apps import apps
from apps.core.models import Contact
import types

# python manage.py test core

class BaseModelTests(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(
            email="bill612@example.com",
            name_first="Bill",
            name_last="Tulson",
            company="TulCo",
            role="user"
        )

    def test_fields_exist(self):
        """Test that metadata, refs, prefs fields exist and have correct default structure."""
        self.assertIsInstance(self.contact.metadata, dict)
        self.assertIsInstance(self.contact.refs, dict)
        self.assertIsInstance(self.contact.prefs, dict)
        self.assertIn("keywords", self.contact.refs)
        self.assertIn("history", self.contact.metadata)

    def test_keyword_generation(self):
        """Test that update_keywords extracts keywords and limits to 50 unique values."""
        self.contact.name_first = "Bill"
        self.contact.name_last = "Tulson"
        self.contact.company = "TulCo"
        self.contact.save()
        keywords = self.contact.refs['keywords']
        self.assertIn("bill", keywords)
        self.assertIn("tulson", keywords)
        self.assertIn("tulco", keywords)
        self.assertLessEqual(len(keywords), 50)

    def test_history_timestamps(self):
        """Test that created and modified timestamps are set and updated."""
        dt_created = self.contact.metadata['history']['created']['dt']
        self.contact.name_first = "William"
        self.contact.save()
        dt_modified = self.contact.metadata['history']['modified']['dt']
        self.assertTrue(dt_modified >= dt_created)

    def test_size_limits(self):
        """Test that oversized metadata, refs, prefs raise ValueError."""
        big_str = "x" * (320001)
        self.contact.metadata['undefined'] = big_str
        with self.assertRaises(ValueError):
            self.contact.save()
        self.contact.metadata['undefined'] = {}
        self.contact.refs['keywords'] = [big_str]
        with self.assertRaises(ValueError):
            self.contact.save()
        self.contact.refs['keywords'] = []
        self.contact.prefs['userdefined'] = big_str
        with self.assertRaises(ValueError):
            self.contact.save()
        self.contact.metadata = big_str
        with self.assertRaises(ValueError):
            self.contact.save()

    def test_get_set_metadata_value(self):
        """Test get_metadata_value and set_metadata_value for nested keys."""
        self.contact.set_metadata_value('history.verified.dt', 1234567890)
        self.contact.save()
        value = self.contact.get_metadata_value('history.verified.dt')
        self.assertEqual(value, 1234567890)

    def dt_test_verified_property(self):
        """Test dt_verified property returns correct datetime or None."""
        self.contact.set_metadata_value('history.verified.dt', 1234567890000)
        self.contact.save()
        dt = self.contact.dt_verified
        self.assertIsNotNone(dt)
        self.contact.set_metadata_value('history.verified.dt', 0)
        self.contact.save()
        dt = self.contact.dt_verified
        self.assertIsNone(dt)

    def test_str_representation(self):
        """Test __str__ returns expected values."""
        self.assertEqual(str(self.contact), f"{self.contact.name_first} {self.contact.name_last}")
        self.contact.name_first = "Bill"
        self.contact.save()
        self.assertIn("Bill", str(self.contact))

    def test_admin_fields(self):
        """Test that Contact model fields are editable in admin (simulated)."""
        self.contact.company = "NewCo"
        self.contact.save()
        self.assertEqual(Contact.objects.get(pk=self.contact.pk).company, "NewCo")

    def test_all_models_inherit_basemodel(self):
        """Loop through all models in all apps to assure they inherit BaseModel."""
        BaseModel = apps.get_model('common', 'BaseModel')
        for app_config in apps.get_app_configs():
            for model in app_config.get_models():
                # Skip abstract models and Django built-ins
                if model._meta.abstract or model.__module__.startswith('django.'):
                    continue
                # Check inheritance
                if hasattr(model, 'metadata') and hasattr(model, 'refs') and hasattr(model, 'prefs'):
                    self.assertTrue(issubclass(model, BaseModel),
                        f"{model.__name__} does not inherit from BaseModel but has BaseModel-like fields.")
