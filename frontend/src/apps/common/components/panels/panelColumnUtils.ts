/**
 * panelColumnUtils — builds PanelColumnDef[] for any model's embedded panel.
 *
 * Two sources, in priority order:
 *   1. db.panel from the model's workbench_fields Setting (explicit columns)
 *   2. Auto-detection from the first record's keys (fallback)
 *
 * Format heuristics apply in both paths: currency for total/price/amount,
 * date for dt_*, phone for phone fields, etc.
 */
import type { PanelColumnDef } from './PanelTable';
import { formatField, type FieldType } from '@/utils/fieldFormatters';

// ── Types matching DbFieldSpec from setting.py ───────────────────────────

interface DbFieldSpec {
  field: string;
  width?: number;
  align?: 'left' | 'center' | 'right';
  visible?: boolean;
  format?: 'currency' | 'percent' | 'date' | 'number' | 'json' | 'phone' | 'masked';
}

// ── Format heuristics by field name ──────────────────────────────────────

const FORMAT_BY_NAME: Record<string, FieldType> = {
  total: 'currency', price: 'currency', cost: 'currency', amount: 'currency',
  subtotal: 'currency', balance: 'currency', msrp: 'currency', unit_price: 'currency',
  phone: 'phone', fax: 'phone', mobile: 'phone',
  email: 'email',
  zip: 'zip', postal_code: 'zip',
};

function guessFormat(field: string): FieldType | undefined {
  if (FORMAT_BY_NAME[field]) return FORMAT_BY_NAME[field];
  if (field.startsWith('dt_')) return 'date';
  if (field.endsWith('_price') || field.endsWith('_cost') || field.endsWith('_amount')) return 'currency';
  if (field.endsWith('_phone') || field.endsWith('_fax')) return 'phone';
  return undefined;
}

// Width hints by field name
const WIDTH_BY_NAME: Record<string, string> = {
  id: 'w-[50px]', ida: 'w-[70px]', status: 'w-[80px]',
  total: 'w-[90px]', price: 'w-[90px]', cost: 'w-[90px]', amount: 'w-[90px]',
  phone: 'w-[110px]', email: 'w-[150px]',
};

// Fields to skip in auto-detection
const SKIP_FIELDS = new Set([
  'id', 'uuid', 'version', 'is_deleted', 'is_archived', 'is_locked',
  'search_vector', 'security_level', 'health_rating',
  'metadata', 'prefs', 'refs', 'config',
]);

// ── Build from DbFieldSpec (db.panel Setting) ────────────────────────────

export function buildColumnsFromSpecs(specs: DbFieldSpec[]): PanelColumnDef<Record<string, unknown>>[] {
  return specs
    .filter((s) => s.visible !== false)
    .map((s) => {
      const fmt = s.format as FieldType | undefined ?? guessFormat(s.field);
      const align = s.align === 'right' ? 'text-right' : s.align === 'center' ? 'text-center' : '';
      const width = s.width ? `w-[${s.width}px]` : (WIDTH_BY_NAME[s.field] ?? '');
      const flex = width ? '' : 'min-w-[60px] flex-1';

      return {
        key: s.field,
        label: s.field.replace(/_/g, ' '),
        cellClassName: `truncate ${width} ${flex} ${align} `.trim(),
        render: (r: Record<string, unknown>) => {
          const val = r[s.field];
          if (val == null || val === '') return '—';
          if (fmt) return formatField(val, fmt, s.field);
          return String(val);
        },
      } satisfies PanelColumnDef<Record<string, unknown>>;
    });
}

// ── Build from record keys (auto-detection fallback) ─────────────────────

export function buildColumnsFromRecord(record: Record<string, unknown>, maxCols = 6): PanelColumnDef<Record<string, unknown>>[] {
  const keys = Object.keys(record)
    .filter((k) => !SKIP_FIELDS.has(k))
    .slice(0, maxCols);

  return keys.map((field) => {
    const fmt = guessFormat(field);
    const width = WIDTH_BY_NAME[field] ?? '';
    const flex = width ? '' : 'min-w-[60px] flex-1';
    const align = fmt === 'currency' || fmt === 'number' || fmt === 'percent' ? 'text-right' : '';

    return {
      key: field,
      label: field.replace(/_/g, ' '),
      cellClassName: `truncate ${width} ${flex} ${align} `.trim(),
      render: (r: Record<string, unknown>) => {
        const val = r[field];
        if (val == null || val === '') return '—';
        if (fmt) return formatField(val, fmt, field);
        if (typeof val === 'object') return JSON.stringify(val).slice(0, 60);
        return String(val);
      },
    } satisfies PanelColumnDef<Record<string, unknown>>;
  });
}
