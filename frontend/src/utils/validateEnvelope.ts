/**
 * validateEnvelope — client-side validation for JSON envelope fields.
 *
 * Catches constraint violations before the request leaves the browser.
 * Backend enforces the same limits with hard 400 rejections.
 *
 * Usage:
 *   const errors = validateEnvelope(record);
 *   if (errors.length > 0) { show errors; return; }
 *
 * Established: 2026-09-02
 */

import {
  USERDEFINED_MAX_KEYS,
  USERDEFINED_KEY_MAX_LEN,
  USERDEFINED_VALUE_MAX_LEN,
  TAGS_MAX_COUNT,
  TAG_MAX_LEN,
  COMMENT_TEXT_MAX_LEN,
  COMMENT_CHANNEL_MAX_COUNT,
  SAVED_SEARCH_MAX_COUNT,
  SAVED_ADDRESSES_MAX_COUNT,
  NOTIFICATIONS_MAX_KEYS,
  looksLikeBinary,
} from '../constants/envelopeLimits';

export interface EnvelopeError {
  path: string;        // e.g. "prefs.userdefined", "comments.public"
  message: string;
}

/**
 * Validate all envelope fields on a record.
 * Returns empty array if valid.
 */
export function validateEnvelope(record: Record<string, any>): EnvelopeError[] {
  const errors: EnvelopeError[] = [];

  // ── prefs ──
  const prefs = record.prefs;
  if (prefs && typeof prefs === 'object') {
    validateUserdefined(prefs.userdefined, errors);
    validateTags(prefs.tags, errors);
    validateSearchCount(prefs.search, errors);

    // Cart prefs
    if (prefs.cart && typeof prefs.cart === 'object') {
      validateListCount(prefs.cart.saved_addresses, SAVED_ADDRESSES_MAX_COUNT, 'prefs.cart.saved_addresses', errors);
      validateDictKeyCount(prefs.cart.notifications, NOTIFICATIONS_MAX_KEYS, 'prefs.cart.notifications', errors);
    }

    // Rep/employee notifications
    if (prefs.rep?.notifications) {
      validateDictKeyCount(prefs.rep.notifications, NOTIFICATIONS_MAX_KEYS, 'prefs.rep.notifications', errors);
    }
    if (prefs.employee?.notifications) {
      validateDictKeyCount(prefs.employee.notifications, NOTIFICATIONS_MAX_KEYS, 'prefs.employee.notifications', errors);
    }
  }

  // ── comments ──
  const comments = record.comments;
  if (comments && typeof comments === 'object') {
    const general = comments.general;
    if (general && typeof general === 'object') {
      for (const channel of ['public', 'process', 'foreign'] as const) {
        validateCommentChannel(general[channel], `comments.general.${channel}`, errors);
      }
    }
  }

  // ── binary check on string fields ──
  for (const [key, value] of Object.entries(record)) {
    if (typeof value === 'string' && looksLikeBinary(value)) {
      errors.push({
        path: key,
        message: 'Binary/base64 content not allowed — use Document upload',
      });
    }
  }

  return errors;
}

// ── individual validators ────────────────────────────────────────────

function validateUserdefined(ud: any, errors: EnvelopeError[]): void {
  if (!ud || typeof ud !== 'object') return;
  const keys = Object.keys(ud);

  if (keys.length > USERDEFINED_MAX_KEYS) {
    errors.push({
      path: 'prefs.userdefined',
      message: `Custom fields exceed ${USERDEFINED_MAX_KEYS} (has ${keys.length})`,
    });
  }

  for (const key of keys) {
    if (key.length > USERDEFINED_KEY_MAX_LEN) {
      errors.push({
        path: `prefs.userdefined.${key.slice(0, 20)}`,
        message: `Key name exceeds ${USERDEFINED_KEY_MAX_LEN} characters`,
      });
    }
    const val = ud[key];
    if (typeof val === 'object' && val !== null) {
      errors.push({
        path: `prefs.userdefined.${key}`,
        message: 'Custom field values must be flat (no objects or arrays)',
      });
    }
    if (typeof val === 'string' && val.length > USERDEFINED_VALUE_MAX_LEN) {
      errors.push({
        path: `prefs.userdefined.${key}`,
        message: `Value exceeds ${USERDEFINED_VALUE_MAX_LEN} characters`,
      });
    }
  }
}

