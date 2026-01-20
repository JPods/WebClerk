# Purchase Order Model

This model represents purchase orders in the transaction system.

## Fields

- `id`: Unique identifier (readonly)
- `purchase_order_no`: Purchase order number (required)
- `dt_created`: Creation timestamp (readonly)

## API Endpoints

- `GET /tx/purchase-orders/` - List purchase orders
- `POST /tx/purchase-orders/` - Create purchase order
- `GET /tx/purchase-orders/{id}/` - Get purchase order details
- `PUT /tx/purchase-orders/{id}/` - Update purchase order
- `DELETE /tx/purchase-orders/{id}/` - Delete purchase order

## Usage

```typescript
import { fetchPurchaseOrders, createPurchaseOrder } from './services/purchaseOrderApi';

// Fetch all purchase orders
const purchaseOrders = await fetchPurchaseOrders();

// Create new purchase order
const newPurchaseOrder = await createPurchaseOrder({ purchase_order_no: 'PO-001' });
