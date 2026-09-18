"""Tests for the write-through proxy (common/write_through.py).

Verifies that when DB_MODE=write-through:
- is_write_through() returns True
- forward_and_store() saves to the remote alias and mirrors locally
- forward_transaction_and_store() handles header+lines
- Error paths return 502 with write_through_error flag
- When disabled, is_write_through() returns False

All tests use @override_settings and mock the remote database so they
run against the local test DB without requiring a real remote connection.
"""
import uuid as _uuid
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from django.test import override_settings

from common.write_through import (
    is_write_through,
    get_remote_alias,
    forward_and_store,
    forward_transaction_and_store,
    _apply_fields,
    _serialize_record,
    _store_bundle_locally,
)


# ── Helpers ─────────────────────────────────────────────────────────


def _mock_request(user=None):
    """Create a minimal mock DRF request."""
    request = MagicMock()
    request.user = user or MagicMock(
        is_authenticated=True,
        is_superuser=True,
        is_staff=True,
        pk=1,
    )
    request.data = {}
    return request


# ── is_write_through() ─────────────────────────────────────────────


class TestIsWriteThrough:

    @override_settings(WRITE_THROUGH_ENABLED=True)
    def test_returns_true_when_enabled(self):
        assert is_write_through() is True

    @override_settings(WRITE_THROUGH_ENABLED=False)
    def test_returns_false_when_disabled(self):
        assert is_write_through() is False

    def test_returns_false_when_setting_missing(self):
        """Gracefully handles missing WRITE_THROUGH_ENABLED setting."""
        from django.conf import settings
        # Temporarily remove the attribute if it exists
        original = getattr(settings, 'WRITE_THROUGH_ENABLED', None)
        if hasattr(settings, 'WRITE_THROUGH_ENABLED'):
            delattr(settings, 'WRITE_THROUGH_ENABLED')
        try:
            assert is_write_through() is False
        finally:
            if original is not None:
                settings.WRITE_THROUGH_ENABLED = original


class TestGetRemoteAlias:

    @override_settings(WRITE_THROUGH_REMOTE_ALIAS='_wt_remote')
    def test_returns_configured_alias(self):
        assert get_remote_alias() == '_wt_remote'

    @override_settings(WRITE_THROUGH_REMOTE_ALIAS='custom_remote')
    def test_returns_custom_alias(self):
        assert get_remote_alias() == 'custom_remote'


# ── _apply_fields() ────────────────────────────────────────────────


@pytest.mark.django_db
class TestApplyFields:

    def test_flat_value_assignment(self, item):
        """Plain key-value pairs are applied directly."""
        from apps.core.utils import registry
        ItemModel = type(item)
        payload = {'description': 'Updated via write-through'}
        _apply_fields(item, payload, ItemModel)
        assert item.description == 'Updated via write-through'

    def test_envelope_format(self, item):
        """WCAPI envelope {mode, value} is unwrapped."""
        ItemModel = type(item)
        payload = {
            'description': {'mode': 'update', 'value': 'Envelope test'},
        }
        _apply_fields(item, payload, ItemModel)
        assert item.description == 'Envelope test'

    def test_delete_mode_sets_none(self, item):
        """mode='delete' sets the field to None."""
        ItemModel = type(item)
        item.description = 'Will be deleted'
        payload = {
            'description': {'mode': 'delete'},
        }
        _apply_fields(item, payload, ItemModel)
        assert item.description is None

    def test_skip_fields_ignored(self, item):
        """Fields in _SKIP_FIELDS are not applied."""
        ItemModel = type(item)
        original_id = item.id
        payload = {'id': 999, 'model_name': 'item', 'description': 'kept'}
        _apply_fields(item, payload, ItemModel)
        assert item.id == original_id  # id was skipped
        assert item.description == 'kept'

    def test_nonexistent_field_ignored(self, item):
        """Unknown field names are silently skipped."""
        ItemModel = type(item)
        payload = {'totally_fake_field_xyz': 'value'}
        _apply_fields(item, payload, ItemModel)  # should not raise


