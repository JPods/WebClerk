# Model name conventions


<!-- TOC START -->

## Table of Contents

- [Model name conventions](#model-name-conventions)
  - [Static files note](#static-files-note)

<!-- TOC END -->

- Only model_name is used; table_name is deprecated.
- Acceptable inputs when creating a Setting:
  - Canonical key from table registry (e.g., sales_order_lines, proposal_line)
  - Endpoint slug (e.g., sales-order-lines)
  - Singular code (e.g., sales_order_line, proposal_line)
- The system normalizes and stores the singular form (e.g., sales_order_line).
- Permissions: ViewEditPermission resolves the model_name from the queryset’s model db_table.

Endpoints to model_name mapping (examples)

- /tx/proposal-lines/ -> proposal_line
- /tx/sales-order-lines/ -> sales_order_lines -> stored as sales_order_line
- /tx/invoice-lines/ -> invoice_line
- /tx/purchase-order-lines/ -> purchase_order_lines -> stored as purchase_order_line
- /tx/workorder-lines/ -> work_order_lines -> stored as work_order_line
- /tx/requisition-lines/ -> requisition_line

## Static files note

If you see a STATICFILES_DIRS warning referencing core/static, either create the folder or remove it from settings if unused.
