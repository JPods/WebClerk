# Centralized Cache Service Implementation

## Overview

WebClerk now features a centralized, Redis-backed cache service that provides cross-process consistency, automatic versioning, and async cache updates via Celery. This replaces scattered caching mechanisms with a unified, scalable solution.

## Architecture

### Core Components

1. **CacheService** (`apps/core/services/cache_service.py`)
   - Redis-backed caching with automatic versioning
   - Graceful degradation when Redis unavailable
   - Cross-process consistency across workers

2. **Cache Tasks** (`apps/core/tasks/cache_tasks.py`)
   - Async cache update operations
   - Scheduled cache refresh tasks
   - Bulk cache invalidation utilities

3. **Cache Signals** (`apps/core/signals/cache_signals.py`)
   - Automatic cache invalidation on data changes
   - Async cache refresh triggers

## Key Features

### 🔄 Cross-Process Consistency
All workers share the same Redis cache, ensuring consistent data across processes.

### 🚀 Async Updates
Expensive cache computations run asynchronously via Celery, preventing request blocking.

### 📦 Automatic Versioning
Cache keys include version hashes that automatically invalidate on deployments.

### 🛡️ Graceful Degradation
System continues functioning if Redis is unavailable, falling back to local storage.

### 🎯 Centralized Management
Single service handles all cache operations with consistent TTLs and invalidation.

## Implementation Details

### CacheService Class

```python
from apps.core.services.cache_service import cache_service

# Basic operations
cache_service.set('key', {'data': 'value'}, ttl=3600)
data = cache_service.get('key')
cache_service.delete('key')

# Namespace operations
cache_service.invalidate_namespace('permissions')
```

### Cache Key Structure
```
{v8d4e1f2}:{namespace}:{part1}:{part2}:{...}
```

Where:
- `v8d4e1f2` is the version hash (first 8 chars of SECRET_KEY MD5)
- `namespace` groups related cache entries
- `parts` provide unique identification within namespace

### Scheduled Cache Updates

| Task | Schedule | Purpose |
|------|----------|---------|
| `update_access_fields_cache` | Every 5 minutes | Refresh permission rules |
| `update_keyword_requirements_cache` | Every 10 minutes | Update keyword validation |
| `update_model_registry_cache` | Daily | Refresh model registry |
| `update_constants_cache` | Every 30 minutes | Refresh database constants |

## Migrated Components

### GlobalStorage
- Now uses Redis with local fallback
- Maintains backward compatibility
- Cross-process consistency

### Keyword Requirements
- Uses centralized cache service
- Automatic invalidation on Setting changes
- Async refresh via Celery

### Transaction Aggregations
- Redis-backed caching with TTL windows
- Proper invalidation on data changes
- Maintains existing LRU cache as fallback

### Permission Matrices
- Enhanced with Redis caching
- Automatic invalidation via signals
- Preserves existing LRU cache performance

### Constants Initialization
- Database-driven constants via Setting records
- Support for multiple categories (industry-specific, UI defaults, etc.)
- Cached loading with automatic refresh on changes
- Industry-specific constant variations

## Cache Namespaces

| Namespace | Purpose | TTL | Invalidation Trigger |
|-----------|---------|-----|---------------------|
| `global` | General application data | 1 hour | Manual |
| `permissions` | View/edit permission matrices | 1 hour | Setting changes |
| `keywords` | Keyword validation rules | 1 hour | Setting changes |
| `registry` | Model registry data | 24 hours | Daily refresh |
| `aggregation` | Transaction aggregations | Dynamic | Data changes |
| `constants` | Database-driven constants | 1 hour | Setting changes |

## Usage Examples

### Basic Caching
```python
from apps.core.services.cache_service import cache_service

# Cache expensive computation
key = cache_service.make_key('myapp', 'computation', str(param_id))
result = cache_service.get(key)
if result is None:
    result = expensive_computation(param_id)
    cache_service.set(key, result, ttl=1800)  # 30 minutes
return result
```

