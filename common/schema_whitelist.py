"""Endpoint whitelist for OpenAPI generation.

Add regex patterns (anchored) for paths you want included in the schema.
Example:
    WHITELIST = [
        r'^/api/auth/login/$',
        r'^/api/auth/signup/$',
    ]

Leave empty to exclude all endpoints by default.

Notes
- Patterns are regular expressions and must be anchored with ^ and $
- This file is documentation-friendly: each entry below is annotated with its HTTP method.
- For more, see readmes/schema-whitelist.md
"""

from typing import List

# ------------------------------------------------------------------------------------
# How to add a new endpoint to the schema whitelist
#
# 1) Decide the exact path and method. Examples (commented):
#    - GET  /api/ping/                -> r'^/api/ping/$'
#    - POST /api/items/               -> r'^/api/items/$'
#    - GET  /api/items/42/detail/     -> r'^/api/items/\\d+/detail/$'
#
# 2) Add the anchored regex pattern to WHITELIST below.
# 3) Regenerate the schema and sync JSON (see readmes/schema-whitelist.md).
# ------------------------------------------------------------------------------------

WHITELIST: List[str] = [
    # Auth APIs
    r'^/wcapi/register/$',           # POST – User registration
    r'^/wcapi/signup/$',             # POST – User registration (alias)
    r'^/wcapi/login/$',              # POST – User login
    r'^/wcapi/logout/$',             # POST – User logout
    r'^/wcapi/me/$',                 # GET  – Get current user profile
    # JWT APIs
    r'^/wcapi/token/$',              # POST – Obtain JWT token pair
    r'^/wcapi/token_refresh/$',      # POST – Refresh JWT token
    # WCAPI endpoints
    r'^/wcapi/get/$',                # GET  – registry-backed list/detail
    r'^/wcapi/save/$',               # POST – registry-backed create/update
    r'^/wcapi/transaction/save/$',   # POST – transaction save endpoint
    r'^/wcapi/models/$',             # GET  – model name -> field names
    r'^/api/model-fields/$',         # GET  – detailed field metadata
    r'^/wcapi/model_name/list/$',    # GET  – list of canonical model_name codes
    r'^/wcapi/model_name/detail/$',  # GET  – detail for a specific model_name
    r'^/wcapi/choices/$',            # GET  – choice catalog for dropdowns
    # Organization APIs
    r'^/api/orgs/customers/$',       # GET/POST – Customer list/create
    r'^/api/orgs/customers/\d+/$',   # GET/PUT/PATCH/DELETE – Customer detail
    # Transaction APIs
    r'^/api/transactions/proposals/$',        # GET/POST – Proposal list/create
    r'^/api/transactions/proposals/\d+/$',    # GET/PUT/PATCH/DELETE – Proposal detail
    r'^/api/transactions/orders/$',           # GET/POST – Order list/create
    r'^/api/transactions/orders/\d+/$',       # GET/PUT/PATCH/DELETE – Order detail
    r'^/api/transactions/purchases/$',        # GET/POST – Purchase list/create
    r'^/api/transactions/purchases/\d+/$',    # GET/PUT/PATCH/DELETE – Purchase detail
    r'^/api/transactions/invoices/$',         # GET/POST – Invoice list/create
    r'^/api/transactions/invoices/\d+/$',     # GET/PUT/PATCH/DELETE – Invoice detail
    r'^/api/transactions/payments/$',         # GET/POST – Payment list/create
    r'^/api/transactions/payments/\d+/$',     # GET/PUT/PATCH/DELETE – Payment detail
    # Documentation APIs
    r'^/api/docs/stats/$',           # GET – Documentation statistics
]
