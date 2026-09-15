# Document Upload — Auth Architecture

## The Problem (2026-08-29)

`POST /wcapi/upload/` returned 500 on file uploads from FileUploadPanel.

Root cause: `_serialize_document()` referenced `doc.model_name` — an attribute
that doesn't exist on the Document model. The parent model name is stored in
`doc.config["parent_model"]`, not as a top-level attribute.

Secondary fix: the three document views (Upload, Download, Delete) had no explicit
`authentication_classes`, falling through to the default
`RoleValidatingJWTAuthentication`. This works when the JWT has a valid role claim
that matches the DB user, but it's fragile — any token without a role claim gets
a hard `AuthenticationFailed` instead of falling through to `SessionAuthentication`.

## Auth Design

Upload authority is based on the **current authenticated user**, not the Contact
role system. The document views now use:

```python
authentication_classes = [JWTAuthentication, SessionAuthentication]
permission_classes = [IsAuthenticated]
```

- `JWTAuthentication` (plain, no role validation) — accepts any valid JWT
- `SessionAuthentication` — fallback for cookie-based requests
- `IsAuthenticated` — user must be logged in, no role check

This is deliberately different from the default `RoleValidatingJWTAuthentication`
used by most wcapi endpoints. Upload/download/delete are utility operations —
any authenticated user can manage documents. Role-based restrictions (if needed)
belong at the application layer, not the auth layer.

## How It Works

1. Frontend sends `POST /wcapi/upload/` with `Authorization: Bearer <token>` and
   `Content-Type: multipart/form-data`
2. `JWTAuthentication` validates the token and returns the user
3. `IsAuthenticated` confirms the user is active
4. `DocumentUploadView.post()` writes the file to disk and creates a Document record
5. Response includes full document metadata including download URL

## File Storage

Files land at `<BASE_DIR>/uploads/document/YYYY/MM/<uuid>.<ext>` (local disk).
Alice moves files to cloud library in a separate process.

## Files

- `apps/docs/views/upload_view.py` — Upload, Download, Delete views
- `apps/docs/urls.py` — URL patterns (mounted at `wcapi/` in main urls.py)
- `apps/core/auth.py` — `RoleValidatingJWTAuthentication` (NOT used by upload views)
- `apps/core/token_views.py` — Token generation (adds role claim)

## The Scar

See `readmes/wisdom/scars.md` — "Upload 500 — Auth Red Herring". The 500 was
misdiagnosed as an auth issue for a full session. The actual fix was one line
in `_serialize_document()`. Rule: when Django returns 500, reproduce with curl
and read the error body before theorizing. 500 means the view crashed — auth
failures are 401/403.
