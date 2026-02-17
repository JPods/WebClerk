# Purchase Model

This model represents purchases in the transaction system.

## Fields

- `id`: Unique identifier (readonly)
- `purchase_no`: Purchase number (required)
- `dt_created`: Creation timestamp (readonly)

## API Endpoints

- `GET /tx/purchase/` - List purchases
- `POST /tx/purchase/` - Create purchase
- `GET /tx/purchase/{id}/` - Get purchase details
- `PUT /tx/purchase/{id}/` - Update purchase
- `DELETE /tx/purchase/{id}/` - Delete purchase

## Usage

```typescript
import { fetchPurchases, createPurchase } from './services/purchaseApi';

// Fetch all purchases
const purchases = await fetchPurchases();

// Create new purchase
const newPurchase = await createPurchase({ purchase_no: 'PO-001' });
