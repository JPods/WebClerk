# Order Model

This model represents orders in the transaction system.

## Fields

- `id`: Unique identifier (readonly)
- `order_no`: Order number (required)
- `dt_created`: Creation timestamp (readonly)

## API Endpoints

- `GET /tx/orders/` - List orders
- `POST /tx/orders/` - Create order
- `GET /tx/orders/{id}/` - Get order details
- `PUT /tx/orders/{id}/` - Update order
- `DELETE /tx/orders/{id}/` - Delete order

## Usage

```typescript
import { fetchOrders, createOrder } from './services/orderApi';

// Fetch all orders
const orders = await fetchOrders();

// Create new order
const newOrder = await createOrder({ order_no: 'SO-001' });
