# Product Model Scalar Field Standardization

## Purpose
To ensure all product-related models in the `apps/products/models/` directory have the following scalar fields for consistency, admin compatibility, and integration:

- `item_id` (ForeignKey to Item or via ItemLinkedBase)
- `item_ida` (CharField, string identifier)
- `description` (CharField or TextField, human-readable description)

## Implementation Details
- All models representing a product instance (e.g., BillOfMaterial, Variant, ItemUsage, Serial, InventoryReservation, OrgItem, InventoryCheckLine) now include:
  - `item_ida = models.CharField(max_length=120, blank=True, db_index=True, help_text="String identifier for this record")`
  - `description = models.CharField(max_length=255, blank=True, help_text="Description for this record")`
- Properties `ida`, `item_ida_value`, and `description_value` are provided for admin and code compatibility.
- The `item_id` field remains a ForeignKey to Item or is inherited via ItemLinkedBase where appropriate.
- Warehouse and other non-product-instance models are excluded from this pattern.

## Migration Steps
1. **Model Changes**: Scalar fields and properties have been added to all relevant models.
2. **Migration**: Run Django migrations to apply these schema changes:
   ```sh
   python manage.py makemigrations apps.products
   python manage.py migrate apps.products
   ```
3. **Admin/Code Usage**: Use the new scalar fields and properties for consistent referencing, display, and integration.

## Benefits
- Uniformity across all product models
- Easier admin configuration and list_display
- Simplified integration and querying
- Future-proofing for reporting and API needs

---
_Last updated: January 24, 2026_
