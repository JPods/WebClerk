/**
 * useSchemaFormats — loads PJPV schema field metadata once per session.
 *
 * The Pydantic schemas on the backend declare widget type, precision,
 * and other display metadata on every field.  This hook fetches that
 * catalog from /wcapi/_pjpv_fields/ and provides a flat lookup map
 * so getDefaultFieldSpec() can prefer schema-declared formats over
 * name-guessing.
 *
 * The catalog is fetched once (session-cached in wcapi.ts) and never
 * re-fetched.
 */
import { useEffect, useState } from 'react';
import {
  getPjpvFieldsCatalog,
  flattenPjpvCatalog,
  type PjpvFieldMeta,
} from '@/api/wcapi';

export type SchemaFormatMap = Record<string, PjpvFieldMeta>;

/**
 * Returns a flat map of field paths to their schema metadata.
 * Keys are both "envelope.field" (e.g. "totals.total") and bare
 * field names (e.g. "total") for top-level fallback.
 *
 * Returns empty {} while loading — callers fall through to name-guessing.
 */
export function useSchemaFormats(): SchemaFormatMap {
  const [formats, setFormats] = useState<SchemaFormatMap>({});

  useEffect(() => {
    let cancelled = false;
    getPjpvFieldsCatalog().then((catalog) => {
      if (!cancelled) {
        setFormats(flattenPjpvCatalog(catalog));
      }
    });
    return () => { cancelled = true; };
  }, []);

  return formats;
}
