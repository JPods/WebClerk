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
    r'^/api/auth/login/$',           # POST – JSON login
    r'^/wcapi/get/$',                # GET  – registry-backed list/detail
    r'^/wcapi/save/$',               # POST – registry-backed create/update
    r'^/wcapi/models/$',             # GET  – model name -> field names
    r'^/api/model-fields/$',         # GET  – detailed field metadata
    r'^/wcapi/model_name/list/$',    # GET  – list of canonical model_name codes
    r'^/wcapi/model_name/detail/$',  # GET  – detail for a specific model_name
]
