"""
filter_operators — single source of truth for allowed query filter lookups.

Mirrors: React2025/src/constants/filterOperators.ts
Used by: wcapi.py _parse_filters(), _request_filter_specs()

Import ALLOWED_LOOKUPS from here instead of defining inline.
"""

ALLOWED_LOOKUPS = frozenset({
    'exact', 'iexact', 'contains', 'icontains',
    'startswith', 'endswith',
    'gt', 'gte', 'lt', 'lte',
    'in', 'range', 'isnull', 'ne',
})

# Operators that require negation via Q objects (not direct filter kwargs)
NEGATED_LOOKUPS = frozenset({'ne', 'not_contains'})

# Map from field internal type to applicable lookups
LOOKUPS_BY_FIELD_TYPE = {
    'CharField': {'exact', 'iexact', 'contains', 'icontains', 'startswith', 'endswith', 'isnull', 'ne'},
    'TextField': {'exact', 'iexact', 'contains', 'icontains', 'startswith', 'endswith', 'isnull', 'ne'},
    'IntegerField': {'exact', 'gt', 'gte', 'lt', 'lte', 'in', 'range', 'isnull', 'ne'},
    'FloatField': {'exact', 'gt', 'gte', 'lt', 'lte', 'in', 'range', 'isnull', 'ne'},
    'DecimalField': {'exact', 'gt', 'gte', 'lt', 'lte', 'in', 'range', 'isnull', 'ne'},
    'DateField': {'exact', 'gt', 'gte', 'lt', 'lte', 'range', 'isnull'},
    'DateTimeField': {'exact', 'gt', 'gte', 'lt', 'lte', 'range', 'isnull'},
    'BooleanField': {'exact', 'isnull'},
    'ForeignKey': {'exact', 'in', 'isnull', 'ne'},
}