### Cache Invalidation
```python
# Invalidate all permission caches
cache_service.invalidate_namespace('permissions')

# Invalidate specific cache entry
cache_key = cache_service.make_key('permissions', 'matrix', str(setting_id))
cache_service.delete(cache_key)
```

### Async Cache Updates
```python
from apps.core.tasks.cache_tasks import update_keyword_requirements_cache, update_constants_cache

# Trigger async cache refresh
update_keyword_requirements_cache.delay()
update_constants_cache.delay()
```

### Constants Usage
```python
from apps.core.constants.constants_init import get_constants, get_constant

# Get all constants
all_constants = get_constants()

# Get constants for specific category
industry_constants = get_constants('industry_specific')

# Get specific constant value
tax_rate = get_constant('industry_specific', 'tax_rate', default=0.08)
```

## Configuration

### Settings Integration
Cache management tasks are configured in `CELERY_BEAT_SCHEDULE`:

```python
CELERY_BEAT_SCHEDULE = {
    'update-access-cache-5m': {
        'task': 'apps.core.tasks.cache_tasks.update_access_fields_cache',
        'schedule': 5 * 60,
    },
    # ... other cache tasks
}
```

### Environment Variables
- `CELERY_RESULT_BACKEND`: Redis URL for cache storage
- `SECRET_KEY`: Used for cache versioning

## Monitoring & Maintenance

### Cache Metrics
- Monitor Redis memory usage
- Track cache hit/miss ratios
- Monitor Celery task execution

### Manual Operations
```python
from apps.core.signals.cache_signals import invalidate_all_caches

# Invalidate all caches (emergency)
invalidate_all_caches()
```

### Health Checks
```python
# Check Redis connectivity
is_healthy = cache_service.redis is not None
ttl = cache_service.get_ttl('test_key')
```

## Benefits

1. **Performance**: Faster response times through intelligent caching
2. **Scalability**: Cross-process consistency enables horizontal scaling
3. **Reliability**: Graceful degradation and automatic recovery
4. **Maintainability**: Centralized cache management and monitoring
5. **Consistency**: Single source of truth for cache operations

## Migration Notes

- Existing code continues to work unchanged
- New caching should use `CacheService` directly
- Old in-memory caches remain as fallbacks
- Cache versioning prevents stale data issues

## Constants Management

### Setting Record Structure
Constants are stored in Setting records with the following structure:

```json
{
    "purpose": "constant_init",
    "model_name": "industry_specific",
    "data": {
        "default_currency": "USD",
        "tax_rate": 0.08,
        "business_hours": {"start": "09:00", "end": "17:00"}
    },
    "is_active": true
}
```

### Categories
- `industry_specific`: Industry-specific business rules and defaults
- `ui_defaults`: User interface configuration and themes
- `business_rules`: General business logic constants
- `integrations`: Third-party integration settings
- `general`: Fallback category for miscellaneous constants

### Remote Updates
Constants can be updated remotely by modifying Setting records:

```sql
-- Example: Update tax rate for industry_specific constants
UPDATE core_setting
SET data = data || '{"tax_rate": 0.10}'
WHERE purpose = 'constant_init'
  AND model_name = 'industry_specific'
  AND is_active = true;
```

This enables live updates without code deployments, perfect for:
- Seasonal business rule changes
- Industry-specific customizations
- A/B testing of constant values
- Emergency configuration changes

## Related Systems

### Mandatory Constants
For application constants management, see: [`readmes/mandatory-constants.md`](mandatory-constants.md)

Mandatory constants provide default values for core application settings, automatically created during system initialization.

### Save Hooks
For custom save logic, see: [`readmes/save-hooks.md`](save-hooks.md)

Save hooks enable administrators to define custom pre/post-save scripts stored in Setting records.

## Future Enhancements

- Cache warming on startup
- Cache analytics and reporting
- Distributed cache invalidation
- Cache compression for large objects
- Cache dependency management
- Constants validation and type checking
- Constants migration tools for deployments