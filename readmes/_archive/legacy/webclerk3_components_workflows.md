# WebClerk3 Components & Workflows

## Core Components Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        C1[Web Frontend]
        C2[Mobile Apps]
        C3[API Clients]
        C4[Third-party Integrations]
    end

    subgraph "API Gateway Layer"
        A1[Django REST Framework]
        A2[Universal API Router]
        A3[Authentication Middleware]
        A4[Rate Limiting]
        A5[Write Gate Middleware]
        A6[Request Logging]
    end

    subgraph "Business Logic Layer"
        B1[Universal Save View]
        B2[WCAPI Query View]
        B3[Transaction Views]
        B4[Product Views]
        B5[Communication Views]
        B6[Sync Views]
    end

    subgraph "Service Layer"
        S1[WCAPI Registry]
        S2[Permission Service]
        S3[Keyword Service]
        S4[Transaction Services]
        S5[Inventory Services]
        S6[Sync Services]
        S7[Verification Services]
    end

    subgraph "Data Access Layer"
        D1[BaseModel System]
        D2[Query Managers]
        D3[Atomic Operations]
        D4[Search Vectors]
        D5[JSON Field Operations]
    end

    subgraph "Infrastructure Layer"
        I1[PostgreSQL Database]
        I2[Redis Cache/Broker]
        I3[Celery Workers]
        I4[File Storage]
        I5[Email Service]
    end

    C1 --> A1
    C2 --> A1
    C3 --> A1
    C4 --> A1

    A1 --> A2
    A2 --> A3
    A3 --> A4
    A4 --> A5
    A5 --> A6

    A2 --> B1
    A2 --> B2
    A2 --> B3
    A2 --> B4
    A2 --> B5
    A2 --> B6

    B1 --> S1
    B2 --> S1
    B3 --> S4
    B4 --> S5
    B5 --> S7
    B6 --> S6

    S1 --> D1
    S4 --> D1
    S5 --> D1
    S7 --> D1
    S6 --> D1

    D1 --> I1
    D2 --> I1
    D3 --> I1
    D4 --> I1
    D5 --> I1

    S3 --> I3
    I3 --> I2
    I3 --> I5
```

## Universal API Component Details

### WCAPI Registry (`apps/core/services/wcapi_registry.py`)
```python
# Key responsibilities:
# - Model allow-list management
# - Key normalization (plural -> singular)
# - Model resolution by string key
# - Registry introspection

