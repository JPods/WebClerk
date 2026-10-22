/**
 * The update body for a record: only the top-level fields that differ from the record as
 * loaded, plus `id` (saveRecord moves it to the path) and `version` (the door's stale-edit guard).
 *
 * The door refuses keys that are not fields (fix #1, 2026-09-25), so an update never echoes
 * the loaded record back — no model_name, uuid, dt_*, ida — and never resends a field the
 * person did not touch. A JSON field that changed goes whole; the door merges it.
 * A field the person emptied goes as the door's clear, `{ mode: 'delete' }`: the door
 * reads a bare null as "not sent" (Bill, 2026-10-17: a cleared customer stayed linked).
 */
export function changedFields(
  loaded: Record<string, unknown> | null | undefined,
  edited: Record<string, unknown>,
): Record<string, unknown> {
  const body: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(edited)) {
    if (loaded && JSON.stringify(loaded[key]) === JSON.stringify(value)) continue;
    body[key] = value === null && loaded?.[key] != null ? { mode: 'delete' } : value;
  }
  if (loaded?.id != null) body.id = loaded.id;
  if (loaded?.version != null) body.version = loaded.version;
  return body;
}
