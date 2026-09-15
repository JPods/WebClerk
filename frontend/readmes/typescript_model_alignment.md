# TypeScript Model Alignment Guide

This guide explains the WC3 ↔ R25 TypeScript alignment strategy for model interfaces in this project.

## Structure
- Each TypeScript interface is located in the corresponding `models` folder, mirroring the backend apps structure.
- File naming follows the convention: `ModelName.ts` (e.g., `Action.ts`, `Contact.ts`).
- Interfaces strictly match canonical WC3 field names and types for full schema alignment.

## Benefits
- Ensures strict schema consistency between backend and frontend.
- Simplifies maintenance and future updates.
- Enables type-safe React components and mappers.
- Promotes code reuse and clarity.

## Example
- `/src/apps/core/models/action/Action.ts`
- `/src/apps/core/models/contact/Contact.ts`
- `/src/apps/transactions/models/project/Project.ts`
- `/src/apps/products/models/item/Item.ts`
- `/src/apps/docs/models/document/Document.ts`

## Next Steps
- Update all React props, mappers, and API integrations to use these interfaces.
- Regenerate interfaces whenever backend model fields change.

For questions or updates, see the WC3 ↔ R25 Field Alignment Guide or contact the project maintainers.
