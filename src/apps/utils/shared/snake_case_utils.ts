export function to_snake(value: string): string {
  return value
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
    .replace(/([A-Z])([A-Z][a-z])/g, '$1_$2')
    .toLowerCase();
}

export function ensure_snake_keys(obj: unknown): unknown {
  if (obj === null || typeof obj !== 'object') return obj;
  if (Array.isArray(obj)) return obj.map(ensure_snake_keys);
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(obj)) {
    out[to_snake(k)] = ensure_snake_keys(v);
  }
  return out;
}

export default {
  to_snake,
  ensure_snake_keys,
};
