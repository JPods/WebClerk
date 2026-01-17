# Data Set Identification

This document describes the mechanism for identifying which data set (environment/database) the backend is connected to.

## Purpose

When working with multiple environments (LOCAL, DEV, STAGING, PRODUCTION), it's critical to know which data set the frontend and backend are communicating with. This prevents accidentally mixing data between environments.

## Quick Start: Switching Databases

### Option 1: Frontend Dev Tools (Recommended)

Click the color-coded badge in the **bottom-left corner** of the React app:
- 🟢 **Green badge** = Remote database (team collaboration)
- 🔵 **Blue badge** = Local database (debugging)

Click to expand the panel, select a mode, then click **Restart Servers**.

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
# Data Set Identification
DATA_SET_ID=DEV                      # Options: LOCAL, DEV, STAGING, PRODUCTION, or custom
DATA_SET_NAME=Development Server     # Human-readable name
```

### Database Toggle (Quick Switch)

Change **one line** in `.env` to switch between databases:

```env
# Options: "remote" or "local"
DB_MODE=remote
```

| Mode | Setting | Use Case |
|------|---------|----------|
| Remote | `DB_MODE=remote` | Team collaboration, shared development |
| Local | `DB_MODE=local` | Local debugging, isolated testing |

**After changing, restart the Django server.** You'll see a confirmation message:
```
[webClerk3] Data Set: DEV - Development Server
[webClerk3] Database: REMOTE @ 85.31.234.194:5432/commerce_expert
```
or
```
[webClerk3] Data Set: DEV - Development Server
[webClerk3] Database: LOCAL @ localhost:5432/commerce_expert
```

### Full Database Configuration

```env
# Toggle: Change this ONE line to switch databases
DB_MODE=remote

# Remote Postgres (team collaboration)
REMOTE_DATABASE_HOST=85.31.234.194
REMOTE_DATABASE_PORT=5432
REMOTE_DATABASE_NAME=commerce_expert
REMOTE_DATABASE_USER=postgres
REMOTE_DATABASE_PASS=wc_psql_server

# Local Postgres (debugging)
LOCAL_DATABASE_HOST=localhost
LOCAL_DATABASE_PORT=5432
LOCAL_DATABASE_NAME=commerce_expert
LOCAL_DATABASE_USER=williamjames
LOCAL_DATABASE_PASS=
```

### Recommended Values by Environment

| Environment | DATA_SET_ID | DATA_SET_NAME |
|-------------|-------------|---------------|
| Local Dev   | LOCAL       | Local Development |
| Development | DEV         | Development Server |
| Staging     | STAGING     | Staging Server |
| Production  | PROD        | Production Server |

## API Endpoint

### GET `/wcapi/system-info/`

Returns system identification information. **No authentication required.**

#### Response Example

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

#### Security Notes

- Database host is partially masked (only last octet shown for remote hosts)
- No credentials are exposed
- Debug mode status is visible to help identify environment

## Usage

### Quick Check via curl

```bash
curl http://localhost:8000/wcapi/system-info/
```

### In Python Code

```python
from decouple import config

data_set_id = config('DATA_SET_ID', default='UNKNOWN')
data_set_name = config('DATA_SET_NAME', default='Unknown')

print(f"Connected to {data_set_name} ({data_set_id})")
```

## Frontend Integration

The React2025 frontend has corresponding utilities:
- `VITE_DATA_SET_ID` and `VITE_DATA_SET_NAME` environment variables
- `useDataSetInfo` hook to fetch and compare data sets
- `DataSetBadge` component to display current environment

See the React2025 readme for frontend documentation.

## Troubleshooting

### "UNKNOWN" Data Set ID
The environment variables are not set. Add `DATA_SET_ID` and `DATA_SET_NAME` to your `.env` file.

### Mismatch Warning
If the frontend and backend data set IDs don't match, you're likely pointing to different environments. Check:
1. Backend `.env` - `DATA_SET_ID`
2. Frontend `.env` - `VITE_DATA_SET_ID`
3. API URL configuration in frontend

## Files

- [apps/core/views/system_info.py](../apps/core/views/system_info.py) - API view
- [apps/core/urls.py](../apps/core/urls.py) - URL routing
- [.env](../.env) - Environment configuration
