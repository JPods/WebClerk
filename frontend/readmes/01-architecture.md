# CommerceExpert React2025 - Architecture Guide

## 📁 Project Structure

This document outlines the established architecture and file organization conventions for the CommerceExpert React2025 application.

## 🏗️ Core Architecture Principles

### Domain-Driven Design
- **Business domains** are organized into separate apps
- **Related functionality** is co-located within each domain
- **Clear separation** between different business concerns

### File Organization
```
src/
├── apps/                    # Business domain applications
│   └── {app}/
│       └── models/
│           └── {model}/
│               ├── pages/      # UI components (Detail, List, etc.)
│               ├── services/   # API integration
│               ├── types/      # TypeScript type definitions
│               ├── utils/      # Utilities and schemas
│               └── index.ts    # Model exports
├── pages/                   # General/shared pages
│   ├── Dashboard/
│   ├── UserProfile/
│   └── ...
├── components/              # Shared UI components
├── routes/                  # Routing configuration
└── ...
```

## 📂 Apps Structure

### Current Apps
- **`core`** - Core business entities (customers, contacts, settings)
- **`transactions`** - Transaction management (orders, invoices, proposals)
- **`products`** - Product/item management
- **`docs`** - Documentation system
- **`accounts`** - Accounting (GL, journals, etc.)
- **`communications`** - Email, phone, domain management

### App Organization
```
apps/{app}/
├── models/
│   └── {model}/
│       ├── pages/           # React components
│       │   ├── {Model}Detail.tsx
│       │   ├── {Model}List.tsx
│       │   └── {Model}Display.tsx (optional)
│       ├── services/
│       │   └── {model}Api.ts
│       ├── types/
│       │   └── {model}Type.ts
│       ├── utils/
│       │   └── {model}Schema.ts
│       └── index.ts
├── components/              # App-specific components
├── constants/
├── hooks/
├── services/
├── types/
└── utils/
```

## 🧩 Component Naming Conventions

### Page Components
- **Detail Components**: `{Model}Detail.tsx` - Add/edit/view forms
- **List Components**: `{Model}List.tsx` - Data tables with CRUD actions
- **Display Components**: `{Model}Display.tsx` - Read-only views
- **Index Components**: `{Model}Index.tsx` - Overview/dashboard pages

### Examples
```
apps/core/models/customer/pages/
├── CustomerDetail.tsx      # Add/edit customer form
└── CustomerList.tsx        # Customer management table

apps/transactions/models/order/pages/
├── OrderDetail.tsx         # Order form
├── OrderList.tsx           # Order management
└── OrderDisplay.tsx        # Order details view
```

### Container Components
- Live close to the feature they coordinate (for example `apps/{app}/models/{model}/containers/` or `src/features/{domain}/SomeContainer.tsx`) so multiple entry points can reuse them.
- Keep routing layers thin: pages import the container and forward props; containers own fetching, state, and orchestration concerns.
- Avoid piling every container into `{model}/pages/`; reserve that folder for route-driven page shells only.
- When sharing a container between frameworks (Vite SPA and Next.js), expose it through the feature index and let each runtime supply its own page wrapper.

## 🔗 API Integration

### Service Files
- Located in `apps/{app}/models/{model}/services/`
- Named `{model}Api.ts`
- Export functions: `fetch{model}s`, `create{model}`, `update{model}`, `delete{model}`

### Model Name Mapping
API endpoints use specific model names (may differ from directory names):
- `order` (not `salesOrder`)
- `purchase` (not `purchaseOrder`)
- `work_order` (not `workOrder`)

## 🎨 UI Patterns

### Form Components
- Use `react-hook-form` with Zod validation
- Schema files in `utils/{model}Schema.ts`
- Support multiple modes: `add`, `edit`, `view`
- Consistent error handling and validation

### List Components
- Use `react-data-table-component`
- Include action buttons (View, Edit, Delete)
- Support inline detail views
- Consistent styling and theming

### Routing
- Routes defined in `src/routes/Routes.ts`
- Components imported in `src/routes/Router.tsx`
- URL patterns: `/{domain}/{model}` or `/{domain}/{model}/:id`

## 📋 Development Guidelines

### Adding New Models
1. Create directory: `src/apps/{app}/models/{model}/`
2. Add subdirectories: `pages/`, `services/`, `types/`, `utils/`
3. Create components following naming conventions
4. Add API service functions
5. Define Zod schemas for validation
6. Update routing in `Routes.ts` and `Router.tsx`

### File Import Paths
- Use relative imports within apps
- Components import from `../../../../../../components/`
- Services import from `../services/{model}Api`

### Code Quality
- TypeScript strict mode enabled
- Zod schemas for runtime validation
- Consistent error handling patterns
- React Hook Form for form management

## 🚀 Benefits

- **Domain Isolation**: Business logic stays within its domain
- **Scalability**: Easy to add new models and apps
- **Maintainability**: Clear structure reduces cognitive load
- **Consistency**: Standardized patterns across all components
- **Developer Experience**: Predictable file locations and patterns

## 📝 Examples

### Adding a New Customer Model
```
src/apps/core/models/customer/
├── pages/
│   └── CustomerDetail.tsx
├── services/
│   └── customerApi.ts
├── types/
│   └── customerType.ts
├── utils/
│   └── customerSchema.ts
└── index.ts
```

### Component Structure
```tsx
// CustomerDetail.tsx
export default function CustomerDetail({
  modeProp,
  dataProp,
  onSaved
}: CustomerDetailProps) {
  // Form logic with react-hook-form + zod
}
```

This architecture ensures a clean, maintainable, and scalable codebase that follows domain-driven design principles.