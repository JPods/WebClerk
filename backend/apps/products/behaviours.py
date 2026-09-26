"""The products' code hooks (core/services/behaviours.py)."""
from apps.core.services.behaviours import ModelBehaviour, register


class BillOfMaterialBehaviour(ModelBehaviour):
    NEW_REQUIRES = ('parent_item_id', 'child_item_id')


class ItemXrefBehaviour(ModelBehaviour):
    NEW_REQUIRES = ('item_id', 'source', 'external_sku')


def register_products() -> None:
    register('bill_of_material', BillOfMaterialBehaviour())
    register('item_xref', ItemXrefBehaviour())
