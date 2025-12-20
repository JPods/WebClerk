# WC2 Proposal Schema Comparison

This document compares the schema from the legacy WC2 proposal system (`wc2_proposal.json`) with the new Django model structure in `apps/transactions/models/proposal.py` and its base class `apps/transactions/models/base_transaction_model.py`.

## Overview

The legacy WC2 schema used a flat structure with individual database fields for each piece of data. The new schema consolidates many of these fields into JSON objects for better flexibility, normalization, and to support complex nested data structures.

## Detailed Field Mapping

| WC2 Field | WC3 Field/Location |
|-----------|-------------------|
| customerID | customer_id |
| status | status |
| dateDocument | dt_created |
| dateNeeded | metadata.dateNeeded |
| idNum | ida |
| inquiryCode | metadata.inquiryCode |
| repID | cost.commissions.repID |
| repCommission | cost.commissions.repCommission |
| salesNameID | cost.commissions.salesNameID |
| salesCommission | cost.commissions.salesCommission |
| company | .refs.links.company |
| address1 | .refs.links.address | collection to be pulled from
| address2 | .refs.links.address |
| city | .refs.links.address |
| state | .refs.links.address |
| zip | .refs.links.address |
| country | .refs.links.address |
| shipVia | flow.shipVia |
| zone | flow.zone |
| typeSale | flow.source.typeSale |
| terms | finance.terms |
| idNumProject | parent_id |
| totalCost | totals.cost |
| phone | .refs.links.phone |
| taxCost | finance.cost_tax |
| amount | totals.subtotal |
| salesTax | totals.tax |
| shipAdjustments | totals.shipping |
| shipMiscCosts | totals.other |
| shipFreightCost | cost.freight |
| shipTotal | totals.shipping |
| total | totals.total |
| taxJuris | finance.sales_tax_name |
| fob | metadata.fob |
| shipInstruct | metadata.shipInstruct |
| comment | metadata.comment |
| attention | .refs.links.attention |
| autoFreight | metadata.autoFreight |
| daysValidFor | metadata.daysValidFor |
| daysLeadTime | metadata.daysLeadTime |
| grossMargin | totals.margin |
| dateExpected | action.dateExpected |
| probability | metadata.probability |
| obSync | metadata.obSync |
| weightEstimate | metadata.weightEstimate |
| lat | .refs.links.location.lat |
| adSource | source.campaign_id |
| lineCount | computed |
| docType | parent_type |
| docReference | parent_id |
| profile1 | metadata.profile1 |
| profile2 | metadata.profile2 |
| profile3 | metadata.profile3 |
| exchangeRate | finance.exchangeRate |
| currency | finance.currency |
| complete | status |
| bill2Company | .refs.links.company |
| actionTime | action.actionTime |
| exchangePrec | finance.exchangePrec |
| idNumOrder | parent_id |
| takenBy | metadata.takenBy |
| requestedBy | metadata.requestedBy |
| contactShipTo | .refs.links.contact |
| commentProcess | metadata.commentProcess |
| alertMessage | metadata.alertMessage |
| dateOrdered | dt_created |
| fax | .refs.links.fax |
| email | .refs.links.email |
| division | metadata.division |
| idNumTask | parent_id |
| addressBillTo | .refs.links.address |
| addressShipFrom | .refs.links.address |
| contactBillTo | .refs.links.contact |
| profile4 | metadata.profile4 |
| profile5 | metadata.profile5 |
| profile6 | metadata.profile6 |
| siteID | metadata.siteID |
| taxOnCost | finance.cost_tax |
| primaryForm | metadata.primaryForm |
| amountForceValue | metadata.amountForceValue |
| shipPartial | metadata.shipPartial |
| taxExemptid | finance.taxExemptid |
| countItems | computed |
| countItemsBl | computed |
| emailVerified | metadata.emailVerified |
| dtLastSync | metadata.dtLastSync |
| sector | metadata.sector |
| id | id |
| customerID2nd | metadata.customerID2nd |
| objective | metadata.objective |
| contractDetail | metadata.contractDetail |
| obGeneral | metadata.obGeneral |
| actionBy | action.actionBy |
| actionDate | action.actionDate |
| action | action.action |
| contractDetailTag | metadata.contractDetailTag |
| idCustomer | customer_id |
| idContactShip | .refs.links.contact |
| idContactBill | .refs.links.contact |
| actionDuration | action.actionDuration |
| phoneCell | .refs.links.phone |

## Key Changes

### 1. Field Consolidation into JSON Objects

Many individual fields from WC2 have been grouped into JSON fields in the new model:

#### Totals and Financial Fields
**Old WC2 Fields (individual):**
- `totalCost` (real)
- `taxCost` (real)
- `amount` (real)
- `salesTax` (real)
- `shipAdjustments` (real)
- `shipMiscCosts` (real)
- `shipFreightCost` (real)
- `shipTotal` (real)
- `total` (real)
- `grossMargin` (real)

**New Structure (JSON objects):**
- `totals` JSONField: Contains header-level cached totals
  - `subtotal`: sum of line extended sell before tax/ship/discount
  - `discount`: header discount amount
  - `taxable`: subtotal - discount subject to tax
  - `tax`: sales tax amount
  - `shipping`: shipping/handling charged to customer
  - `other`: misc charges
  - `total`: grand total customer-facing
  - `cost`: total cost (for margin compute)
  - `margin`: total - cost
  - `margin_pc`: (margin / total)*100
  - `received`: payments received (for invoices)
  - `balance`: total - received (for invoices)