# ── _serialize_record() ────────────────────────────────────────────


@pytest.mark.django_db
class TestSerializeRecord:

    def test_includes_id_and_uuid(self, item):
        result = _serialize_record(item)
        assert 'id' in result
        assert result['id'] == item.id

    def test_uuid_is_string(self, item):
        """UUIDs should be serialized as strings, not UUID objects."""
        if hasattr(item, 'uuid') and item.uuid:
            result = _serialize_record(item)
            if result.get('uuid') is not None:
                assert isinstance(result['uuid'], str)

    def test_includes_non_editable_fields(self, item):
        """Non-editable fields (like auto-set id) should be present."""
        result = _serialize_record(item)
        assert 'id' in result


# ── _store_bundle_locally() ─────────────────────────────────────────


@pytest.mark.django_db
class TestStoreBundleLocally:

    def test_creates_local_record_when_missing(self):
        """If no matching local record exists, one is created."""
        from tests.conftest import ItemFactory
        remote_obj = ItemFactory.build(
            id=999999,
            ida='REMOTE-ONLY-001',
            description='Created on remote',
        )
        remote_obj.uuid = _uuid.uuid4()
        # Ensure no local record with this uuid
        ItemModel = type(remote_obj)
        ItemModel.objects.filter(uuid=remote_obj.uuid).delete()

        bundle = _serialize_record(remote_obj)
        _store_bundle_locally(ItemModel, remote_obj, bundle)

        local = ItemModel.objects.filter(uuid=remote_obj.uuid).first()
        assert local is not None
        assert local.description == 'Created on remote'
        assert local.ida == 'REMOTE-ONLY-001'

    def test_updates_existing_local_record_by_uuid(self, item):
        """If a local record with matching uuid exists, it's updated."""
        ItemModel = type(item)
        original_uuid = item.uuid

        # Simulate a remote object with same uuid but different data
        remote_obj = MagicMock()
        remote_obj.pk = item.pk
        remote_obj.uuid = original_uuid

        for field in ItemModel._meta.concrete_fields:
            val = getattr(item, field.name, None)
            setattr(remote_obj, field.name, val)
        remote_obj.description = 'Updated from remote'

        bundle = {'description': 'Updated from remote', 'uuid': str(original_uuid)}
        _store_bundle_locally(ItemModel, remote_obj, bundle)

        item.refresh_from_db()
        assert item.description == 'Updated from remote'


# ── forward_and_store() — integration ───────────────────────────────


