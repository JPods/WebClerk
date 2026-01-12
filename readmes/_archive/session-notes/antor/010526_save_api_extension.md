# WCAPI Save API Extension: Bulk Operations

- **Author**: Antor Ahmed
- **Time**: 2026-01-05T13:03:00.231Z (Asia/Dhaka UTC+6)
- **Purpose**: Document the extension of the wcapi/save API to support bulk save operations, allowing multiple model saves in a single atomic transaction.

## Overview
The wcapi/save API has been extended to support bulk operations. Previously, the API could only save one model record per request. Now, it can handle multiple saves atomically using a new 'bulk' parameter in the payload.

## Changes Made

### 1. API Payload Extension
- Added support for a new `bulk` key in the JSON payload.
- `bulk` is an optional array of objects, each representing a separate save operation.
- Each bulk item must include `model_name` and other fields similar to the main payload.

### 2. Transaction Atomicity
- Wrapped the entire save operation (main + bulk) in a Django database transaction.
- Ensures all operations succeed or all fail together, maintaining data consistency.

### 3. Error Handling
- Bulk operations are processed sequentially after the main save.
- If a bulk item fails, it is recorded in the response with an error message, but does not rollback the entire transaction.
- The response includes `bulk_results` array with success payloads or error details for each bulk operation.

### 4. Code Refactoring
- Extracted the core save logic into a new `_perform_save` method in `SaveWcapiView`.
- Modified the `post` method to handle bulk processing.
- Added transaction import and updated type hints.

### 5. OpenAPI Schema Updates
- Updated the request serializer to include the `bulk` field.
- Updated the response serializer to include `bulk_results`.
- Added documentation and examples for bulk operations.
- Updated the API description to mention bulk functionality.

### 6. Backward Compatibility
- The extension is fully backward compatible.
- Existing clients using the API without `bulk` will continue to work unchanged.
- `bulk` is optional and defaults to no bulk operations.

## API Usage

### Request Format
```json
{
  "model_name": "project",
  "id": 3,
  "name": {"mode": "update", "value": "Updated Project"},
  "bulk": [
    {
      "model_name": "action",
      "id": 5,
      "status": {"mode": "update", "value": "completed"}
    },
    {
      "model_name": "contact",
      "name_first": {"mode": "update", "value": "John"}
    }
  ]
}
```

### Response Format
```json
{
  "status": "success",
  "code": 200,
  "message": "",
  "data": {
    "id": 3,
    "model_name": "project",
    "record": {"id": 3, "name": "Updated Project"},
    "bulk_results": [
      {
        "id": 5,
        "model_name": "action",
        "record": {"id": 5, "status": "completed"}
      },
      {
        "error": "Record not found",
        "model_name": "contact",
        "id": null
      }
    ]
  }
}
```

## Files Modified
- `apps/core/views/save_view.py`: Main implementation
  - Added `_perform_save` method
  - Modified `post` method for bulk handling
  - Updated imports and schema

## Testing
- The implementation maintains all existing functionality.
- Bulk operations are processed in order after main save.
- Error isolation ensures one failed bulk item doesn't affect others or the main save.
- Transaction rollback occurs only if the main save fails.

## Future Considerations
- Consider adding bulk size limits for performance.
- Potential for parallel processing of bulk items if no dependencies.
- Monitoring and logging for bulk operation metrics.