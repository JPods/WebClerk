"""The products' code hooks (core/services/behaviours.py)."""
from apps.core.services.behaviours import HookContext, ModelBehaviour, register
from apps.core.services.door import Refused


class BillOfMaterialBehaviour(ModelBehaviour):
    NEW_REQUIRES = ('parent_item_id', 'child_item_id')


class ItemXrefBehaviour(ModelBehaviour):
    NEW_REQUIRES = ('item_id', 'source', 'external_sku')


class CatalogLineBehaviour(ModelBehaviour):
    """A catalog line prices one item, or the items its scope covers (Bill, 2026-10-22).

    `new` saves the line empty under its catalog; the save that fills it must name an item
    or a non-empty scope (all_items, categories, vendors). A line naming neither prices
    nothing, so it is refused with what to send.
    """
    NEW_REQUIRES = ('catalog_id',)

    def before_save(self, ctx: HookContext) -> None:
        line = ctx.obj
        if (line.config or {}).get('is_new'):
            return
        from pydantic import ValidationError
        from apps.products.models.catalog_line_pydantic import CatalogLineScope
        try:
            scope = CatalogLineScope.model_validate(line.scope or {})
        except ValidationError as e:
            raise Refused(400, 'invalid_scope',
                          'A catalog line\'s scope is {all_items: true|false, categories: '
                          '[category], vendors: [vendor id]}.', [str(e)])
        if line.item_id is None and not scope.names_something():
            raise Refused(400, 'catalog_line_covers_nothing',
                          'A catalog line prices an item, or the items its scope covers. Name '
                          'an item, or set scope: all_items true, categories, or vendors.',
                          ['item', 'scope'])


def register_products() -> None:
    register('bill_of_material', BillOfMaterialBehaviour())
    register('item_xref', ItemXrefBehaviour())
    register('catalog_line', CatalogLineBehaviour())
