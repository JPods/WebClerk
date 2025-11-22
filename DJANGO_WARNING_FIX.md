# Django Database Warning Fix

## Problem
The original `python manage.py check` command was showing this warning:
```
RuntimeWarning: Accessing the database during app initialization is discouraged. 
To fix this warning, avoid executing queries in AppConfig.ready() or when your app modules are imported.
```

## Root Cause
The `apps/core/apps.py` file had a `ready()` method that was calling `update_all_settings_cache()` during Django app initialization. This made database queries before Django was fully loaded, triggering the warning.

## Solution Implemented

### 1. Moved Database Operations Out of App Initialization
- **Before**: Database queries were called directly in `CoreConfig.ready()`
- **After**: Database queries are now handled by Django signals that fire after Django is fully initialized

### 2. Created Management Command
Created `apps/core/management/commands/populate_cache.py` that provides:
- Manual cache population: `python manage.py populate_cache`
- Selective cache types: `python manage.py populate_cache --cache-type settings`
- Silent mode for automation: `python manage.py populate_cache --silent`

### 3. Added Signal-Based Auto-Population
Created `apps/core/init_handlers.py` that:
- Uses `post_migrate` signal to populate cache after Django is ready
- Includes lazy loading function for on-demand cache population
- Provides graceful error handling with logging

### 4. Updated App Configuration
Modified `apps/core/apps.py` to:
- Remove direct database calls from `ready()` method
- Import signal handlers to enable auto-population
- Maintain all existing functionality while eliminating warnings

## Files Changed

| File | Changes |
|------|---------|
| `apps/core/apps.py` | Removed database calls from `ready()` method |
| `apps/core/init_handlers.py` | **NEW** - Signal handlers for post-migration cache population |
| `apps/core/management/commands/populate_cache.py` | **NEW** - Management command for manual cache control |
| `apps/core/management/__init__.py` | **NEW** - Package initialization |
| `apps/core/management/commands/__init__.py` | **NEW** - Package initialization |

## Usage

### Automatic (Recommended)
The cache will be automatically populated after migrations complete. No manual action required.

### Manual Control
```bash
# Populate all caches
python manage.py populate_cache

# Populate only settings cache
python manage.py populate_cache --cache-type settings

# Silent mode for automation
python manage.py populate_cache --silent
```

### Verify Fix
```bash
python manage.py check
```
Should now show "checking freezed!" without the database warning.

## Benefits
- ✅ Eliminates Django database initialization warning
- ✅ Maintains automatic cache population functionality  
- ✅ Provides manual control options
- ✅ Better separation of concerns
- ✅ Improved startup performance
- ✅ Graceful error handling