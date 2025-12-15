# Proposal Model

This model represents proposals in the transaction system.

## Fields

- `id`: Unique identifier (readonly)
- `proposal_no`: Proposal number (required)
- `dt_created`: Creation timestamp (readonly)

## API Endpoints

- `GET /tx/proposals/` - List proposals
- `POST /tx/proposals/` - Create proposal
- `GET /tx/proposals/{id}/` - Get proposal details
- `PUT /tx/proposals/{id}/` - Update proposal
- `DELETE /tx/proposals/{id}/` - Delete proposal

## Usage

```typescript
import { fetchProposals, createProposal } from './services/proposalApi';

// Fetch all proposals
const proposals = await fetchProposals();

// Create new proposal
const newProposal = await createProposal({ proposal_no: 'PROP-001' });
