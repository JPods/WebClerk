# Web Clerk API Gateway (wcapi)

Canonical-only
- Blessed models: contact (core.Contact), domain (communications.Domain), document (docs.Document), linkage (docs.Linkage)
- q on list endpoints (GET /<model>/?q=...) is staff-only (403 for non-staff).