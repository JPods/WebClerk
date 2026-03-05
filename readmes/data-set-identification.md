# Data Set Identification

This document describes the mechanism for identifying which data set (environment/database) the frontend is connected to and validating it matches the backend.

## Purpose

When working with multiple environments (LOCAL, DEV, STAGING, PRODUCTION), it's critical to know which data set the frontend and backend are communicating with. This prevents accidentally mixing data between environments.

## Quick Start: Switching Databases

### Option 1: Frontend Dev Tools Badge (Recommended)

Look for the color-coded badge in the **bottom-left corner** of the app:
- 🟢 **🌐 REMOTE** (Green) = Remote database (team collaboration)
- 🔵 **💻 LOCAL** (Blue) = Local database (debugging)

**To switch:**
1. Click the badge to expand the Dev Tools panel
2. Select **Remote (Team)** or **Local (Debug)**
3. Click **Restart Servers**

The badge always shows the current database mode at a glance.

### Option 2: Command Line

```bash
cd /path/to/webClerk3/tools

# Switch to remote database (team collaboration)
./switch-dataset.sh remote

# Switch to local database (debugging)
./switch-dataset.sh local

# Check current status
./switch-dataset.sh status
```

## Configuration

### Environment Variables

Add these to your `.env` file:

```env
# Data Set Identification - should match backend DATA_SET_ID
VITE_DATA_SET_ID='DEV'
VITE_DATA_SET_NAME='Development Server'
```

### Recommended Values by Environment

| Environment | VITE_DATA_SET_ID | VITE_DATA_SET_NAME |
|-------------|------------------|-------------------|
| Local Dev   | LOCAL            | Local Development |
| Development | DEV              | Development Server |
| Staging     | STAGING          | Staging Server |
| Production  | PROD             | Production Server |

## Components & Utilities

### DevTools Component (Dev Only)

A floating badge and panel for switching database modes. Only visible in DEV mode.

```tsx
import { DevTools } from '@/components/DevTools';

// In App.tsx
<DevTools position="bottom-left" />
```

**Badge Colors:**
- 🟢 **Green (🌐 REMOTE)** - Connected to shared team database
- 🔵 **Blue (💻 LOCAL)** - Connected to local database for debugging

### DataSetBadge Component

A visual indicator showing the current data set with mismatch warnings.

```tsx
import { DataSetBadge } from '@/components/DataSetBadge';

// Fixed position badge (bottom-right corner)
<DataSetBadge position="bottom-right" showDetails />

// Inline badge
<DataSetBadge position="inline" />

// Without expandable details
<DataSetBadge position="top-left" showDetails={false} />
```

#### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `showDetails` | boolean | false | Show expandable details panel on click |
| `position` | string | 'inline' | Position: 'top-left', 'top-right', 'bottom-left', 'bottom-right', 'inline' |
| `className` | string | '' | Additional CSS class |

#### Color Coding

- 🟢 **Green** - LOCAL/DEV environment
- 🟠 **Orange** - STAGING environment  
- 🔴 **Red** - PRODUCTION environment
- ⚠️ **Pulsing Red Border** - Frontend/Backend mismatch!

### useDataSetInfo Hook

React hook for programmatic access to data set information.

```tsx
import { useDataSetInfo } from '@/hooks/useDataSetInfo';

function MyComponent() {
  const { 
    frontend,    // { id: string, name: string }
    backend,     // SystemInfo | null
    isLoading,   // boolean
    error,       // string | null
    isMatch,     // boolean | null
    message,     // string
    refresh      // () => Promise<void>
  } = useDataSetInfo();

  if (isMatch === false) {
    console.warn('Data set mismatch!', message);
  }

  return <div>Connected to: {frontend.id}</div>;
}
```

### Utility Functions

```tsx
import { 
  getFrontendDataSet,
  fetchBackendSystemInfo,
  validateDataSetMatch,
  logDataSetInfo 
} from '@/utils/dataSetInfo';

// Get frontend config
const frontend = getFrontendDataSet();
// { id: 'DEV', name: 'Development Server' }

// Fetch backend info
const backend = await fetchBackendSystemInfo('/api');

// Validate match
const { isMatch, message } = validateDataSetMatch(frontend, backend.data_set);

// Log to console (useful for debugging)
logDataSetInfo(frontend, backend);
```

## Integration Example

Add the badge to your App.tsx or main layout:

```tsx
// src/App.tsx
import { DataSetBadge } from './components/DataSetBadge';

function App() {
  return (
    <div>
      {/* Your app content */}
      
      {/* Show data set badge in development */}
      {import.meta.env.DEV && (
        <DataSetBadge position="bottom-right" showDetails />
      )}
    </div>
  );
}
```

## Backend API

The frontend fetches data set info from:

```
GET /wcapi/system-info/
```

Response:
```json
{
  "data_set": {
    "id": "DEV",
    "name": "Development Server"
  },
  "database": {
    "host": "***.***.***.194",
    "name": "commerce_expert"
  },
  "server": {
    "debug": true,
    "django_version": [5, 0, 0],
    "python_version": "3.13.0"
  },
  "message": "Connected to Development Server (DEV)"
}
```

## Troubleshooting

### Badge Shows "UNKNOWN"
Environment variables not set. Add `VITE_DATA_SET_ID` and `VITE_DATA_SET_NAME` to your `.env` file.

### Mismatch Warning (Pulsing Red Badge)
Frontend and backend are pointing to different data sets. Check:
1. Frontend `.env` - `VITE_DATA_SET_ID`
2. Backend `.env` - `DATA_SET_ID`  
3. `VITE_API_URL` / `VITE_API_URL_PROD` pointing to correct server

### Backend Info Not Loading
- Check network tab for `/wcapi/system-info/` request
- Verify CORS settings on backend
- Ensure backend server is running

### Data Not Appearing / Wrong Database

The backend supports easy database switching. In `webClerk3/.env`:

```env
# Change to "local" for debugging, "remote" for team collaboration
DB_MODE=remote
```

| Mode | Setting | Use Case |
|------|---------|----------|
| Remote | `DB_MODE=remote` | Team collaboration, shared data |
| Local | `DB_MODE=local` | Local debugging, isolated testing |

**After changing, restart the Django server.**

See [webClerk3 Data Sync Consolidated](../../webClerk3/readmes/topics/infrastructure/data-sync-consolidated.md) for full backend documentation.

## Files

- [src/components/DataSetBadge.tsx](../src/components/DataSetBadge.tsx) - Visual badge component
- [src/hooks/useDataSetInfo.ts](../src/hooks/useDataSetInfo.ts) - React hook
- [src/utils/dataSetInfo.ts](../src/utils/dataSetInfo.ts) - Utility functions
- [.env](../.env) - Environment configuration
