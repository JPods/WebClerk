"""Every panel list is the shared list (Bill, 2026-10-31: "all panels and lists have the same
inherited code"): an item's serials, cross references, specifications and BOM, a catalog's
lines, the inventory layers and a record's documents show the columns their models' layouts
name, and a BOM component and a catalog line open in a card.

A definition still holding the generated columns takes the designed ones; one a company changed
keeps its own. A card is added where there is none. Specification, now a listed model, gains its
definition from seed_model_definitions (which makes a missing one), not here: a definition made
by a migration carries access, and the test setup reads any such row as all models seeded.
"""
from django.db import migrations

GENERATED = {
    'serial': ['ida', 'purpose', 'status', 'serial_ida', 'item_ida', 'description'],
    'item_xref': ['ida', 'purpose', 'status', 'item_ida', 'external_sku', 'source_name'],
    'bill_of_material': ['ida', 'purpose', 'status', 'child_ida', 'child_description', 'quantity'],
    'catalog_line': ['purpose', 'status', 'adjustment_type', 'adjustment_value', 'catalog', 'discount_amount'],
    'inventory_layer': ['ida', 'purpose', 'status', 'item_ida', 'lot', 'source_doc_type'],
    'document': ['ida', 'purpose', 'status', 'name', 'mime_type', 'comments.process'],
}
CARDS = ('bill_of_material', 'catalog_line')


def update(apps, schema_editor):
    from apps.core import layouts
    Setting = apps.get_model('core', 'Setting')
    for d in Setting.objects.filter(purpose='wc:model', parent_model__in=set(GENERATED) | set(CARDS)):
        shipped = layouts.build(d.parent_model)
        config = dict(d.config or {})
        layout = dict(config.get('layout') or {})
        changed = False
        held = [c.get('field') for c in layout.get('panel') or [] if isinstance(c, dict)]
        if d.parent_model in GENERATED and held in ([], GENERATED[d.parent_model]):
            layout['panel'] = shipped['panel']
            changed = True
        cards = dict(layout.get('card') or {})
        edit = (shipped.get('card') or {}).get('edit')
        if d.parent_model in CARDS and edit and 'edit' not in cards:
            cards['edit'] = edit
            layout['card'] = cards
            changed = True
        if changed:
            config['layout'] = layout
            Setting.objects.filter(pk=d.pk).update(config=config)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0051_action_panel_card'),
    ]

    operations = [
        migrations.RunPython(update, migrations.RunPython.noop),
    ]
