/**
 * The update body for a record: only the top-level fields that differ from the record as
 * loaded, plus `id` (saveRecord moves it to the path) and `version` (the door's stale-edit guard).
 *
 * The door refuses keys that are not fields (fix #1, 2026-09-25), so an update never echoes
 * the loaded record back — no model_name, uuid, dt_*, ida — and never resends a field the
 * person did not touch. A JSON field that changed goes whole; the door merges it.
 */
export function changedFields(
  loaded: Record<string, unknown> | null | undefined,
  edited: Record<string, unknown>,
): Record<string, unknown> {
  const body: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(edited)) {
    if (loaded && JSON.stringify(loaded[key]) === JSON.stringify(value)) continue;
    body[key] = value;
  }
  if (loaded?.id != null) body.id = loaded.id;
  if (loaded?.version != null) body.version = loaded.version;
  return body;
}