MODEL_MAP = {
    'contact': Contact,
    'action': Action,
    'email': Email,
    'phone': Phone,
    'location': Location,
    'document': Document,
    # ... transaction models
    'proposal': Proposal,
    'order': Order,
    'invoice': Invoice,
    # ... etc
}
```

### Save View (`apps/core/views/save_view.py`)
**Responsibilities:**
- JSON payload parsing and validation
- Model resolution via registry
- Field size enforcement
- Deep merge of JSON fields (refs, prefs, metadata)
- Optimistic concurrency with version checking
- Pre/post save hooks
- Async task dispatching (keywords, sync)

**Key Features:**
- Supports both create and update operations
- Unknown fields captured in `prefs.userdefined`
- Password hashing for user models
- Comprehensive error handling with structured responses

### Query View (`apps/core/views/wcapi.py`)
**Responsibilities:**
- Safe filtering with allow-list
- Field projection
- Pagination
- Sorting
- Strict mode for unknown filters

**Safe Filter Fields:**
```python
SAFE_FILTER_FIELDS = {
    'email', 'name_first', 'name_last', 'company',
    'action', 'status', 'contact_id', 'created_by_id'
}
```

## Transaction System Components

### Transaction Base Classes
```mermaid
classDiagram
    class TransactionBaseModel {
        +BaseModel
        +contact_id: IntegerField
        +status: CharField
        +currency: CharField
        +totals: JSONField
        +due_date: DateTimeField
        +compute_totals()*
        +validate_flow()*
    }

    class TransactionLineBaseModel {
        +BaseModel
        +parent_id: IntegerField
        +item_id: IntegerField
        +quantity: DecimalField
        +price_unit: DecimalField
        +cost_unit: DecimalField
        +status: CharField
        +inherit_from_parent()*
        +update_lineage()*
    }

    TransactionBaseModel ||--o{ TransactionLineBaseModel : contains
```

### Transaction Flow Engine
**Key Components:**
- **Flow Conversion Services** (`apps/transactions/services/`)
  - `order_to_invoice.py`: Order → Invoice conversion
  - `purchase_to_order.py`: Purchase Requisition → Purchase Order
  - `transfer_utils.py`: Cross-document data transfer

- **Aggregation Services**
  - `invoice_totals.py`: Invoice sell/cost calculations
  - `po_totals.py`: Purchase order totals
  - `wo_totals.py`: Work order totals

- **Validation Services**
  - Flow state validation
  - Business rule enforcement
  - Lineage consistency checks

### Transaction Workflow States
```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Submitted : submit()
    Submitted --> Approved : approve()
    Submitted --> Rejected : reject()
    Rejected --> Draft : revise()
    Approved --> InProgress : start_work()
    InProgress --> Completed : complete()
    InProgress --> Cancelled : cancel()
    Completed --> [*]
    Cancelled --> [*]

    note right of Submitted
        Status transitions
        vary by document type
    end note
```

## Inventory Management Components

### Inventory Layer System
```mermaid
classDiagram
    class InventoryLayer {
        +CoreModel
        +item_id: IntegerField
        +location_id: IntegerField
        +quantity: DecimalField
        +cost_avg: DecimalField
        +reservations: JSONField
        +adjust_quantity()*
        +reserve_quantity()*
        +release_reservation()*
    }

    class InventoryReservation {
        +CoreModel
        +inventory_layer_id: IntegerField
        +contact_id: IntegerField
        +quantity: DecimalField
        +purpose: CharField
        +expires_at: DateTimeField
        +fulfill()*
        +expire()*
    }

    InventoryLayer ||--o{ InventoryReservation : has
```

### Reservation Workflow
```mermaid
flowchart TD
    A[Create Reservation] --> B{Check Available Qty}
    B -->|Insufficient| C[Reservation Failed]
    B -->|Available| D[Reserve Quantity]
    D --> E[Set Expiration Timer]
    E --> F{Expires or Fulfilled?}
    F -->|Expires| G[Auto Release]
    F -->|Fulfilled| H[Mark Complete]
    G --> I[Quantity Available]
    H --> I
```

## Synchronization Components

### Connection Framework
```mermaid
classDiagram
    class Connection {
        +BaseModel
        +name: CharField
        +type: CharField
        +config: JSONField
        +status: CharField
        +maps: JSONField
        +rules: JSONField
        +test_connection()*
        +sync_data()*
        +handle_conflicts()*
    }

    class SyncService {
        +authenticate()*
        +fetch_data()*
        +transform_data()*
        +push_changes()*
        +resolve_conflicts()*
    }

    Connection --> SyncService : uses
```

### Sync Workflow
```mermaid
flowchart TD
    A[Trigger Sync] --> B[Authenticate]
    B --> C{Fetch Remote Data}
    C --> D[Transform Data]
    D --> E{Check Conflicts}
    E -->|No Conflicts| F[Apply Changes]
    E -->|Conflicts| G[Resolve via Rules]
    G --> F
    F --> H[Update Local Records]
    H --> I[Log Sync Event]
    I --> J[Notify Stakeholders]
```

## Communication Components

### Verification System
```mermaid
flowchart TD
    A[Request Verification] --> B{Type?}
    B -->|Email| C[Send Email Code]
    B -->|Phone| D[Send SMS Code]
    B -->|Domain| E[DNS Check]
    B -->|Location| F[Address Validation]

    C --> G[User Enters Code]
    D --> G
    E --> H[Auto Verify]
    F --> I[Manual Review]

    G --> J{Valid Code?}
    J -->|Yes| K[Mark Verified]
    J -->|No| L[Increment Attempts]
    L --> M{Max Attempts?}
    M -->|No| G
    M -->|Yes| N[Lock Account]

    H --> K
    I --> K
    K --> O[Update Status]
```

## Key Workflows

### 1. Universal CRUD Workflow
```mermaid
flowchart TD
    A[Client Request] --> B{HTTP Method}
    B -->|GET| C[Query/List Operation]
    B -->|POST| D[Create Operation]
    B -->|PATCH| E[Update Operation]
    B -->|DELETE| F[Delete Operation]

    C --> G[Parse Query Params]
    D --> H[Parse JSON Body]
    E --> H
    F --> I[Parse URL Params]

    G --> J[Apply Filters/Sorting]
    H --> K[Validate Payload]
    I --> L[Check Permissions]

    J --> M[Execute Query]
    K --> N[Resolve Model]
    L --> O[Check Ownership]

    M --> P[Serialize Results]
    N --> Q[Create/Update Record]
    O --> R[Soft Delete]

    P --> S[Return Envelope]
    Q --> S
    R --> S
```

### 2. Transaction Conversion Workflow
```mermaid
flowchart TD
    A[Source Document] --> B[Validate State]
    B --> C{Can Convert?}
    C -->|No| D[Return Error]
    C -->|Yes| E[Create Target Document]

    E --> F[Copy Header Fields]
    F --> G[Process Line Items]
    G --> H[Update Lineage]
    H --> I[Calculate Totals]

    I --> J[Set Status]
    J --> K[Create Action Records]
    K --> L[Trigger Notifications]

    L --> M[Update Source Status]
    M --> N[Log Conversion Event]
    N --> O[Return Success]
```

### 3. Keyword Refresh Pipeline
```mermaid
flowchart TD
    A[Model Save] --> B[Mark Keywords Dirty]
    B --> C[Defer to Background]

    C --> D[Celery Task: refresh_keywords]
    D --> E[Query Dirty Records]
    E --> F[Extract Text Fields]

    F --> G[Generate Keywords]
    G --> H[Update refs.keywords]
    H --> I[Clear Dirty Flag]

    I --> J[Rebuild Search Index]
    J --> K[Log Completion]
```

### 4. Permission Resolution Workflow
```mermaid
flowchart TD
    A[API Request] --> B[Extract User/Role]
    B --> C[Identify Model]
    C --> D[Query Settings Table]

    D --> E{Found Matrix?}
    E -->|Yes| F[Load Permission Rules]
    E -->|No| G[Use Defaults]

    F --> H[Check Field Permissions]
    G --> I[Apply Default Rules]

    H --> J{Allowed?}
    I --> J

    J -->|Yes| K[Proceed with Operation]
    J -->|No| L[Return 403 Forbidden]
```

## Service Layer Components

### Core Services
- **WCAPI Registry**: Model discovery and allow-listing
- **Permission Service**: Field-level access control
- **Keyword Service**: Text extraction and indexing
- **Validation Service**: Business rule enforcement

### Domain Services
- **Transaction Services**: Flow conversions, totals calculation
- **Inventory Services**: Quantity tracking, reservations
- **Communication Services**: Verification, notifications
- **Sync Services**: External system integration

### Infrastructure Services
- **Cache Service**: Redis operations for performance
- **Queue Service**: Celery task management
- **Storage Service**: File upload/download handling
- **Notification Service**: Email/SMS delivery

## Error Handling & Resilience

### Error Response Envelope
```json
{
  "status": "error",
  "error": {
    "code": "validation_error",
    "details": "Field validation failed",
    "field_errors": {
      "email": ["Invalid format"],
      "quantity": ["Must be positive"]
    }
  },
  "meta": {
    "request_id": "abc-123",
    "timestamp": 1730937600000
  }
}
```

### Circuit Breaker Pattern
- Automatic failure detection for external services
- Graceful degradation when dependencies unavailable
- Retry logic with exponential backoff
- Fallback responses for critical operations

### Monitoring & Observability
- Structured logging with correlation IDs
- Metrics collection (request counts, durations, errors)
- Health checks for all major components
- Alerting on service degradation

This component and workflow documentation provides a detailed view of WebClerk3's architecture, showing how the various pieces work together to deliver a cohesive business application platform.