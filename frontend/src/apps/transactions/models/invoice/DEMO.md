# Invoice Model

This model represents invoices in the transaction system.

## Fields

- `id`: Unique identifier (readonly)
- `invoice_no`: Invoice number (required)
- `dt_created`: Creation timestamp (readonly)

## API Endpoints

- `GET /tx/invoices/` - List invoices
- `POST /tx/invoices/` - Create invoice
- `GET /tx/invoices/{id}/` - Get invoice details
- `PUT /tx/invoices/{id}/` - Update invoice
- `DELETE /tx/invoices/{id}/` - Delete invoice

## Usage

```typescript
import { fetchInvoices, createInvoice } from './services/invoiceApi';

// Fetch all invoices
const invoices = await fetchInvoices();

// Create new invoice
const newInvoice = await createInvoice({ invoice_no: 'INV-001' });
