# Quote Model

This model represents quotes in the transaction system.

## Fields

- `id`: Unique identifier (readonly)
- `quote_no`: Quote number (required)
- `dt_created`: Creation timestamp (readonly)

## API Endpoints

- `GET /tx/quotes/` - List quotes
- `POST /tx/quotes/` - Create quote
- `GET /tx/quotes/{id}/` - Get quote details
- `PUT /tx/quotes/{id}/` - Update quote
- `DELETE /tx/quotes/{id}/` - Delete quote

## Usage

```typescript
import { fetchQuotes, createQuote } from './services/quoteApi';

// Fetch all quotes
const quotes = await fetchQuotes();

// Create new quote
const newQuote = await createQuote({ quote_no: 'PROP-001' });
