# Mandatory Constants Reference

## Overview

Mandatory constants are essential configuration values that must be present in the system for proper operation. These constants are automatically created during system initialization and provide default values for core application settings.

## Categories and Constants

### System Defaults (`system_defaults`)
Core system configuration values that affect basic application behavior.

| Constant | Type | Default | Description |
|----------|------|---------|-------------|
| `default_currency` | string | "USD" | Default currency for financial operations |
| `default_timezone` | string | "UTC" | Default timezone for date/time operations |
| `max_upload_size_mb` | integer | 10 | Maximum file upload size in megabytes |
| `session_timeout_minutes` | integer | 60 | User session timeout in minutes |
| `max_login_attempts` | integer | 5 | Maximum failed login attempts before lockout |
| `password_min_length` | integer | 8 | Minimum password length requirement |
| `default_language` | string | "en" | Default user interface language |
| `items_per_page` | integer | 25 | Default number of items per page in lists |
| `max_items_per_page` | integer | 100 | Maximum allowed items per page |

### Business Rules (`business_rules`)
Business logic configuration that affects transaction processing and validation.

| Constant | Type | Default | Description |
|----------|------|---------|-------------|
| `default_tax_rate` | float | 0.0 | Default tax rate for transactions |
| `invoice_due_days` | integer | 30 | Default invoice payment due period |
| `quote_valid_days` | integer | 30 | Default quote validity period |
| `default_payment_terms` | string | "Net 30" | Default payment terms text |
| `auto_save_interval_seconds` | integer | 30 | Auto-save interval for forms |
| `max_line_items_per_transaction` | integer | 100 | Maximum line items per transaction |
| `decimal_precision` | integer | 2 | Decimal places for monetary values |
| `rounding_mode` | string | "HALF_UP" | Rounding mode for calculations |

### UI Defaults (`ui_defaults`)
User interface configuration and display preferences.

| Constant | Type | Default | Description |
|----------|------|---------|-------------|
| `theme` | string | "light" | Default UI theme (light/dark) |
| `date_format` | string | "MM/DD/YYYY" | Default date display format |
| `time_format` | string | "12h" | Time format (12h/24h) |
| `number_format` | string | "en-US" | Number formatting locale |
| `currency_display` | string | "symbol" | Currency display style |
| `table_density` | string | "comfortable" | Table row density |
| `sidebar_collapsed` | boolean | false | Default sidebar state |
| `notifications_enabled` | boolean | true | Enable user notifications |

### Security (`security`)
Security-related configuration and policies.

| Constant | Type | Default | Description |
|----------|------|---------|-------------|
| `password_history_count` | integer | 5 | Number of previous passwords to remember |
| `password_expiry_days` | integer | 90 | Password expiry period in days |
| `session_inactivity_timeout` | integer | 30 | Session timeout on inactivity (minutes) |
| `two_factor_required` | boolean | false | Require two-factor authentication |
| `audit_log_retention_days` | integer | 365 | Audit log retention period |
| `max_concurrent_sessions` | integer | 3 | Maximum concurrent user sessions |

### Integrations (`integrations`)
External service integration settings.

| Constant | Type | Default | Description |
|----------|------|---------|-------------|
| `email_enabled` | boolean | true | Enable email functionality |
| `sms_enabled` | boolean | false | Enable SMS functionality |
| `api_rate_limit_per_minute` | integer | 60 | API rate limit per minute |
| `webhook_timeout_seconds` | integer | 30 | Webhook request timeout |
| `max_webhook_retries` | integer | 3 | Maximum webhook retry attempts |

### Performance (`performance`)
System performance and caching configuration.

| Constant | Type | Default | Description |
|----------|------|---------|-------------|
| `cache_ttl_seconds` | integer | 3600 | Default cache time-to-live |
| `db_query_timeout_seconds` | integer | 30 | Database query timeout |
| `max_concurrent_requests` | integer | 100 | Maximum concurrent requests |
| `file_cache_size_mb` | integer | 100 | File cache size limit |
| `memory_cache_size_mb` | integer | 50 | Memory cache size limit |

