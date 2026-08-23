"""Data integrity tests.

Validates:
  - Export/import roundtrip preserves record counts and FK integrity
  - Refs↔FK consistency via RefsMismatchLog
  - Soft delete exclusion from default queries
  - Version conflict detection
"""
import pytest
import json
import tempfile
import os
from decimal import Decimal

from tests.conftest import (
    CustomerFactory, ContactFactory, ItemFactory,
    OrderFactory, InvoiceFactory, WarehouseFactory,
)


@pytest.mark.django_db
class TestExportImportRoundtrip:
    """Export data → clear → import → verify counts match."""

    def test_roundtrip_preserves_records(self):
        """Create records, export, clear, import, verify counts."""
        from django.core import serializers
        from apps.orgs.models import OrgBase
        from apps.products.models import Item
        from apps.core.models import Contact

        # Create test data
        customer = CustomerFactory(display_name="Roundtrip Corp")
        contact = ContactFactory(email="roundtrip@test.com", customer=customer)
        item = ItemFactory(ida="RT-001", description="Roundtrip Widget")

        # Record counts before export
        org_count = OrgBase.objects.count()
        contact_count = Contact.objects.count()
        item_count = Item.objects.count()

        assert org_count >= 1
        assert contact_count >= 1
        assert item_count >= 1

        # Export to JSON strings
        org_json = serializers.serialize('json', OrgBase.objects.all())
        contact_json = serializers.serialize('json', Contact.objects.all())
        item_json = serializers.serialize('json', Item.objects.all())

        # Verify JSON is valid and contains records
        org_data = json.loads(org_json)
        contact_data = json.loads(contact_json)
        item_data = json.loads(item_json)

        assert len(org_data) == org_count
        assert len(contact_data) == contact_count
        assert len(item_data) == item_count

        # Clear and reimport
        Contact.objects.all().delete()
        Item.objects.all().delete()
        OrgBase.objects.all().delete()

        assert OrgBase.objects.count() == 0

        # Import — order matters for FK integrity (orgs before contacts)
        for obj in serializers.deserialize('json', org_json):
            obj.save()
        for obj in serializers.deserialize('json', item_json):
            obj.save()
        for obj in serializers.deserialize('json', contact_json):
            obj.save()

        # Verify counts match
        assert OrgBase.objects.count() == org_count
        assert Contact.objects.count() == contact_count
        assert Item.objects.count() == item_count

    def test_fk_integrity_after_import(self):
        """After roundtrip, FK relationships are preserved."""
        from django.core import serializers
        from apps.orgs.models import OrgBase
        from apps.core.models import Contact

        customer = CustomerFactory(display_name="FK Test Corp")
        contact = ContactFactory(email="fk@test.com", customer=customer)
        original_customer_id = contact.customer_id

        # Export
        org_json = serializers.serialize('json', OrgBase.objects.all())
        contact_json = serializers.serialize('json', Contact.objects.all())

        # Clear + reimport
        Contact.objects.all().delete()
        OrgBase.objects.all().delete()
        for obj in serializers.deserialize('json', org_json):
            obj.save()
        for obj in serializers.deserialize('json', contact_json):
            obj.save()

        # FK preserved
        restored_contact = Contact.objects.get(email="fk@test.com")
        assert restored_contact.customer_id == original_customer_id
        assert restored_contact.customer is not None


@pytest.mark.django_db
class TestRefsFKConsistency:
    """Refs↔FK mismatch detection."""

    def test_log_mismatch_detects_drift(self):
        """RefsMismatchLog.log_mismatch creates entry when sets differ."""
        from apps.core.models.refs_mismatch_log import RefsMismatchLog

        entry = RefsMismatchLog.log_mismatch(
            parent_model='customer',
            parent_id=999,
            related_model='contact',
            fk_field='customer_id',
            fk_ids=[1, 2, 3],
            refs_ids=[1, 2],  # missing 3
            caller='test',
        )

        assert entry is not None
        assert entry.mismatch_type == 'fk_only'
        assert entry.only_in_fk == [3]
        assert entry.only_in_refs == []

    def test_log_mismatch_returns_none_when_matching(self):
        """No mismatch → returns None, no record created."""
        from apps.core.models.refs_mismatch_log import RefsMismatchLog

        entry = RefsMismatchLog.log_mismatch(
            parent_model='customer',
            parent_id=999,
            related_model='contact',
            fk_field='customer_id',
            fk_ids=[1, 2],
            refs_ids=[1, 2],
            caller='test',
        )
        assert entry is None

    def test_refs_only_mismatch(self):
        """ID in refs but not in FK → refs_only type."""
        from apps.core.models.refs_mismatch_log import RefsMismatchLog

        entry = RefsMismatchLog.log_mismatch(
            parent_model='customer',
            parent_id=999,
            related_model='contact',
            fk_field='customer_id',
            fk_ids=[1],
            refs_ids=[1, 5],  # 5 doesn't exist via FK
            caller='test',
        )
        assert entry.mismatch_type == 'refs_only'
        assert entry.only_in_refs == [5]


@pytest.mark.django_db
class TestSoftDeleteConsistency:
    """Soft-deleted records excluded from default queries."""

    def test_soft_delete_excludes_from_active(self):
        """Soft-deleted items don't appear in default queryset."""
        from apps.products.models import Item

        item = ItemFactory(ida="SOFT-001")
        assert Item.objects.filter(pk=item.pk).exists()

        # Soft delete
        Item.objects.filter(pk=item.pk).update(is_deleted=True)

        # Default manager (FullManager.active) should exclude it
        active = Item.objects.active()
        assert not active.filter(pk=item.pk).exists()

        # But .deleted() should find it
        deleted = Item.objects.deleted()
        assert deleted.filter(pk=item.pk).exists()

    def test_restore_returns_to_active(self):
        """Restoring a soft-deleted record makes it active again."""
        from apps.products.models import Item

        item = ItemFactory(ida="RESTORE-001")
        Item.objects.filter(pk=item.pk).update(is_deleted=True)
        assert not Item.objects.active().filter(pk=item.pk).exists()

        Item.objects.filter(pk=item.pk).update(is_deleted=False)
        assert Item.objects.active().filter(pk=item.pk).exists()


@pytest.mark.django_db
class TestVersionConflict:
    """Optimistic concurrency via version field."""

    def test_version_increments_on_save(self):
        """Each save bumps the version number."""
        item = ItemFactory(ida="VER-001")
        v1 = item.version

        item.description = "Updated"
        item.save()
        assert item.version == v1 + 1

    def test_assert_version_detects_stale(self):
        """assert_version queries DB and raises on mismatch."""
        from common.models import VersionConflictError

        item = ItemFactory(ida="CONFLICT-001")
        original_version = item.version

        # Simulate concurrent edit: bump version in DB
        item.__class__.objects.filter(pk=item.pk).update(version=original_version + 5)

        with pytest.raises(VersionConflictError):
            item.assert_version(original_version)
