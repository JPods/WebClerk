# Customer Dashboard Design

This dashboard provides a comprehensive interface for managing customer records, including both scalar and nested (dotted) data, and a suite of containers for related business objects and actions.

## Features

### 2.1. Scalar and Dotted Object Data
- Display all scalar fields (e.g., name, id, status) and nested objects (e.g., customer.address.city).

### 2.2. Contact Information Container
- Add and edit contact information:
  - Email addresses
  - Phone numbers
  - Domains
  - Physical addresses

### 2.3. Related Business Objects
- View and access:
  - Proposals
  - Orders
  - Invoices
  - Payments
  - Ledgers
  - Projects

### 2.4. Comments Container
- View and add comments related to the customer.

### 2.5. Preferences Container
- View and edit customer `.prefs` values.

### 2.6. Actions Container
- View and edit actions associated with the customer.

### 2.7. Linkage Container
- View and edit linkage records (relationships to other entities).

### 2.8. Document Container
- View and edit documents associated with the customer.

### 2.9. Question & Answer Container
- View and edit question/answer records for the customer.

### 2.10. Tag Container
- View and edit tags assigned to the customer.

### 2.11. Products/Serials Container
- View and edit products or serials sold to this customer.

### 2.12. Relationship Container
- View and edit relationships to:
  - Vendor
  - Manufacturer
  - Rep
  - Employee records

### 2.13. Catalogs Container
- View and edit catalogs associated with the customer.

### 2.14. Campaigns Container
- View and edit campaign records associated with the customer.

---

## Implementation Notes
- Each container should be a modular React component.
- Containers should support CRUD operations where applicable.
- Use tabs or an accordion UI for navigation between containers.
- Ensure all data is fetched and updated via API integration.
- Provide clear error handling and loading states for each container.