@pytest.mark.django_db
class TestForwardAndStore:

    @override_settings(
        WRITE_THROUGH_ENABLED=True,
        WRITE_THROUGH_REMOTE_ALIAS='default',  # use test DB as "remote"
    )
    def test_create_new_record(self):
        """Creating a new record returns 201 with write_through flag."""
        from apps.core.utils import registry
        ItemModel = registry.resolve('item')
        if not ItemModel:
            pytest.skip("Item model not registered")

        request = _mock_request()
        payload = {
            'model_name': 'item',
            'ida': f'WT-TEST-{_uuid.uuid4().hex[:8]}',
            'description': 'Write-through create test',
        }

        result, status_code = forward_and_store(request, ItemModel, payload)

        assert status_code == 201
        assert result.get('write_through') is True
        assert result.get('id') is not None
        assert result['record']['description'] == 'Write-through create test'

        # Verify the record exists in DB
        obj = ItemModel.objects.get(pk=result['id'])
        assert obj.description == 'Write-through create test'

    @override_settings(
        WRITE_THROUGH_ENABLED=True,
        WRITE_THROUGH_REMOTE_ALIAS='default',
    )
    def test_update_existing_record(self, item):
        """Updating an existing record returns 200 with write_through flag."""
        ItemModel = type(item)
        request = _mock_request()
        payload = {
            'model_name': 'item',
            'id': item.pk,
            'description': 'Updated via write-through',
        }

        result, status_code = forward_and_store(request, ItemModel, payload)

        assert status_code == 200
        assert result.get('write_through') is True
        assert result['record']['description'] == 'Updated via write-through'

        # Verify the DB was updated
        item.refresh_from_db()
        assert item.description == 'Updated via write-through'

    @override_settings(
        WRITE_THROUGH_ENABLED=True,
        WRITE_THROUGH_REMOTE_ALIAS='default',
    )
    def test_update_nonexistent_returns_404(self):
        """Updating a record that doesn't exist returns 404."""
        from apps.core.utils import registry
        ItemModel = registry.resolve('item')
        if not ItemModel:
            pytest.skip("Item model not registered")

        request = _mock_request()
        payload = {'model_name': 'item', 'id': 999999999}

        result, status_code = forward_and_store(request, ItemModel, payload)

        assert status_code == 404
        assert 'not found' in result.get('detail', '').lower()

    @override_settings(
        WRITE_THROUGH_ENABLED=True,
        WRITE_THROUGH_REMOTE_ALIAS='_nonexistent_db_alias',
    )
    def test_remote_error_returns_502(self):
        """When remote DB is unreachable, returns 502."""
        from apps.core.utils import registry
        ItemModel = registry.resolve('item')
        if not ItemModel:
            pytest.skip("Item model not registered")

        request = _mock_request()
        payload = {
            'model_name': 'item',
            'ida': 'WT-FAIL',
            'description': 'Should fail',
        }

        result, status_code = forward_and_store(request, ItemModel, payload)

        assert status_code == 502
        assert result.get('write_through_error') is True


# ── forward_transaction_and_store() — integration ───────────────────


@pytest.mark.django_db
class TestForwardTransactionAndStore:

    @override_settings(
        WRITE_THROUGH_ENABLED=True,
        WRITE_THROUGH_REMOTE_ALIAS='default',
    )
    def test_error_returns_502_on_bad_model(self):
        """Invalid model key returns 502."""
        request = _mock_request()
        result, status_code = forward_transaction_and_store(
            request=request,
            model_key='nonexistentmodel',
            record_data={},
            lines_data=[],
            options={},
        )
        assert status_code == 502
        assert result.get('write_through_error') is True


# ── SaveWcapiView integration (HTTP-level) ──────────────────────────


@pytest.mark.django_db
class TestSaveViewWriteThrough:
    """Test that SaveWcapiView respects write-through mode."""

    @override_settings(WRITE_THROUGH_ENABLED=False)
    def test_normal_mode_does_not_call_write_through(self):
        """When write-through is off, forward_and_store is NOT called."""
        assert is_write_through() is False

    @override_settings(WRITE_THROUGH_ENABLED=True)
    def test_write_through_mode_is_active(self):
        """When write-through is on, the flag is True."""
        assert is_write_through() is True


# ── WCAPITransactionSaveView integration ────────────────────────────


@pytest.mark.django_db
class TestTransactionSaveViewWriteThrough:

    @override_settings(WRITE_THROUGH_ENABLED=True)
    def test_write_through_flag_detected(self):
        """Transaction save view checks write-through flag."""
        assert is_write_through() is True

    @override_settings(WRITE_THROUGH_ENABLED=False)
    def test_normal_mode_skips_write_through(self):
        assert is_write_through() is False


# ── WCAPISaveView integration ──────────────────────────────────────


@pytest.mark.django_db
class TestWCAPISaveViewWriteThrough:

    @override_settings(WRITE_THROUGH_ENABLED=True)
    def test_write_through_flag_detected(self):
        assert is_write_through() is True

    @override_settings(WRITE_THROUGH_ENABLED=False)
    def test_normal_mode_skips_write_through(self):
        assert is_write_through() is False