function validateTags(tags: any, errors: EnvelopeError[]): void {
  if (!Array.isArray(tags)) return;

  if (tags.length > TAGS_MAX_COUNT) {
    errors.push({
      path: 'prefs.tags',
      message: `Tags exceed ${TAGS_MAX_COUNT} (has ${tags.length})`,
    });
  }

  for (let i = 0; i < tags.length; i++) {
    const tag = tags[i];
    if (typeof tag === 'string' && tag.length > TAG_MAX_LEN) {
      errors.push({
        path: `prefs.tags[${i}]`,
        message: `Tag "${tag.slice(0, 20)}..." exceeds ${TAG_MAX_LEN} characters`,
      });
    }
  }
}

function validateSearchCount(searches: any, errors: EnvelopeError[]): void {
  if (!Array.isArray(searches)) return;
  if (searches.length > SAVED_SEARCH_MAX_COUNT) {
    errors.push({
      path: 'prefs.search',
      message: `Saved searches exceed ${SAVED_SEARCH_MAX_COUNT}`,
    });
  }
}

function validateCommentChannel(channel: any, path: string, errors: EnvelopeError[]): void {
  if (!Array.isArray(channel)) return;
  if (channel.length > COMMENT_CHANNEL_MAX_COUNT) {
    errors.push({ path, message: `Comments exceed ${COMMENT_CHANNEL_MAX_COUNT}` });
  }
  for (let i = 0; i < channel.length; i++) {
    const entry = channel[i];
    if (entry && typeof entry.text === 'string' && entry.text.length > COMMENT_TEXT_MAX_LEN) {
      errors.push({
        path: `${path}[${i}].text`,
        message: `Comment exceeds ${COMMENT_TEXT_MAX_LEN} characters`,
      });
    }
  }
}

function validateListCount(list: any, max: number, path: string, errors: EnvelopeError[]): void {
  if (Array.isArray(list) && list.length > max) {
    errors.push({ path, message: `Exceeds ${max} entries (has ${list.length})` });
  }
}

function validateDictKeyCount(dict: any, max: number, path: string, errors: EnvelopeError[]): void {
  if (dict && typeof dict === 'object' && Object.keys(dict).length > max) {
    errors.push({ path, message: `Exceeds ${max} keys` });
  }
}

/**
 * Validate a single comment text before sending.
 * Returns error message or null if valid.
 */
export function validateCommentText(text: string): string | null {
  if (text.length > COMMENT_TEXT_MAX_LEN) {
    return `Comment exceeds ${COMMENT_TEXT_MAX_LEN} characters (${text.length})`;
  }
  if (looksLikeBinary(text)) {
    return 'Binary/base64 content not allowed in comments';
  }
  return null;
}

/**
 * Validate a single tag before adding.
 * Returns error message or null if valid.
 */
export function validateTag(tag: string, currentCount: number): string | null {
  if (tag.length > TAG_MAX_LEN) {
    return `Tag exceeds ${TAG_MAX_LEN} characters`;
  }
  if (currentCount >= TAGS_MAX_COUNT) {
    return `Maximum ${TAGS_MAX_COUNT} tags reached`;
  }
  return null;
}

/**
 * Validate a userdefined key:value pair before adding.
 * Returns error message or null if valid.
 */
export function validateUserdefinedEntry(
  key: string,
  value: any,
  currentCount: number,
): string | null {
  if (key.length > USERDEFINED_KEY_MAX_LEN) {
    return `Field name exceeds ${USERDEFINED_KEY_MAX_LEN} characters`;
  }
  if (typeof value === 'object' && value !== null) {
    return 'Custom field values must be flat (no objects or arrays)';
  }
  if (typeof value === 'string' && value.length > USERDEFINED_VALUE_MAX_LEN) {
    return `Value exceeds ${USERDEFINED_VALUE_MAX_LEN} characters`;
  }
  if (currentCount >= USERDEFINED_MAX_KEYS) {
    return `Maximum ${USERDEFINED_MAX_KEYS} custom fields reached`;
  }
  return null;
}
