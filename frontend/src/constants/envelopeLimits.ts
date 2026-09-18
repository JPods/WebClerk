/**
 * envelopeLimits — hard limits for all JSON envelope fields.
 *
 * Mirrors backend constraints in:
 *   common/schemas/envelopes.py
 *   apps/core/services/save_field_assignment.py
 *   webclerk3_api/settings.py
 *
 * Backend is the law. Frontend is the courtesy.
 * These limits prevent users from hitting 400 errors by catching
 * violations before the request leaves the browser.
 *
 * Established: 2026-09-02
 */

// ── userdefined ──────────────────────────────────────────────────────
export const USERDEFINED_MAX_KEYS = 20;
export const USERDEFINED_KEY_MAX_LEN = 64;
export const USERDEFINED_VALUE_MAX_LEN = 255;

// ── tags ─────────────────────────────────────────────────────────────
export const TAGS_MAX_COUNT = 50;
export const TAG_MAX_LEN = 64;

// ── comments ─────────────────────────────────────────────────────────
export const COMMENT_TEXT_MAX_LEN = 1000;
export const COMMENT_FIELD_MAX_LEN = 255;     // by, source, ts
export const COMMENT_CHANNEL_MAX_COUNT = 500;

// ── saved searches ───────────────────────────────────────────────────
export const SAVED_SEARCH_MAX_COUNT = 25;
export const SAVED_SEARCH_FIELDS_MAX = 20;
export const SAVED_SEARCH_FILTERS_MAX_KEYS = 10;

// ── saved addresses ──────────────────────────────────────────────────
export const SAVED_ADDRESSES_MAX_COUNT = 10;

// ── notifications ────────────────────────────────────────────────────
export const NOTIFICATIONS_MAX_KEYS = 20;

// ── audit trail ──────────────────────────────────────────────────────
export const AUDIT_TRAIL_MAX_ENTRIES = 500;
export const AUDIT_DETAIL_MAX_SIZE = 2048;    // bytes

// ── metadata lists ───────────────────────────────────────────────────
export const EROSION_MAX_COUNT = 50;
export const SMALL_STING_MAX_COUNT = 100;
export const TEMP_MAX_COUNT = 50;

// ── structural ───────────────────────────────────────────────────────
export const JSON_MAX_DEPTH = 8;
export const STRING_FIELD_MAX_LEN = 10000;
export const MAX_PAYLOAD_BYTES = 2 * 1024 * 1024;  // 2 MB — matches settings.py

// ── binary detection ─────────────────────────────────────────────────
const BASE64_PATTERN = /^(?:[A-Za-z0-9+/]{4}){10,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/;
const DATA_URI_PATTERN = /^data:[^;]+;base64,/;
const BINARY_MIN_LEN = 500;

/**
 * Return true if a string looks like base64 or a data URI.
 * Documents go through Document.path — binary in other fields is rejected.
 */
export function looksLikeBinary(value: string): boolean {
  if (value.length < BINARY_MIN_LEN) return false;
  if (DATA_URI_PATTERN.test(value)) return true;
  if (BASE64_PATTERN.test(value.slice(0, 200).trim())) return true;
  return false;
}
