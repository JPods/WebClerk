# Frontend Dropdowns System

## Overview

The Frontend Dropdowns system provides centralized management of dropdown selection lists for React frontend components. It supports both hardcoded defaults and database-driven configuration through Setting records.

## Architecture

### Components

1. **FrontendDropdownsService** (`apps/core/services/frontend_dropdowns.py`)
   - Core service for generating dropdown options
   - Caching layer for performance
   - Fallback to hardcoded defaults

2. **API View** (`apps/core/views/dropdowns.py`)
   - REST endpoint for frontend consumption
   - Authentication required
   - Supports both full and individual dropdown retrieval

3. **Migration Command** (`apps/core/management/commands/migrate_frontend_dropdowns.py`)
   - Moves hardcoded dropdowns to Setting records
   - Supports dry-run and force options

## Current Dropdowns

### assigned_to_ddl

- **Purpose**: User assignment dropdown for actions/tasks
- **Format**: `[{"label": "Full Name", "value": contact_id}, ...]`
- **Source**: Active Contact records, ordered by last name, first name
- **Dynamic**: Always queries database (not cached in settings)

### difficulty_ddl

- **Purpose**: Task difficulty levels
- **Format**: `["1", "5", "25", "50", "101"]`
- **Configurable**: Can be overridden via Setting records

### priority_ddl

- **Purpose**: Task priority levels
- **Format**: `["UKN", "Low", "Medium", "High", "Immediate"]`
- **Configurable**: Can be overridden via Setting records

## API Endpoints

### GET /dropdowns/

Returns all frontend dropdowns.

**Response:**

```json
{
  "assigned_to_ddl": [
    {"label": "John Doe", "value": 1},
    {"label": "Jane Smith", "value": 2}
  ],
  "difficulty_ddl": ["1", "5", "25", "50", "101"],
  "priority_ddl": ["UKN", "Low", "Medium", "High", "Immediate"]
}
```

### GET /dropdowns/?name=dropdown_name

Returns a specific dropdown.

**Example:** `/dropdowns/?name=priority_ddl`

**Response:**

```json
["UKN", "Low", "Medium", "High", "Immediate"]
```

## Configuration via Settings

Once migrated, dropdowns are stored as Setting records with:

- **purpose**: `"front_end-ddl"`
- **name**: `"frontend-dropdown-{dropdown_name}"`
- **data**: The dropdown options array/object

### Example Setting Record

```json
{
  "name": "frontend-dropdown-priority_ddl",
  "purpose": "front_end-ddl",
  "data": ["UKN", "Low", "Medium", "High", "Immediate", "Critical"],
  "is_active": true
}
```

## Migration Process

### Step 1: Preview Migration

```bash
python manage.py migrate_frontend_dropdowns --dry-run
```

### Step 2: Execute Migration

```bash
python manage.py migrate_frontend_dropdowns
```

### Step 3: Verify

Check that Setting records exist with purpose="front_end-ddl"

### Step 4: Update Frontend

Frontend will automatically use the new settings-based dropdowns

## Usage in React Frontend

```javascript
// Fetch all dropdowns
const response = await fetch('/dropdowns/', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
const dropdowns = await response.json();

// Use in component
<select>
  {dropdowns.priority_ddl.map(priority => (
    <option key={priority} value={priority}>{priority}</option>
  ))}
</select>
```

## Adding New Dropdowns

1. **Add hardcoded default** in `FrontendDropdownsService.DEFAULT_DROPDOWNS`
2. **Add getter method** following the pattern of existing methods
3. **Update get_all_dropdowns()** to include the new dropdown
4. **Run migration** to create Setting record
5. **Update frontend** to consume the new dropdown

## Cache Management

- Dropdowns are cached for 1 hour to improve performance
- Cache is automatically invalidated when settings change
- `assigned_to_ddl` is always fresh (not cached in settings)

## Security

- All endpoints require authentication
- Dropdown data is read-only for frontend consumption
- Settings can be modified through Django admin (staff access required)

## Future Enhancements

- Role-based dropdown filtering
- Dynamic dropdowns based on user context
- Validation of dropdown values on form submission
- Audit logging of dropdown changes
