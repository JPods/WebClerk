# Sales Order Model

This model represents sales orders in the transaction system.

## Fields

- `id`: Unique identifier (readonly)
- `sales_order_no`: Sales order number (required)
- `dt_created`: Creation timestamp (readonly)

## API Endpoints

- `GET /tx/sales-orders/` - List sales orders
- `POST /tx/sales-orders/` - Create sales order
- `GET /tx/sales-orders/{id}/` - Get sales order details
- `PUT /tx/sales-orders/{id}/` - Update sales order
- `DELETE /tx/sales-orders/{id}/` - Delete sales order

## Usage

```typescript
import { fetchSalesOrders, createSalesOrder } from './services/salesOrderApi';

// Fetch all sales orders
const salesOrders = await fetchSalesOrders();

// Create new sales order
const newSalesOrder = await createSalesOrder({ sales_order_no: 'SO-001' });
