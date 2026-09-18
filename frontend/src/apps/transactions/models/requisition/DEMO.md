# Requisition Model

This model represents requisitions in the transaction system.

## Fields

- `id`: Unique identifier (readonly)
- `requisition_no`: Requisition number (required)
- `dt_created`: Creation timestamp (readonly)

## API Endpoints

- `GET /tx/requisitions/` - List requisitions
- `POST /tx/requisitions/` - Create requisition
- `GET /tx/requisitions/{id}/` - Get requisition details
- `PUT /tx/requisitions/{id}/` - Update requisition
- `DELETE /tx/requisitions/{id}/` - Delete requisition

## Usage

```typescript
import { fetchRequisitions, createRequisition } from './services/requisitionApi';

// Fetch all requisitions
const requisitions = await fetchRequisitions();

// Create new requisition
const newRequisition = await createRequisition({ requisition_no: 'REQ-001' });
