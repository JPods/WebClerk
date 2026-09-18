/**
 * WebClerk project-wide types — replace raw `any` with semantic types.
 *
 * JsonValue / JsonObject: any valid JSON structure.
 * WcRecord: a single record from wcapi (always has id + json envelope).
 * FieldValue: what a single field can hold in the UI layer.
 * WcList: a page of records from getRecords().
 */

// ── JSON primitives ────────────────────────────────────────────────
export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonObject | JsonArray;
export type JsonObject = { [key: string]: JsonValue };
export type JsonArray = JsonValue[];

// ── Record types ───────────────────────────────────────────────────
/** A single record returned by wcapi. Every record has at least id and json. */
export interface WcRecord {
  id: number;
  uuid?: string;
  json: JsonObject;
  model_name?: string;
  [key: string]: JsonValue | undefined;
}

/** What a UI field can hold — broader than JSON to include Files and Dates. */
export type FieldValue = JsonValue | Date | File | undefined;

// ── API response shapes ────────────────────────────────────────────
/** A page of records from getRecords(). */
export interface WcList {
  model_name: string;
  results: WcRecord[];
  total: number;
  limit?: number | null;
  offset?: number;
}

/** A single record from getRecord(). */
export interface WcDetail {
  model_name: string;
  record: WcRecord;
  related?: Record<string, WcRecord[]>;
}