## Usage Examples

### Getting Constants
```python
from apps.core.constants.mandatory_constants import get_mandatory_constant, get_constant_with_fallback

# Get a specific mandatory constant
default_currency = get_mandatory_constant('system_defaults', 'default_currency')

# Get with fallback (database -> mandatory defaults -> provided default)
tax_rate = get_constant_with_fallback('business_rules', 'default_tax_rate', 0.0)
```

### Validation
```python
from apps.core.constants.mandatory_constants import validate_mandatory_constants

# Validate all mandatory constants are properly configured
result = validate_mandatory_constants()
if not result['valid']:
    print("Issues found:", result['issues'])
```

### Initialization
```python
from apps.core.constants.mandatory_constants import ensure_mandatory_constants_exist

# Ensure all mandatory constants exist in database
result = ensure_mandatory_constants_exist()
print(f"Created: {result['created']}")
print(f"Existing: {result['existing']}")
```

## Database Storage

Mandatory constants are stored as Setting records with:
- `purpose`: 'constant_init'
- `model_name`: Category name (e.g., 'system_defaults')
- `data`: JSON object containing the constants
- `is_active`: true

Example Setting record:
```json
{
    "purpose": "constant_init",
    "model_name": "system_defaults",
    "data": {
        "default_currency": "USD",
        "default_timezone": "UTC",
        "max_upload_size_mb": 10
    },
    "is_active": true,
    "description": "Mandatory constants for system defaults"
}
```

## Remote Updates

Constants can be updated remotely without code deployments:

```sql
-- Update default currency
UPDATE core_setting
SET data = data || '{"default_currency": "EUR"}'
WHERE purpose = 'constant_init'
  AND model_name = 'system_defaults';

-- Add new constant
UPDATE core_setting
SET data = data || '{"new_feature_enabled": true}'
WHERE purpose = 'constant_init'
  AND model_name = 'system_defaults';
```

## Initialization Process

### Django App Startup (`apps/core/apps.py`)
During Django app initialization:

1. Load cached constants from Redis
2. Ensure mandatory constants exist in database
3. Create any missing Setting records with defaults
4. Update existing records with missing keys

### Development Server Startup (`webclerk3_api/settings.py`)
When running `python manage.py runserver`:

1. **Django Setup Check**: Ensure Django is configured and models are loaded
2. **Constants Initialization**: Call `ensure_mandatory_constants_exist(verbose=False)`
3. **Database Creation**: Create any missing Setting records with default values
4. **Silent Operation**: No verbose output during server startup
5. **Cache Loading**: Refresh in-memory and Redis caches

**Example output when starting development server:**
```
[INIT] Constants ready: 6 categories, 35 constants
```

**Note**: When constants are created during `runserver`, they are marked with metadata flags:
- `metadata.health.forced = true` - Indicates automatic creation
- `metadata.history.created.forced = true` - Tracks forced initialization

**Note**: The development server runs with `verbose=False` to keep startup output clean. Use `python manage.py ensure_constants` for detailed status information.

This ensures constants are **always available** regardless of environment or deployment method.

## Validation

The system validates:
- All mandatory categories exist
- All required constants are present
- Constant values have correct types
- No invalid or corrupted data

## Best Practices

1. **Use get_constant_with_fallback()** for application code to ensure graceful degradation
2. **Validate regularly** using validate_mandatory_constants() in health checks
3. **Document changes** when updating mandatory constants
4. **Test thoroughly** when modifying default values
5. **Monitor usage** to identify frequently accessed constants

## Troubleshooting

### Missing Constants
If constants are missing, run:
```python
from apps.core.constants.mandatory_constants import ensure_mandatory_constants_exist
result = ensure_mandatory_constants_exist()
```

### Invalid Types
Check the validation results:
```python
from apps.core.constants.mandatory_constants import validate_mandatory_constants
result = validate_mandatory_constants()
print(result['issues'])
```

### Cache Issues
Clear the constants cache:
```python
from apps.core.services.cache_service import cache_service
cache_service.invalidate_namespace('constants')
