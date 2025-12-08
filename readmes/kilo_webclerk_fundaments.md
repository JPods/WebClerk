# Kilo WebClerk Fundamentals

## Overview
WebClerk3 is a Django-based ERP/commerce backend system designed for business transaction management. It provides REST APIs for a React frontend (React2025) to manage proposals, orders, invoices, inventory, accounting, and organizational data.

## Core Architecture

### 1. Django REST Framework Foundation
- **Model-View-Controller Pattern**: Django models define data structure, views handle HTTP requests, serializers manage data transformation
- **DRF ViewSets**: Standardized CRUD operations for all major entities
- **Permission System**: Role-based access control with custom permission classes

### 2. Universal API Layer (WCAPI)
- **Generic Model Access**: `/wcapi/get/` endpoint can query any registered model
- **Query Parameters**: Support for filtering, pagination, field selection
- **Policy Injection**: Automatic permission and constraint application
- **Registry System**: Dynamic model registration for extensibility

### 3. Transaction Management Core
- **Base Transaction Model**: Abstract class with common fields (status, customer/vendor IDs, JSON fields for flexible data)
- **Line Item Pattern**: All transactions have related line items with `related_name="lines"`
- **State Management**: Status transitions with validation
- **Flow Tracking**: Source/destination tracking for transaction relationships

### 4. Key Transaction Types
- **Proposals**: Sales proposals with line items, status workflow (planned→sent→accepted/rejected)
- **Sales Orders**: Customer orders with inventory allocation
- **Purchase Orders**: Vendor orders for procurement
- **Invoices**: Billing documents with payment tracking
- **Payments**: Payment processing with gateway integration

### 5. Product & Inventory System
- **Item Catalog**: Products with variants, specifications, BOMs
- **Inventory Tracking**: Layer-based inventory with reservations
- **Warehouse Management**: Multi-location inventory control
- **Service Billing**: Time-based service tracking

### 6. Accounting Integration
- **General Ledger**: Double-entry accounting with journals
- **Currency Handling**: Multi-currency support with exchange rates
- **Tax Management**: Jurisdiction-based tax calculations
- **Terms & Payment**: Configurable payment terms

### 7. Organization & User Management
- **Multi-tenant**: Organization-based data isolation
- **Contact System**: Unified customer/vendor/contact management
- **User Permissions**: Granular permission system
- **Audit Trail**: Comprehensive change tracking

## Data Flow Patterns

### 1. Transaction Creation
1. WCAPI save or REST API creates header record
2. Lines created separately or via nested serializer
3. Status validation and workflow enforcement
4. Related records updated (inventory, accounting)

### 2. Query Optimization
- `prefetch_related()` for line items to prevent N+1 queries
- `select_related()` for foreign key optimization
- JSON fields for flexible, indexed data storage

### 3. Serialization Strategy
- **Nested Serializers**: Include related data in API responses
- **Read-only Fields**: Computed fields for frontend consumption
- **Validation**: Cross-field and status transition validation

## React2025 Integration Points

### 1. API Consumption
- REST endpoints for CRUD operations
- WCAPI for dynamic queries and reporting
- Real-time updates via WebSockets (planned)

### 2. Data Synchronization
- Optimistic locking with version fields
- Change detection and conflict resolution
- Bulk operations for efficiency

### 3. State Management
- Transaction state machines
- Inventory level tracking
- User permission context

## Development Patterns

### 1. Model Design
- Abstract base classes for common functionality
- JSON fields for extensible data
- Custom managers for complex queries

### 2. Service Layer
- Business logic separated from views
- Reusable services for common operations
- Transaction wrapping for data integrity

### 3. Testing Strategy
- Unit tests for models and services
- Integration tests for API endpoints
- Factory pattern for test data creation

## Key Design Principles

### 1. Flexibility
- JSON fields allow schema evolution without migrations
- Registry system enables plugin-like extensions
- Generic APIs reduce boilerplate code

### 2. Performance
- Prefetching and select_related for query optimization
- Pagination and field selection for large datasets
- Background processing for heavy operations

### 3. Security
- Permission injection at query level
- Field-level access control
- Audit logging for compliance

### 4. Maintainability
- Clear separation of concerns
- Comprehensive documentation
- Automated testing

## Future Considerations

### 1. Scaling
- Database optimization for high transaction volumes
- Caching strategies for frequently accessed data
- Microservice decomposition if needed

### 2. Integration
- Third-party ERP system connections
- E-commerce platform integrations
- API rate limiting and monitoring

### 3. User Experience
- Real-time notifications
- Advanced search and filtering
- Mobile-responsive design

## Team Collaboration

### 1. Code Organization
- Feature-based app structure
- Shared utilities in `core` app
- Clear naming conventions

### 2. Documentation
- README files for major features
- API documentation via DRF
- Code comments for complex logic

### 3. Development Workflow
- Git-based version control
- Code review requirements
- Automated testing in CI/CD

This foundation provides a solid base for building comprehensive business management software with room for growth and customization.