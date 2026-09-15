# Model name conventions


<!-- TOC START -->

## Table of Contents

- [Model name conventions](#model-name-conventions)
  - [Table of Contents](#table-of-contents)
  - [Endpoints](#endpoints)
  - [Static files note](#static-files-note)

<!-- TOC END -->

- Only model_name is used; legacy aliases are not supported.
- Acceptable inputs when creating a Setting:
  - Canonical key from table registry (e.g., order_lines, proposal_line)
  - Endpoint slug (e.g., order-lines)
  - Singular code (e.g., order_line, proposal_line)
- The system normalizes and stores the singular form (e.g., order_line).
- Permissions: ViewEditPermission resolves the model_name from the queryset’s model db_table.

Endpoints to model_name mapping (examples)

- /tx/proposal-lines/ -> proposal_line
- /tx/order-lines/ -> order_lines -> stored as order_line
- /tx/invoice-lines/ -> invoice_line
- /tx/purchase-order-lines/ -> purchase_lines -> stored as purchase_line
- /tx/workorder-lines/ -> work_order_lines -> stored as workorder_line
- /tx/requisition-lines/ -> requisition_line

## Endpoints

- List available model_name values (singular codes):
  - GET `/wcapi/model_name/list/`
- Detail for a specific model_name (metadata + fields):
  - GET `/wcapi/model_name/detail/?model_name=order_line`

Examples:

```bash
curl -sS "http://localhost:8000/wcapi/model_name/detail/?model_name=purchase_line" \
  -H "Authorization: Bearer <token>" | jq
```

Example responses

- List

```json
{
  "ok": true,
  "data": {
    "model_names": ["invoice_line", "purchase_line", "order_line", "workorder_line"],
    "count": 4
  }
}
```

- Detail

```json
{
  "ok": true,
  "data": {
    "model": {
      "model_name": "purchase_line",
      "app_label": "transactions",
      "db_table": "purchase_lines",
      "endpoint": "/tx/purchase-order-lines/",
      "verbose_name": "Purchase order line",
      "fields": [
        {"name": "id", "type": "UUIDField", "required": true},
        {"name": "quantity", "type": "DecimalField", "required": true},
        {"name": "unit_price", "type": "DecimalField", "required": false}
      ]
    }
  }
}
```

## Static files note

If you see a STATICFILES_DIRS warning referencing core/static, either create the folder or remove it from settings if unused.
