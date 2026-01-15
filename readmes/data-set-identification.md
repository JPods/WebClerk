# Data Set Identification

This document describes the mechanism for identifying which data set (environment/database) the backend is connected to.

## Purpose

When working with multiple environments (LOCAL, DEV, STAGING, PRODUCTION), it's critical to know which data set the frontend and backend are communicating with. This prevents accidentally mixing data between environments.

## Configuration

### Environment Variables

Add these to your `.env` file:

```env
# Data Set Identification
DATA_SET_ID=DEV                      # Options: LOCAL, DEV, STAGING, PRODUCTION, or custom
DATA_SET_NAME=Development Server     # Human-readable name
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