- `cost` JSONField: Contains cost-related calculations
  - `line_sum_goods`
  - `line_sum_tax`
  - `line_sum_shipping`
  - `line_sum_handling`
  - `handling`
  - `freight`
  - `tax_rate`
  - `tax`
  - `commissions`
  - `total`

- `sell` JSONField: Contains sell-related calculations (structure similar to cost)

- `finance` JSONField: Contains financial details
  - `sales_tax_id`
  - `sales_tax_name`
  - `sales_tax_rate`
  - `sales_tax`
  - `cost_tax_id`
  - `cost_tax_name`
  - `cost_tax_rate`
  - `cost_tax`
  - `tax_subtotal`
  - `tax_pc`
  - `collection_expense`
  - `exchange_expense`

#### Commission and Representative Fields
**Old WC2 Fields:**
- `repID` (alpha)
- `repCommission` (real)
- `salesNameID` (alpha)
- `salesCommission` (real)

**New Structure:**
These are likely incorporated into the `cost` or `finance` JSON objects, specifically under `commissions` in the cost structure.

#### Shipping and Logistics Fields
**Old WC2 Fields:**
- `shipVia` (alpha)
- `zone` (longint)
- `fob` (alpha)
- `shipInstruct` (alpha)
- `autoFreight` (boolean)
- `weightEstimate` (real)

**New Structure:**
These may be part of the `flow` JSONField or stored in related shipping address/contact models.

#### Transaction Flow and Source Fields
**Old WC2 Fields:**
- `typeSale` (alpha)
- `terms` (alpha)
- `adSource` (alpha)
- `profile1-6` (alpha) - custom profile fields

**New Structure:**
- `flow` JSONField: Tracks transaction flow
  - `source`: array of source objects
  - `children`: array of child transactions

- `source` JSONField: Contains source information
  - `campaign_id`
  - `catalog_id`
  - `vendor_id`
  - `manufacturer_id`

- `action` JSONField: Contains action tracking
  - `action_next`: next action details

#### Address and Contact Fields
**Old WC2 Fields:**
- `company` (alpha)
- `address1` (alpha)
- `address2` (alpha)
- `city` (alpha)
- `state` (alpha)
- `zip` (alpha)
- `country` (alpha)
- `phone` (alpha)
- `fax` (alpha)
- `email` (alpha)
- `attention` (alpha)
- `bill2Company` (alpha)
- `contactShipTo` (longint)
- `contactBillTo` (longint)
- `addressBillTo` (alpha)
- `addressShipFrom` (alpha)

**New Structure:**
These are likely handled through separate contact and address models, referenced by foreign keys rather than stored directly in the proposal model.

### 2. Status and Lifecycle Fields

**Old WC2 Fields:**
- `status` (alpha)

**New Structure:**
- `status` CharField with predefined choices:
  - `planned`
  - `released`
  - `in_progress`
  - `hold`
  - `complete`
  - `canceled`

### 3. Date and Time Fields

**Old WC2 Fields:**
- `dateDocument` (date)
- `dateNeeded` (date)
- `dateExpected` (date)
- `dateOrdered` (date)
- `actionTime` (time)
- `actionDate` (date)
- `emailVerified` (date)

**New Structure:**
These are handled by the common `BaseModel` which includes:
- `dt_created`
- `dt_modified`
- `version`

Additional date fields may be stored in JSON objects or related models as needed.

### 4. Identifier Fields

**Old WC2 Fields:**
- `idNum` (longint, autosequence)
- `id` (alpha UUID)
- `idNumProject` (longint)
- `idNumOrder` (longint)
- `idNumTask` (longint)

**New Structure:**
- `id` (UUID from BaseModel)
- `ida` (string identifier from BaseModel)
- `customer_id` (BigIntegerField)
- `manufacturer_id` (BigIntegerField)
- `vendor_id` (BigIntegerField)
- `parent_id` (BigIntegerField)
- `parent_type` (CharField with choices)

### 5. Other Fields

**Old WC2 Fields:**
- `inquiryCode` (alpha)
- `takenBy` (alpha)
- `requestedBy` (alpha)
- `comment` (alpha)
- `commentProcess` (alpha)
- `alertMessage` (alpha)
- `objective` (blob)
- `contractDetail` (alpha)
- `contractDetailTag` (alpha)
- `obSync` (blob)
- `obGeneral` (blob)

**New Structure:**
These are likely stored in the metadata JSON field from the common `BaseModel`, or in separate related models for comments, objectives, etc.

## Migration Considerations

When migrating from WC2 to the new schema:

1. **Data Mapping:** Each old field needs to be mapped to its new location in JSON objects or related models.

2. **Normalization:** Address and contact information should be extracted into separate normalized tables.

3. **Calculations:** Financial totals that were stored as static fields are now computed dynamically and cached in JSON fields.

4. **Flexibility:** The JSON structure allows for future extensions without database schema changes.

## Benefits of New Structure

- **Scalability:** JSON fields can accommodate varying data structures
- **Performance:** Cached totals reduce computation overhead
- **Maintainability:** Related data is properly normalized
- **Extensibility:** Easy to add new fields without migrations