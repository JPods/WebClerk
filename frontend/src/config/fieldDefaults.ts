/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * fieldDefaults.ts — Field-level behavior rules (r25 source of truth)
 *
 * Defines how fields are initialized, displayed, and defaulted across the app.
 * These rules apply universally unless a model-specific override exists in
 * modelDefaults.ts.
 *
 * Key rule: Any epoch-ms datetime field that is null, undefined, or 0 is
 * treated as "now" at display/create time. The original null/0 is preserved
 * in the record — only the *displayed* value is substituted.
 *
 * Backed up to wc3 via the config sync mechanism (see useAppConfig).
 */

// ---------------------------------------------------------------------------
// Datetime fallback
// ---------------------------------------------------------------------------

/** Field name patterns that trigger the "null/0 → now" display behavior. */
export const DT_FALLBACK_FIELDS = [
  'dt_start',
  'dt_created',
  'dt_modified',
  'dt_deadline',
  'dt_expected',
  'dt_completed',
  'dt_end',
  'dt_due',
  'dt_shipped',
  'dt_received',
  'dt_ordered',
  'dt_invoiced',
  'dt_approved',
  'dt_submitted',
  'dt_verified',
  'dt_synced',
] as const;

/** Prefix check — any field starting with `dt_` gets the fallback. */
export const DT_FIELD_PREFIX = 'dt_';

/**
 * Return `Date.now()` when the value is null, undefined, or 0.
 * For display only — never mutate the persisted record with this.
 *
 * Usage:
 *   <span>{formatEpochMs(applyDtFallback(record.dt_start))}</span>
 */
export function applyDtFallback(value: number | null | undefined): number {
  return !value || value === 0 ? Date.now() : value;
}

/**
 * For a create/new record: stamp the field with now if it's empty.
 * Unlike applyDtFallback (display-only), this is meant to *set* the value
 * in the data being saved.
 */
export function stampDtIfEmpty(value: number | null | undefined): number {
  return !value || value === 0 ? Date.now() : value;
}

/**
 * Check if a field name is a datetime field that should get the fallback.
 */
export function isDtField(fieldName: string): boolean {
  return fieldName.startsWith(DT_FIELD_PREFIX);
}

/**
 * Apply dt defaults to all dt_* fields in a record (for new record creation).
 * Returns a shallow copy with stamped values.
 */
export function applyDtDefaults<T extends Record<string, unknown>>(record: T): T {
  const result = { ...record };
  for (const key of Object.keys(result)) {
    if (isDtField(key)) {
      const val = result[key];
      if (val === null || val === undefined || val === 0) {
        (result as Record<string, unknown>)[key] = Date.now();
      }
    }
  }
  return result;
}

// ---------------------------------------------------------------------------
// String field defaults
// ---------------------------------------------------------------------------

/** Fields that should default to empty string rather than null. */
export const STRING_DEFAULT_FIELDS = [
  'name',
  'title',
  'description',
  'ida',
  'display_name',
  'email',
  'phone',
  'status',
] as const;

// ---------------------------------------------------------------------------
// JSON envelope defaults (mirror wc3 CoreModel / BaseModel shapes)
// ---------------------------------------------------------------------------

export const ENVELOPE_DEFAULTS: Record<string, () => unknown> = {
  metadata: () => ({}),
  refs: () => ({ keywords: [], tags: [], links: {}, categories: [], related_ids: [] }),
  prefs: () => ({ userdefined: {} }),
  comments: () => ({ public: '', process: '', partner: '', notes: [] }),
  actions: () => ({}),
};

/**
 * Apply envelope defaults to a record being created.
 * Only sets values for keys that are null/undefined.
 */
export function applyEnvelopeDefaults<T extends Record<string, unknown>>(record: T): T {
  const result = { ...record };
  for (const [field, factory] of Object.entries(ENVELOPE_DEFAULTS)) {
    if (result[field] === null || result[field] === undefined) {
      (result as Record<string, unknown>)[field] = factory();
    }
  }
  return result;
}

// ---------------------------------------------------------------------------
// Core field defaults (for new record creation)
// ---------------------------------------------------------------------------

export function coreRecordDefaults(): Record<string, unknown> {
  const now = Date.now();
  return {
    id: null,
    uuid: null,
    ida: '',
    dt_created: now,
    dt_modified: now,
    version: 1,
    is_active: true,
    health_rating: 0,
  };
}
