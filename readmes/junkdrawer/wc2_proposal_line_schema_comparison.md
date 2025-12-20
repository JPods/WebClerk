# WC2 Proposal Line Schema Comparison

This document compares the schema from the legacy WC2 proposal line system (`wc2_proposalline.json`) with the new Django model structure in `apps/transactions/models/proposal_line.py` and its base classes `apps/transactions/models/base_line_model.py`.

## Overview

The legacy WC2 schema used individual database fields for each piece of data. The new schema consolidates many of these fields into JSON objects for better flexibility, normalization, and to support complex nested data structures.

## Detailed Field Mapping

| WC2 Field | WC3 Field/Location |
|-----------|-------------------|
| idNumProposal | proposal_id |
| itemNum | item.ida_item |
| qty | quantity.placed |
| description | item.description |
| costUnitofMeasure | item.unit_measure |
| costTaxable | tax.sales_rate |
| unitCost | cost.unit |
| extendedCost | cost.extended |
| probability | metadata.probability |
| costValueAddedTax | cost.tax |
| costFreight | cost.freight |
| location | metadata.location |
| unitofMeasure | item.unit_measure |
| taxJuris | cost.tax_code |
| unitPrice | price.unit |
| extendedPrice | price.extended |
| discount | price.discount_amount |
| salesTax | tax.sales |
| extendedWt | physical.weight.value |
| calculateLine | computed |
| commRateSales | cost.commissions |
| unitWeight | physical.weight.value |
| flag1 | metadata.flag1 |
| flag2 | metadata.flag2 |
| note | metadata.note |
| leadTime | item.time_lead |
| commRateRep | cost.commissions |
| commRep | cost.commissions |
| commSales | cost.commissions |
| status | status |
| serialized | metadata.serialized |
| typeSale | metadata.typeSale |
| seq | item.sequence |
| altItemNum | metadata.altItemNum |
| complete | status |
| producedBy | metadata.producedBy |
| comment | metadata.comment |
| profile1 | metadata.profile1 |
| profile2 | metadata.profile2 |
| profile3 | metadata.profile3 |
| dateExpected | metadata.dateExpected |
| customerID | from parent proposal |
| lineNum | item.line_number |
| vendorID | metadata.vendorID |
| itemType | metadata.itemType |
| itemProfile1 | metadata.itemProfile1 |
| itemProfile2 | metadata.itemProfile2 |
| itemProfile3 | metadata.itemProfile3 |
| itemProfile4 | metadata.itemProfile4 |
| divisionNum | metadata.divisionNum |
| qtyOpen | quantity.remaining |
| idNum | ida |
| taxCost | cost.tax |
| printNot | metadata.printNot |
| locationBin | physical.locationBin |
| discountedPrice | computed |
| dtLastSync | metadata.dtLastSync |
| id | id |
| obGeneral | metadata.obGeneral |
| salesTaxRate | tax.sales_rate |

## Key Changes

### 1. Field Consolidation into JSON Objects

Many individual fields from WC2 have been grouped into JSON fields in the new model:

- `item` JSONField: Contains item-related data like description, unit_measure, etc.
- `quantity` JSONField: Contains quantity data like placed, remaining, etc.
- `cost` JSONField: Contains cost-related calculations like unit, extended, tax, etc.
- `price` JSONField: Contains price-related data like unit, discount, extended.
- `tax` JSONField: Contains tax information.
- `physical` JSONField: Contains physical attributes like weight, dimensions.
- `metadata` JSONField: Contains miscellaneous fields not fitting elsewhere.

### 2. Foreign Key Relationships

- `proposal_id`: Foreign key to the parent Proposal.

### 3. Computed Fields

Some WC2 fields that were stored are now computed dynamically, such as extended prices and costs.

## Migration Considerations

When migrating from WC2 to the new schema:

1. **Data Mapping:** Each old field needs to be mapped to its new location in JSON objects.
2. **Normalization:** Item and quantity data are properly structured.
3. **Calculations:** Extended amounts are computed from unit prices and quantities.
4. **Flexibility:** The JSON structure allows for future extensions without migrations.

## Benefits of New Structure

- **Scalability:** JSON fields can accommodate varying data structures.
- **Performance:** Computed fields reduce storage needs.
- **Maintainability:** Related data is properly normalized.
- **Extensibility:** Easy to add new fields without migrations.