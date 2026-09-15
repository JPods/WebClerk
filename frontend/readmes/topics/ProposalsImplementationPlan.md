# Proposals Implementation Plan

## Overview

This document outlines the plan to fully implement proposals functionality in both the React frontend (React2025) and the Django backend (WebClerk3). The backend already has a comprehensive proposal model with lines, serializers, and views, but the frontend currently only supports basic proposal creation with minimal fields.

## Current State Analysis

### Backend (WebClerk3)
- **Model**: `Proposal` inherits from `TransactionBaseModel`
- **Fields**: id, uuid, ida, status, id_customer, id_vendor, cost, sell, finance, flow, source, action, dt_created, dt_modified, version
- **Lines**: `ProposalLine` model with comprehensive JSON fields (item, quantity, price, cost, tax, physical, etc.)
- **Serializer**: `ProposalSerializer` with all fields
- **Views**: CRUD operations + actions (convert to sales order)
- **URLs**: `/tx/proposals/` endpoints

### Frontend (React2025)
- **Basic Structure**: Exists in `src/apps/transactions/models/proposal/`
- **Pages**: `ProposalList.tsx`, `ProposalDetail.tsx`
- **Types**: Minimal - only `proposal_no` field
- **API**: Basic CRUD using `tx_proposals` endpoint
- **Missing**: Full field support, proposal lines, actions

## Implementation Plan

### Phase 1: Backend Verification and Enhancement
1. **Verify Backend Completeness**
   - Ensure all proposal endpoints are properly configured
   - Test proposal CRUD operations
   - Verify proposal-to-sales-order conversion functionality
   - Check proposal line handling

2. **Add Missing Backend Features** (if needed)
   - Ensure proposal line serializers exist
   - Add any missing API endpoints
   - Verify database migrations are applied

### Phase 2: Frontend Type System Update
1. **Update Proposal Types**
   - Expand `proposalType.ts` to include all backend fields
   - Add proper TypeScript interfaces for proposal data
   - Include proposal line types

2. **Add Proposal Line Types**
   - Create `proposalLineType.ts` with line item interfaces
   - Define types for item, quantity, price, cost, tax, physical fields

### Phase 3: Frontend API Layer Enhancement
1. **Update API Services**
   - Modify `proposalApi.ts` to handle full proposal objects
   - Add proposal line CRUD operations
   - Add action endpoints (convert to sales order)

2. **Add Proposal Line API**
   - Create `proposalLineApi.ts` for line item operations
   - Implement nested resource handling

### Phase 4: Frontend Component Updates
1. **Update Proposal Forms**
   - Modify `ProposalDetail.tsx` to include all proposal fields
   - Add form validation using Zod schemas
   - Implement mode-based rendering (add/edit/view)

2. **Add Proposal Line Management**
   - Create `ProposalLineList.tsx` component
   - Add `ProposalLineDetail.tsx` for line item editing
   - Implement inline editing capabilities

3. **Enhance Proposal List**
   - Update `ProposalList.tsx` to display relevant proposal fields
   - Add filtering and sorting capabilities
   - Include status indicators

### Phase 5: Business Logic Integration
1. **Add Proposal Actions**
   - Implement "Convert to Sales Order" functionality
   - Add status management
   - Include workflow transitions

2. **Form Validation**
   - Implement comprehensive validation schemas
   - Add business rule validation
   - Include cross-field validation

### Phase 6: Testing and Integration
1. **Unit Tests**
   - Test proposal components
   - Test API integrations
   - Test form validations

2. **Integration Tests**
   - Test full proposal workflows
   - Test proposal-to-sales-order conversion
   - Test line item management

3. **UI/UX Polish**
   - Ensure responsive design
   - Add loading states and error handling
   - Implement proper navigation and breadcrumbs

## Technical Considerations

### Data Structure Alignment
- Ensure frontend types exactly match backend serializer fields
- Handle JSON fields properly (cost, sell, finance, etc.)
- Implement proper date/time handling

### Performance
- Implement pagination for proposal lists
- Add lazy loading for proposal lines
- Optimize API calls with proper caching

### Security
- Ensure proper authentication for proposal operations
- Implement field-level permissions
- Add audit logging for sensitive operations

## Dependencies

### Frontend Dependencies
- React Hook Form + Zod (already in use)
- Existing UI components (DataTable, forms, etc.)
- Redux for state management

### Backend Dependencies
- Django REST Framework
- Existing transaction models and serializers
- Database migrations

## Success Criteria

1. **Full CRUD Operations**: Create, read, update, delete proposals with all fields
2. **Line Item Management**: Add, edit, delete proposal line items
3. **Workflow Integration**: Convert proposals to sales orders
4. **Data Integrity**: All frontend data matches backend schema
5. **User Experience**: Intuitive forms and workflows
6. **Performance**: Fast loading and responsive interactions

## Timeline Estimate

- Phase 1: 1-2 days (backend verification)
- Phase 2: 1 day (type updates)
- Phase 3: 2 days (API enhancements)
- Phase 4: 3-4 days (component updates)
- Phase 5: 2 days (business logic)
- Phase 6: 2-3 days (testing and polish)

Total: 11-15 days for complete implementation.

## Risk Assessment

### High Risk
- Complex JSON field handling in frontend
- Proposal-to-sales-order conversion logic
- Line item bulk operations

### Mitigation
- Thorough testing of JSON serialization/deserialization
- Step-by-step implementation of conversion logic
- Incremental addition of line item features

## Next Steps

1. Begin with Phase 1: Backend verification
2. Update this plan as implementation progresses
3. Create detailed task breakdown for each phase
4. Assign responsibilities and timelines