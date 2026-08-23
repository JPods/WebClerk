/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * modelDefaults.ts — Per-model default values (r25 source of truth)
 *
 * When creating a new record of a given model, these defaults are merged
 * into the blank record before the form opens. Overrides the generic
 * fieldDefaults for specific models.
 *
 * Structure:
 *   MODEL_DEFAULTS[modelKey] = { field: value, ... }
 *
 * Dynamic overrides from wc3 are merged on top at runtime via configSlice.
 * Admins can edit these in the r25 settings UI; changes are synced back to wc3.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ModelDefaultEntry {
  /** Display label for admin UI */
  label: string;
  /** Default field values applied when creating a new record */
  defaults: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Per-model defaults
// ---------------------------------------------------------------------------

export const MODEL_DEFAULTS: Record<string, ModelDefaultEntry> = {
  // --- Transactions ------------------------------------------------------
  order: {
    label: 'Sales Order',
    defaults: {
      terms: 'On Order',
      due_date_period: 1,
      price_level: 'retail',
      priority: 'standard',
      status: 'active',
    },
  },
  invoice: {
    label: 'Invoice',
    defaults: {
      terms: 'Due on Receipt',
      due_date_period: 30,
      price_level: 'retail',
      priority: 'standard',
      status: 'active',
    },
  },
  proposal: {
    label: 'Proposal',
    defaults: {
      terms: 'On Order',
      due_date_period: 30,
      price_level: 'retail',
      priority: 'standard',
      status: 'active',
    },
  },
  purchase: {
    label: 'Purchase Order',
    defaults: {
      terms: 'Net 30',
      due_date_period: 30,
      price_level: 'wholesale',
      priority: 'standard',
      status: 'active',
    },
  },
  requisition: {
    label: 'Requisition',
    defaults: {
      terms: '',
      priority: 'standard',
      status: 'active',
    },
  },
  work_order: {
    label: 'Work Order',
    defaults: {
      terms: '',
      priority: 'standard',
      status: 'active',
    },
  },

  // --- Entities ----------------------------------------------------------
  customer: {
    label: 'Customer',
    defaults: {
      terms: 'On Order',
      price_level: 'retail',
      status: 'active',
    },
  },
  vendor: {
    label: 'Vendor',
    defaults: {
      terms: 'Net 30',
      price_level: 'wholesale',
      status: 'active',
    },
  },
  contact: {
    label: 'Contact',
    defaults: {
      status: 'active',
    },
  },

  // --- Products ----------------------------------------------------------
  item: {
    label: 'Item',
    defaults: {
      status: 'active',
      price_level: 'retail',
    },
  },
};

// ---------------------------------------------------------------------------
// Accessors
// ---------------------------------------------------------------------------

/**
 * Get default values for a model. Returns empty object if no defaults defined.
 */
export function getModelDefaults(modelKey: string): Record<string, unknown> {
  return MODEL_DEFAULTS[modelKey]?.defaults ?? {};
}

/**
 * Get a specific default value for a model + field.
 */
export function getModelDefault(modelKey: string, field: string): unknown {
  return MODEL_DEFAULTS[modelKey]?.defaults?.[field];
}

/**
 * All model keys that have defaults defined.
 */
export function modelKeysWithDefaults(): string[] {
  return Object.keys(MODEL_DEFAULTS);
}
