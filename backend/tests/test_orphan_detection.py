"""Tests for orphan detection service.

Validates detection of dangling FKs across required parent relationships.
Most transaction line FKs are NOT NULL, so null orphans won't exist —
the main risk is dangling FKs (parent deleted but child remains).
"""
import pytest
from tests.conftest import OrderFactory, ItemFactory, WarehouseFactory


@pytest.mark.django_db
class TestOrphanDetection:

    def test_counts_structure(self):
        """get_orphan_counts returns correct structure."""
        from apps.core.services.record_orphans import get_orphan_counts

        results = get_orphan_counts()
        assert isinstance(results, list)
        for r in results:
            assert 'model' in r
            assert 'fk_field' in r
            assert 'null_count' in r
            assert 'dangling_count' in r
            assert 'total_orphans' in r

    def test_detail_structure(self):
        """get_orphan_detail returns correct structure."""
        from apps.core.services.record_orphans import get_orphan_detail

        result = get_orphan_detail('transactions', 'OrderLine', 'order_id')
        assert 'total' in result
        assert 'records' in result
        assert isinstance(result['records'], list)

    def test_manage_action_counts(self):
        """Manage action get_orphan_counts works."""
        from apps.core.views.manage_view import _get_orphan_counts

        result = _get_orphan_counts({})
        assert 'orphans' in result
        assert 'total_orphans' in result
        assert 'tables_with_orphans' in result
        assert isinstance(result['total_orphans'], int)

    def test_manage_action_detail_requires_params(self):
        """Manage action get_orphan_detail requires app, model, fk_field."""
        from apps.core.views.manage_view import _get_orphan_detail

        with pytest.raises(ValueError, match="required"):
            _get_orphan_detail({})

    def test_manage_action_detail_valid_params(self):
        """Manage action get_orphan_detail works with valid params."""
        from apps.core.views.manage_view import _get_orphan_detail

        result = _get_orphan_detail({
            'app': 'transactions',
            'model': 'OrderLine',
            'fk_field': 'order_id',
            'type': 'null',
        })
        assert 'total' in result

    def test_invalid_model_returns_error(self):
        """get_orphan_detail with invalid model returns error."""
        from apps.core.services.record_orphans import get_orphan_detail

        result = get_orphan_detail('transactions', 'FakeModel', 'fake_id')
        assert 'error' in result

    def test_relationship_registry_complete(self):
        """All registered relationships reference real models."""
        from apps.core.services.record_orphans import REQUIRED_FK_RELATIONSHIPS

        for child_app, child_model, fk_field, parent_app, parent_model in REQUIRED_FK_RELATIONSHIPS:
            try:
                ChildModel = dj_apps.get_model(child_app, child_model)
                ParentModel = dj_apps.get_model(parent_app, parent_model)
            except Exception as e:
                pytest.fail(f"Invalid relationship: {child_app}.{child_model}.{fk_field} → {parent_app}.{parent_model}: {e}")


# Import at function scope for test_relationship_registry_complete
from django.apps import apps as dj_apps
