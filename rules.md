Pushing to dev and main:
1. Define tests in app/tests folder or webclerk3_api/tests
2. Setup automatic testing and reporting functions.
3. All code must pass automated tests and linting before pushing to dev.
4. Only push to main after reviewing team checklist.

Version Baseline:
- All endpoints, data structures, and conventions described here are considered baseline v0.3.
- Any breaking changes or new features must increment the version and be documented.

Baseline rules that require a published exception:

1. Django REST Framework for all endpoints
2. Only json response to endpoints.
3. Standardize response with:
   3.1. { "success": true, "data": ..., "errors": {} }  
        Related data in a json must be noted as data.related{} for consistency.
   3.2. { "success": false, "data": null, "errors": { "message": "...", "help": "https://..." } }. Clear error messages with link to help.
4. jsons for exchanging information, even inputs. Convert all CSV's etc into json outside of WebClerk.
5. always refer to the table_name in its plural and a record in its singular. Drive table_names so they only have plural forms that end in "s" or "es". Minimize "es" endings. No tables ending in e
6. always use table_name for table_name of the primary table being worked and "id" is the id for the primary table record id. For non-primary table_name_id format.
7. ways save paths to larger documents. Never save large documents in the database.
8. limit size of objects that can be stored in JSONBs that might be exposed to the outside (see MAX_METADATA_SIZE = 32000 in common/models.py
9. always put relationships into table_name.refs.links.related_table_name[id1,id4,...]]
10. settings records for view_edit.  "view_edit" is a keyword that cannot be used for anything except referring to [] of fields by role for table, etc...
11. Break the common Django framework of put, post, add functions with generalized, universal wcapi/relate, wcapi/get, wcapi/save etc... see core/urls.py
11. Use Celery to wrap generalized functions such as wcapi/save to pre and post save executables.
12. ONLY use uuid for communicating between databases with syncs records. Examples, product catalog updates, security issues, default changes, etc... 

Rate Limiting:
- Implement DRF throttling classes for all endpoints to prevent abuse.
- Document rate limits for each endpoint in API docs.

Logging and Monitoring:
- All API requests and errors must be logged.
- Integrate with monitoring tools for proactive alerts (e.g., Sentry, Prometheus, or similar).
- Regularly review logs and alerts for suspicious activity or performance issues.

Related Data in jsons
1. Related data must always be sent as data.related for consistency.

Performance:
1. Optimize queries (use select_related, prefetch_related).
2. Implement pagination, filtering, and ordering for list endpoints.
3. Store all non-critical save actions in table_name temps records. Celery will run a background loop to apply the temp.data. Example, saving an invoice creates temps records for changes in inventory on-hand. A background loop will apply these changes to the products quantity_on_hand. Note that inventory critical or serialized items may require temps query to assure there is not unapplied changes in the queue.

Deployment
1. Prepare for deployment as an API-only backend (e.g., use gunicorn, nginx, etc.).
2. Set up environment variables for secrets and settings.
3. Implement pagination, filtering, and ordering for list endpoints.
4. Provide syncs records with suggested javascript and html information.

Table structure
1. always put relationships into table_name.refs.links.related_table[]
2. always save paths to larger documents. Never save large documents in the database.

Business Logic
1. In 'services' folder in each app folder for app specific endpoints
2. In 'common' folder for common things.
3. 'sandbox' folder in each app for hacks with a date to review/delete in comments
4. default setups in common/defaults  both the json data and .py to load them.
5. executables in Celery

Version Control
1. Automate version mismatches by comparing expected schema with incoming data. See and add to current settings purpose view_edit for example.
2. Use Serializers and endpoint json objects to manage issues with version control. The endpoint remains the same.
3. Push syncs records into remote databases for version issues. Users have to unpack these. When they do they assign actions records with dt_actions assigned to the appropriate person in the user's settings records.
4. Endpoint calls violating version issues should receive a response such as:
    {
    "success": false,
    "data": null,
    "errors": {
        "message": "Version mismatch detected",
        "help": "https://help.webclerk.com/versioning/...",
        "sync_id": "uuid"
    }
    }
5. Log and sync any mismatches to remote databases for resolution.
6. Except for emergency or security issues, grant a minimum of 90 days to make changes before breaking the endpoint. Send syncs records each week with countdown.

Frontend
1. always use -list for lists, tables,
2. always use -details for forms, data displays, etc...

Consistent Date/Time Handling
1. Always use ISO 8601 format for dates/times in JSON.
2. Store all times in UTC in the backend.
3. No date or time fields or variables. Name fields and variable dt_...

Internationalization (i18n)
1. Structure of multiple languages and localization.

API Documentation, Help, and Deprecation Policy
1. Add endpoint/help/ to link to data on the endpoint
2. Maintain an actions record documenting how and when endpoints or table_names.fields will be deprecated.
3. Document the process for deprecating endpoints/fields and provide migration guides with clickable urls, videos, syncs support.
4. Use sync endpoints using uuid to publish to database administrators advance notice and migration guides for breaking changes.
5. All endpoints must be documented in and kept up to date OpenAPI/Swagger. Use tools like drf-yasg or drf-spectacular to auto-generate Swagger/OpenAPI docs. Use syncs records to distribute updates to all users.
6. Use Celery to regularly scan for dependency updates from each database independent of WebClerk.com. If they find an update not covered by a syncs record, automatically post a syncs record to webclerk.com

Security:
1. Enforce HTTPS in production.
2. Provide sync functions for databases to automatically report attacks that present some risk so the programmers can adapt responses.
3. Provide sync functions to notify and/or automatically update dependencies.
4. Provide sync functions for users to install automated scans for vulnerabilities.
5. Use Django’s security middleware (SECURE_* settings).
6. Sync functions are the only used of uuid.
7. All secrets and sensitive settings must be stored in environment variables, never in code.
8. Use syncs records to regularly update dependencies and scan for vulnerabilities. Think of these as commandline actions users can cut and paste into terminals.

Data Validation
1. Provide endpoints for approved database schema.
2. Provide sync functions to add actions to remote databases for out of compliance issues.
3. Provide frontend designers rolebased feedback for designing -lists and -details.
4. In response json, add any field misuse and non-alignment errors even in successful responses.
