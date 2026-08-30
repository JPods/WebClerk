# WCAPI: Queries (Simple, Keyword, Open-Query)

This document covers query styles consolidated in wcapi.

## 1) Simple GET

Parameters:
- Filters: only fields in __meta__.filters.allow (plus any view fields if allow not provided)
- q: free-text search across __meta__.search.fields
- ordering: e.g., -date_joined
- page, page_size: constrained by __meta__.pagination

Example:
- GET /wcapi/contact?company=Acme&q=john&ordering=-date_joined&page=1&page_size=25

Specialty profile:
- GET /wcapi/contact?name=compact (or header X-View-Name: compact)

## 2) Keyword Search

Enable in __meta__.search.keywords:
- type: array with field refs__keywords for ArrayField/JSON lists
- or fallback to text search across search.fields

Usage:
- GET /wcapi/contact?kw=john,doe
- GET /wcapi/contact?kw=acme west

## 3) Open Query (POST DSL)

Endpoint:
- POST /wcapi/<model>/_query

Body:
- where: list of conditions { field, op, value }
- order_by: ["-date_joined"]
- joins: ["emails", "phones"] (aliases defined in __meta__.query.allow_joins)
- limit, offset: constrained by __meta__.query.max_rows

Example:
{
  "where": [
    { "field": "company", "op": "icontains", "value": "Acme" },
    { "field": "role", "op": "in", "value": ["ADMIN","USER"] }
  ],
  "order_by": ["-date_joined"],
  "joins": ["emails"],
  "limit": 100,
  "offset": 0
}

Supported ops:
- eq, ne, lt, lte, gt, gte
- contains, icontains
- startswith, istartswith, endswith, iendswith
- in, isnull

Security policy (__meta__.query):
- allow_fields: whitelist of fields
- allow_ops: allowed operations
- allow_joins: { alias: "path" } for safe prefetch/select
- max_rows: server cap (limit is clamped)
- max_depth: reserved for future nested conditions

Saved queries:
- POST /wcapi/<model>/_query with { "saved": "<id|name>" } runs a saved query DSL.

## Serialization

List results are serialized with role-based view fields and optional relations from __meta__.relations. Specialty profile can override fields/pagination.

## Examples (curl)

- Simple:
  curl -sS "http://localhost:8000/wcapi/contact?kw=john&company=Acme"

- Open-query:
  curl -sS -X POST http://localhost:8000/wcapi/contact/_query \
    -H "Content-Type: application/json" \
    -d '{"where":[{"field":"company","op":"icontains","value":"Acme"}],"limit":50}'

- Saved:
  curl -sS -X POST http://localhost:8000/wcapi/contact/_query \
    -H "Content-Type: application/json" \
    -d '{"saved":"My Contacts"}'