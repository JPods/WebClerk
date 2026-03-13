/**
 * Fragment-based search utilities for wc2-parity search behavior.
 *
 * Comma-separated fragments with AND logic across fragments, OR across fields.
 * Prefix a fragment with "@" for contains (substring) matching.
 * Default (no prefix) uses startsWith (prefix) matching.
 *
 * Examples:
 *   "acm, 102"     → both must match (startsWith) somewhere on the record
 *   "@west"         → substring match (contains)
 *   "acm, @west"   → "acm" startsWith AND "west" contains
 */

export interface SearchFragment {
  /** Lowercased, trimmed search value */
  value: string;
  /** "startswith" = prefix match (default), "contains" = substring match (@ prefix) */
  mode: "startswith" | "contains";
}

/**
 * Parse a raw search input string into typed fragments.
 *
 * - Splits on comma (with optional surrounding whitespace)
 * - "@" prefix → contains mode (@ is stripped from value)
 * - No prefix → startswith mode
 * - Empty/whitespace-only fragments are dropped
 * - Values are lowercased for case-insensitive matching
 */
export function parseFragments(input: string): SearchFragment[] {
  if (!input || !input.trim()) return [];
  return input
    .split(/,\s*/)
    .map((s) => s.trim())
    .filter(Boolean)
    .map((raw) => {
      if (raw.startsWith("@") && raw.length > 1) {
        return { value: raw.slice(1).toLowerCase(), mode: "contains" as const };
      }
      return { value: raw.toLowerCase(), mode: "startswith" as const };
    });
}

/**
 * Collect all searchable string values from a row, including refs.keywords.
 * Returns individual values (not joined) so matchers can apply per-value logic.
 */
function collectSearchableValues(row: Record<string, unknown>): string[] {
  const values: string[] = [];

  // Scalar fields
  for (const [, val] of Object.entries(row)) {
    if (val === null || val === undefined) continue;
    if (typeof val === "string" || typeof val === "number" || typeof val === "boolean") {
      values.push(String(val).toLowerCase());
    }
  }

  // refs.keywords (string or string[])
  const refs = row.refs;
  if (refs && typeof refs === "object" && !Array.isArray(refs)) {
    const kw = (refs as Record<string, unknown>).keywords;
    if (typeof kw === "string") {
      values.push(kw.toLowerCase());
    } else if (Array.isArray(kw)) {
      for (const k of kw) {
        if (typeof k === "string") {
          values.push(k.toLowerCase());
        }
      }
    }
  }

  return values;
}

/**
 * Test whether a single fragment matches any of the searchable values.
 *
 * - startswith mode: at least one value starts with the fragment
 * - contains mode: at least one value contains the fragment
 *
 * Keywords (from refs.keywords) always use contains regardless of mode,
 * since keywords are individual tokens rather than full field values.
 */
function fragmentMatchesAnyValue(
  fragment: SearchFragment,
  scalarValues: string[],
  keywordValues: string[],
): boolean {
  // Check scalar fields with the fragment's mode
  for (const v of scalarValues) {
    if (fragment.mode === "startswith") {
      if (v.startsWith(fragment.value)) return true;
    } else {
      if (v.includes(fragment.value)) return true;
    }
  }

  // Keywords always use contains (they're individual tokens)
  for (const kw of keywordValues) {
    if (kw.includes(fragment.value)) return true;
  }

  return false;
}

/**
 * Check if a row matches ALL fragments (AND logic).
 *
 * Each fragment is tested against all scalar fields + refs.keywords (OR).
 * All fragments must match somewhere on the record (AND).
 */
export function matchesFragments(
  row: Record<string, unknown>,
  fragments: SearchFragment[],
): boolean {
  if (!fragments.length) return true;

  const allValues = collectSearchableValues(row);

  // Separate keywords for distinct matching behavior
  const refs = row.refs;
  const keywordValues: string[] = [];
  const scalarValues: string[] = [];

  if (refs && typeof refs === "object" && !Array.isArray(refs)) {
    const kw = (refs as Record<string, unknown>).keywords;
    if (typeof kw === "string") {
      keywordValues.push(kw.toLowerCase());
    } else if (Array.isArray(kw)) {
      for (const k of kw) {
        if (typeof k === "string") keywordValues.push(k.toLowerCase());
      }
    }
  }

  // Everything else is scalar
  for (const [key, val] of Object.entries(row)) {
    if (key === "refs" || val === null || val === undefined) continue;
    if (typeof val === "string" || typeof val === "number" || typeof val === "boolean") {
      scalarValues.push(String(val).toLowerCase());
    }
  }

  return fragments.every((frag) =>
    fragmentMatchesAnyValue(frag, scalarValues, keywordValues),
  );
}

/**
 * Backward-compatible wrapper: parse + match in one call.
 * For use in components that just need a simple filter predicate.
 */
export function rowMatchesSearch(
  row: Record<string, unknown>,
  searchInput: string,
): boolean {
  const fragments = parseFragments(searchInput);
  return matchesFragments(row, fragments);
}

/**
 * Backward-compatible: parse comma-separated terms as flat string array.
 * Preserves @ prefix in the value for components that send raw strings to the backend.
 * @deprecated Use parseFragments() for typed fragment matching.
 */
export function parseSearchTerms(input: string): string[] {
  if (!input || !input.trim()) return [];
  return input
    .split(/,\s*/)
    .map((t) => t.trim().toLowerCase())
    .filter((t) => t.length > 0);
}
