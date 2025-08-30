import pytest
from django.test import TestCase

from common.models import VersionConflictError
from apps.communications.models.domain import Domain

@pytest.mark.django_db
class AtomicJSONTests(TestCase):
    def setUp(self):
        self.obj = Domain.objects.create(path='https://example.com', type='website')

    def test_atomic_json_set_and_version_bump(self):
        old_version = self.obj.version
        updated, new_version = Domain.atomic_json_set(self.obj.pk, 'metadata', ['flags', 'schema_rev'], 2, expected_version=old_version)
        assert updated == 1
        assert new_version == old_version + 1
        refetched = Domain.objects.get(pk=self.obj.pk)
        assert refetched.metadata.get('flags', {}).get('schema_rev') == 2

    def test_version_conflict(self):
        old_version = self.obj.version
        Domain.atomic_json_set(self.obj.pk, 'metadata', ['flags', 'schema_rev'], 3, expected_version=old_version)
        with pytest.raises(VersionConflictError):
            Domain.atomic_json_set(self.obj.pk, 'metadata', ['flags', 'schema_rev'], 4, expected_version=old_version)

    def test_atomic_list_append(self):
        old_version = self.obj.version
        new_version = Domain.atomic_list_append(self.obj.pk, 'comments', ['notes'], {'text': 'hello'}, expected_version=old_version)
        assert new_version == old_version + 1
        refetched = Domain.objects.get(pk=self.obj.pk)
        assert len(refetched.comments.get('notes', [])) == 1

    def test_instance_atomic_set_and_append(self):
        obj = Domain.objects.create(path='https://example.com', type='website')
        v = obj.version
        # atomic_set via instance
        new_version = obj.atomic_set('metadata', ['flags', 'schema_rev'], 2, expected_version=v)
        assert new_version == v + 1
        assert obj.metadata['flags']['schema_rev'] == 2
        # atomic_append via instance
        v2 = obj.version
        new_version2 = obj.atomic_append('comments', ['notes'], {'text': 'hi', 'type': 'info'}, expected_version=v2)
        assert new_version2 == v2 + 1
        assert any(n.get('text') == 'hi' for n in obj.comments['notes'])
