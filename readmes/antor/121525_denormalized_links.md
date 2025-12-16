# Denormalize Links in Refs Object

## Overview
Implemented automatic denormalization of links in the `refs.links` object to include full object data instead of just IDs. This change ensures that linked entities are always available with their display fields without requiring additional database queries during serialization.

## Changes Made

### 1. Added Denormalization Fields Mapping (`common/models.py`)
- Added `LINK_DENORMALIZE_FIELDS` dictionary mapping model names to lists of fields to include when denormalizing
- Covers all major models in the project with appropriate fields for display and identification
- Fields are selected based on common display requirements (name, email, type, etc.)

### 2. Enhanced RefsMixin (`common/models.py`)
- **`denormalize_links()`**: Fetches related objects and returns denormalized data
- **`ensure_links_denormalized()`**: Updates `refs.links` in place, converting ID lists to object lists
- Handles both existing ID lists and already-denormalized data
- Gracefully handles missing models or invalid IDs

### 3. Modified BaseModel Save Process (`common/models.py`)
- Added call to `ensure_links_denormalized()` in the `save()` method
- Ensures all links are denormalized before saving to the database
- Maintains data consistency across all model instances

### 4. Updated Serialization Methods (`common/models.py`)
- **`to_universal_dict()`**: Now always returns denormalized links (removed parameter)
- **`as_pydantic()`**: Updated to work with automatic denormalization
- **`pydantic_dump()`**: Updated to work with automatic denormalization
- All serialization now includes full link data by default

### 5. Created Migration Management Command (`apps/core/management/commands/denormalize_links.py`)
- **`denormalize_links`**: Django management command to migrate existing data
- Supports dry-run mode to preview changes
- Can process specific models or all models
- Batch processing for large datasets
- Error handling and logging

## Data Structure Transformation

### Before
```json
{
  "refs": {
    "links": {
      "email": [2, 3],
      "contact": [1],
      "item": [5, 6]
    }
  }
}
```

### After
```json
{
  "refs": {
    "links": {
      "email": [
        {"id": 2, "email": "user@example.com", "name": "John Doe", "type": "work", "is_primary": true},
        {"id": 3, "email": "admin@example.com", "name": "Jane Smith", "type": "personal", "is_primary": false}
      ],
      "contact": [
        {"id": 1, "email": "contact@example.com", "name_first": "Alice", "name_last": "Johnson", "company": "ABC Corp", "title": "Manager", "role": "user"}
      ],
      "item": [
        {"id": 5, "name": "Widget A", "sku": "WGT-A", "description": "A useful widget", "kind": "physical", "uom": "EA"},
        {"id": 6, "name": "Service B", "sku": "SRV-B", "description": "A service offering", "kind": "service", "uom": "HR"}
      ]
    }
  }
}
```

## Model Field Mappings

The following fields are included for each model type:

- **Email**: id, email, name, type, is_primary
- **Contact**: id, email, name_first, name_last, company, title, role
- **Phone**: id, number, format, name
- **Location**: id, address1, city, state, zip, country, full
- **Item**: id, name, sku, description, kind, uom
- **Domain**: id, path, type
- **OrgBase**: id, display_name, org_type, status
- **Currency**: id, code, name, symbol
- **Term**: id, name
- **GlAccount**: id, account_credit
- **TaxJurisdiction**: id, name, code
- **ExchangeRate**: id, from_currency, to_currency, rate
- **PaymentMethod**: id, name, type
- **PaymentTerm**: id, name, terms
- **Project**: id, name, status
- **Catalog**: id, name, code, currency
- **Warehouse**: id, name, code
- **Connection**: id, name, type
- **Bundle**: id, name
- **Notification**: id, name
- **Setting**: id, name
- **Report**: id, name
- **Template**: id, purpose
- **Action**: id, name
- **AuditLog**: id, action
- **Document**: id, name, type
- **Tag**: id, name
- **Linkage**: id, name
- **QuestionAnswer**: id, question
- **SerialLog**: id, serial_number
- **InventoryCheck**: id, name
- **DeliveryVisit**: id, status
- **PurchaseReceipt**: id, receipt_number
- **PaymentApplication**: id, amount_applied
- **ProjectAssociation**: id, project_id
- **InventoryReservation**: id, quantity_reserved
- **InventoryAdjustmentProcessor**: id, status
- **InventoryMetricsSnapshot**: id, snapshot_date
- **PendingInventoryAdjustment**: id, adjustment_type
- **Variant**: id, name
- **BillOfMaterial**: id, parent_item_id
- **Service**: id, name
- **Campaign**: id, name
- **Support**: id, name

## Migration Instructions

To migrate existing data in the database:

1. **Dry run first** (recommended):
   ```bash
   python manage.py denormalize_links --dry-run
   ```

2. **Migrate all models**:
   ```bash
   python manage.py denormalize_links
   ```

3. **Migrate specific model**:
   ```bash
   python manage.py denormalize_links --model app_label.model_name
   ```

4. **Adjust batch size** (default 1000):
   ```bash
   python manage.py denormalize_links --batch-size 500
   ```

## Benefits

1. **Performance**: Eliminates N+1 queries when displaying linked entities
2. **Consistency**: All linked data is immediately available in API responses
3. **Simplicity**: No need for client-side lookups or additional API calls
4. **Reliability**: Data is denormalized at save time, ensuring consistency

## Considerations

1. **Storage**: Increased storage requirements due to duplicated data
2. **Updates**: Linked entity changes don't automatically update denormalized data
3. **Size Limits**: Large link sets may approach JSON field size limits
4. **Migration**: One-time migration required for existing data

## Future Enhancements

- Consider background jobs to refresh denormalized data when linked entities change
- Add configuration options for which fields to include per model
- Implement compression for large denormalized datasets
- Add validation for denormalized data consistency