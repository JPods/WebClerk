// Utility to create a blank record matching WC3 CoreModel, BaseModel, and model_name
import { BaseModelFields } from '../apps/utils/kanban/taskFormTypes';

export function createBlankRecord(modelName: string, fields: string[]): BaseModelFields & { model_name: string } {
  // Default values for CoreModelFields
  const coreDefaults = {
    id: null,
    uuid: null,
    ida: '',
    dt_created: Date.now(),
    dt_modified: Date.now(),
    version: 1,
    is_active: true,
  };

  // Default values for BaseModelFields
  const baseDefaults = {
    metadata: {},
    refs: {},
    prefs: {},
    comments: {},
    health_rating: null,
  };

  // Helper to guess default by field name/type
  function guessDefault(field: string) {
    // Common dict/object fields
    if (["metadata", "refs", "prefs", "comments"].includes(field)) return {};
    // Common numeric fields
    if (["version", "health_rating", "price"].includes(field)) return 0;
    // Common boolean fields
    if (["is_active"].includes(field)) return true;
    // Common date fields
    if (["dt_created", "dt_modified", "dt_start", "dt_deadline", "dt_completed", "dt_expected"].includes(field)) return Date.now();
    // Common id fields
    if (["id", "actor_id", "projectId"].includes(field)) return null;
    // UUID
    if (field === "uuid") return null;
    // Default string
    return '';
  }

  // Fill in all model fields with sensible defaults
  const record: any = { ...coreDefaults, ...baseDefaults, model_name: modelName };
  fields.forEach(f => {
    if (!(f in record)) {
      record[f] = guessDefault(f);
    }
  });
  return record;
}
