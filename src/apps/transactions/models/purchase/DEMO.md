# Purchase Order Model

This model represents purchase orders in the transaction system.

## Fields

- `id`: Unique identifier (readonly)
- `purchase_no`: Purchase order number (required)
- `dt_created`: Creation timestamp (readonly)

## API Endpoints

- `GET /tx/purchase-orders/` - List purchase orders
- `POST /tx/purchase-orders/` - Create purchase order
- `GET /tx/purchase-orders/{id}/` - Get purchase order details
- `PUT /tx/purchase-orders/{id}/` - Update purchase order
- `DELETE /tx/purchase-orders/{id}/` - Delete purchase order

## Usage

```typescript
import { fetchPurchases, createPurchase } from './services/purchaseOrderApi';

// Fetch all purchase orders
const purchaseOrders = await fetchPurchases();

// Create new purchase order
const newPurchase = await createPurchase({ purchase_no: 'PO-001' });
