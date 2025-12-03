# Workorder Model

This model represents workorders in the transaction system.

## Fields

- `id`: Unique identifier (readonly)
- `workorder_no`: Workorder number (required)
- `dt_created`: Creation timestamp (readonly)

## API Endpoints

- `GET /tx/workorders/` - List workorders
- `POST /tx/workorders/` - Create workorder
- `GET /tx/workorders/{id}/` - Get workorder details
- `PUT /tx/workorders/{id}/` - Update workorder
- `DELETE /tx/workorders/{id}/` - Delete workorder

## Usage

```typescript
import { fetchWorkorders, createWorkorder } from './services/workorderApi';

// Fetch all workorders
const workorders = await fetchWorkorders();

// Create new workorder
const newWorkorder = await createWorkorder({ workorder_no: 'WO-001' });