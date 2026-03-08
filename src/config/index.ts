/**
 * config/index.ts — Barrel export for the configuration system
 *
 * Import from '@/config' to access field defaults, model defaults,
 * and select lists.
 */

// Field-level behavior rules
export {
  applyDtFallback,
  stampDtIfEmpty,
  isDtField,
  applyDtDefaults,
  applyEnvelopeDefaults,
  coreRecordDefaults,
  DT_FALLBACK_FIELDS,
  DT_FIELD_PREFIX,
  ENVELOPE_DEFAULTS,
  STRING_DEFAULT_FIELDS,
} from './fieldDefaults';

// Per-model default values
export {
  MODEL_DEFAULTS,
  getModelDefaults,
  getModelDefault,
  modelKeysWithDefaults,
  type ModelDefaultEntry,
} from './modelDefaults';

// Select lists
export {
  STATIC_LISTS,
  DYNAMIC_LISTS,
  SELECT_LIST_MAP,
  getSelectList,
  getSelectOptions,
  toLegacyPairs,
  editableListKeys,
  type SelectOption,
  type SelectListDef,
} from './selectLists';

// Select list sync (r25 ↔ wc3 Setting records)
export {
  fetchSelectListsFromWc3,
  fetchSelectListFromWc3,
  pushSelectListToWc3,
  pushAllSelectListsToWc3,
  mergeWc3SelectLists,
  diffSelectList,
  type SyncResult,
} from './syncSelectLists';

// Report/print definitions per model
export {
  MODEL_REPORTS,
  getReportsForModel,
  getReportsByOutputType,
  getReportsByCategory,
  getReportsForRole,
  modelKeysWithReports,
  getReportByName,
  type ReportDef,
  type ReportOutputType,
  type ReportCategory,
} from './reportLists';
