/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
// TypeScript interface for Audit model based on webclerk3 Django model

export interface Audit {
  id?: number;
  created_at?: string;
  updated_at?: string;
  purpose?: string;
  name?: string;
  conflicts?: any; // JSONField
  changes?: any; // JSONField
  actions?: any; // JSONField
  recommendations?: any; // JSONField
  rating?: number;
  is_completed?: boolean;
  priority?: number;
}

// Field labels - using exact field names as requested
export const AUDIT_FIELD_LABELS: Record<keyof Audit, string> = {
  id: 'id',
  created_at: 'created_at',
  updated_at: 'updated_at',
  purpose: 'purpose',
  name: 'name',
  conflicts: 'conflicts',
  changes: 'changes',
  actions: 'actions',
  recommendations: 'recommendations',
  rating: 'rating',
  is_completed: 'is_completed',
  priority: 'priority',
};