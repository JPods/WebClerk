/**
 * panelColumnUtils — builds PanelColumnDef[] for any model's embedded panel.
 *
 * Two sources, in priority order:
 *   1. db.panel from the model's workbench_fields Setting (explicit columns)
 *   2. Auto-detection from the first record's keys (fallback)
 *
 * Cells format through cellFormat, as in every list.
 */
import React from 'react';
import type { DbColumnDef } from './DbColumns';
import { cellAlign, fieldLabel, formatCell, valueAt } from './cellFormat';

// ── Thumbnails ────────────────────────────────────────────────────────
// A column spec of { field: "ida_item", format: "image" } renders the item's
// thumbnail. The field supplies the identity; the format supplies the picture.
// The path segment is lowercase "item" — it must match the on-disk image
// library directory, which is case-sensitive on Linux.
const IMAGE_SIZE = 28;

function thumbnail(ida: string): React.ReactNode {
  return React.createElement('img', {
    src: `/wcapi/_image/item/${encodeURIComponent(ida)}/tn.jpg`,
    alt: '',
    loading: 'lazy',
    width: IMAGE_SIZE,
    height: IMAGE_SIZE,
    style: { width: IMAGE_SIZE, height: IMAGE_SIZE, objectFit: 'contain',
             borderRadius: 3, display: 'block' },
    // the endpoint answers with a placeholder rather than 404, so this only
    // fires if the server is unreachable
    onError: (e: React.SyntheticEvent<HTMLImageElement>) => {
      (e.currentTarget as HTMLImageElement).style.visibility = 'hidden';
    },
  });
}

// ── Types matching DbFieldSpec from setting.py ───────────────────────────

interface DbFieldSpec {
  field: string;
  width?: number;
  align?: 'left' | 'center' | 'right';
  visible?: boolean;
  format?: 'currency' | 'percent' | 'date' | 'number' | 'json' | 'phone' | 'masked' | 'image';
}

// Width hints by field name
const WIDTH_BY_NAME: Record<string, number> = {
  id: 50, ida: 70, status: 80,
  total: 90, price: 90, cost: 90, amount: 90,
  phone: 110, email: 150,
};

// Fields to skip in auto-detection
const SKIP_FIELDS = new Set([
  'id', 'uuid', 'version', 'is_archived',
  'search_vector', 'security_level', 'health_rating',
  'metadata', 'prefs', 'refs', 'config',
]);

// ── Build from DbFieldSpec (db.panel Setting) ────────────────────────────

type Rec = Record<string, unknown>;

export function buildColumnsFromSpecs(specs: DbFieldSpec[]): DbColumnDef<Rec>[] {
  return specs
    .filter((s) => s.visible !== false)
    .map((s) => {
      const image = String(s.format) === 'image';
      return {
        key: s.field,
        label: image ? '' : fieldLabel(s.field).replace(/_/g, ' '),
        width: s.width ?? WIDTH_BY_NAME[s.field],
        align: cellAlign(s.field, { format: s.format, align: s.align }),
        // An image column: the field supplies the identity, the format the picture.
        render: image
          ? (r: Rec) => { const v = valueAt(r, s.field); return v == null || v === '' ? null : thumbnail(String(v)); }
          : (r: Rec) => formatCell(valueAt(r, s.field), s.field, { format: s.format }),
      } satisfies DbColumnDef<Rec>;
    });
}

// ── Build from record keys (auto-detection fallback) ─────────────────────

export function buildColumnsFromRecord(record: Rec, maxCols = 6): DbColumnDef<Rec>[] {
  return Object.keys(record)
    .filter((k) => !SKIP_FIELDS.has(k))
    .slice(0, maxCols)
    .map((field) => ({
      key: field,
      label: field.replace(/_/g, ' '),
      width: WIDTH_BY_NAME[field],
      align: cellAlign(field, {}, record[field]),
      render: (r: Rec) => formatCell(r[field], field),
    }));
}
