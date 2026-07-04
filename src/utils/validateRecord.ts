/**
 * validateRecord — client-side validation that accumulates ALL errors.
 *
 * Generates validation rules from field_behaviors config.
 * Returns a field-keyed error dict (empty = valid).
 *
 * Pattern source: EA_Tasks validateTaskFields.4dm — collect all errors, return together.
 */

type FieldBehaviors = Record<string, Record<string, any>>;
type ValidationErrors = Record<string, string>;

/**
 * Validate a record against its field behaviors.
 * Returns empty object if valid, or {fieldName: errorMessage} for each invalid field.
 */
export function validateRecord(
  record: Record<string, unknown>,
  fieldBehaviors: FieldBehaviors,
  visibleFields: string[],
): ValidationErrors {
  const errors: ValidationErrors = {};

  for (const field of visibleFields) {
    const beh = fieldBehaviors[field];
    if (!beh) continue;

    const value = record[field];
    const isEmpty = value === null || value === undefined || value === '';

    // Required field check
    if (beh.required && isEmpty) {
      errors[field] = `${field} is required`;
      continue;
    }

    // Skip further validation if empty and not required
    if (isEmpty) continue;

    // Type-specific validation
    switch (beh.type) {
      case 'email':
        if (typeof value === 'string' && value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
          errors[field] = 'Invalid email format';
        }
        break;

      case 'phone':
        if (typeof value === 'string' && value && !/^[+\d\s().-]{7,}$/.test(value)) {
          errors[field] = 'Invalid phone format';
        }
        break;

      case 'url':
        if (typeof value === 'string' && value && !/^https?:\/\/.+/.test(value)) {
          errors[field] = 'URL must start with http:// or https://';
        }
        break;

      case 'number':
      case 'currency':
        if (typeof value === 'string' && value && isNaN(Number(value))) {
          errors[field] = 'Must be a number';
        }
        break;

      case 'select':
        if (beh.choices && Array.isArray(beh.choices)) {
          const validValues = beh.choices.map((c: any) =>
            typeof c === 'string' ? c : c.value ?? c.key ?? c
          );
          if (!validValues.includes(value)) {
            errors[field] = `Must be one of: ${validValues.slice(0, 5).join(', ')}`;
          }
        }
        break;
    }

    // Max length check
    if (beh.max_length && typeof value === 'string' && value.length > beh.max_length) {
      errors[field] = `Maximum ${beh.max_length} characters (currently ${value.length})`;
    }
  }

  return errors;
}

/**
 * Check if a validation result has any errors.
 */
export function hasErrors(errors: ValidationErrors): boolean {
  return Object.keys(errors).length > 0;
}

/**
 * Format all errors into a single message for display.
 */
export function formatErrors(errors: ValidationErrors): string {
  return Object.entries(errors)
    .map(([field, msg]) => `${field}: ${msg}`)
    .join('\n');
}
