/**
 * filterOperators — single source of truth for query filter operators.
 *
 * Used by: DataGrid column filters, RowColorRule evaluation, wcapi filter parsing.
 * Django backend: apps/core/constants/filter_operators.py mirrors this vocabulary.
 *
 * Each operator maps a user-facing label to a Django ORM lookup suffix.
 * Grouped by field type — UI shows only operators appropriate to the field.
 */

export type FilterOperator = {
  label: string;
  key: string;         // internal key used in RowColorRule, DataGrid filters
  django: string;      // Django ORM lookup suffix (appended after __)
};

export const TEXT_OPERATORS: FilterOperator[] = [
  { label: 'Contains', key: 'contains', django: 'icontains' },
  { label: 'Begins with', key: 'startswith', django: 'startswith' },
  { label: 'Ends with', key: 'endswith', django: 'endswith' },
  { label: 'Is', key: 'eq', django: 'exact' },
  { label: 'Is not', key: 'neq', django: 'ne' },
  { label: 'Does not contain', key: 'not_contains', django: 'icontains' },  // negated in query
  { label: 'Is empty', key: 'empty', django: 'isnull' },
  { label: 'Is not empty', key: 'notempty', django: 'isnull' },  // negated
];

export const NUMBER_OPERATORS: FilterOperator[] = [
  { label: 'Equals', key: 'eq', django: 'exact' },
  { label: 'Not equal', key: 'neq', django: 'ne' },
  { label: 'Greater than', key: 'gt', django: 'gt' },
  { label: 'Less than', key: 'lt', django: 'lt' },
  { label: 'Greater or equal', key: 'gte', django: 'gte' },
  { label: 'Less or equal', key: 'lte', django: 'lte' },
  { label: 'Is empty', key: 'empty', django: 'isnull' },
  { label: 'Is not empty', key: 'notempty', django: 'isnull' },
];

export const DATE_OPERATORS: FilterOperator[] = [
  { label: 'Is', key: 'eq', django: 'exact' },
  { label: 'Before', key: 'lt', django: 'lt' },
  { label: 'After', key: 'gt', django: 'gt' },
  { label: 'On or before', key: 'lte', django: 'lte' },
  { label: 'On or after', key: 'gte', django: 'gte' },
  { label: 'Between', key: 'range', django: 'range' },
  { label: 'Is empty', key: 'empty', django: 'isnull' },
];

export const BOOLEAN_OPERATORS: FilterOperator[] = [
  { label: 'Is true', key: 'eq', django: 'exact' },
  { label: 'Is false', key: 'neq', django: 'exact' },
];

export const LOOKUP_OPERATORS: FilterOperator[] = [
  { label: 'Is', key: 'eq', django: 'exact' },
  { label: 'Is not', key: 'neq', django: 'ne' },
  { label: 'Is empty', key: 'empty', django: 'isnull' },
  { label: 'Is not empty', key: 'notempty', django: 'isnull' },
];

export const JSON_OPERATORS: FilterOperator[] = [
  { label: 'Contains text', key: 'json_contains_text', django: 'icontains' },
  { label: 'Has value', key: 'json_has', django: 'contains' },
  { label: 'Is empty', key: 'empty', django: 'isnull' },
  { label: 'Is not empty', key: 'notempty', django: 'isnull' },
];

/** Map from widget/field type to available operators */
export const OPERATORS_BY_TYPE: Record<string, FilterOperator[]> = {
  text: TEXT_OPERATORS,
  email: TEXT_OPERATORS,
  phone: TEXT_OPERATORS,
  url: TEXT_OPERATORS,
  textarea: TEXT_OPERATORS,
  number: NUMBER_OPERATORS,
  currency: NUMBER_OPERATORS,
  date: DATE_OPERATORS,
  timestamp: DATE_OPERATORS,
  boolean: BOOLEAN_OPERATORS,
  select: LOOKUP_OPERATORS,
  lookup: LOOKUP_OPERATORS,
  readonly: TEXT_OPERATORS,
  json: JSON_OPERATORS,
};

/** All allowed Django lookup suffixes — used for validation */
export const ALLOWED_DJANGO_LOOKUPS = new Set([
  'exact', 'iexact', 'contains', 'icontains', 'startswith', 'endswith',
  'gt', 'gte', 'lt', 'lte', 'in', 'range', 'isnull', 'ne',
  'has_key', 'has_keys',
]);

/** Convert a RowColorRule operator key to its Django equivalent */
export function operatorToDjango(key: string): string {
  for (const ops of Object.values(OPERATORS_BY_TYPE)) {
    const match = ops.find((op) => op.key === key);
    if (match) return match.django;
  }
  return 'exact';
}
