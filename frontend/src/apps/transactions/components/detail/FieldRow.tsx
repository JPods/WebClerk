/* LastChecked: 2026-08-02 | WhereUsed: UiDetail | WhoCreated: Claude */
import React, { useState } from 'react';
import { formatDt, formatField } from '@/utils/fieldFormatters';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Resolve a dot-notation field path (e.g., "config.ship_to.company") from a record */
export function getNestedValue(data: any, path: string): unknown {
  if (!data || !path) return undefined;
  return path.split('.').reduce((obj, key) => obj?.[key], data);
}

/** Format epoch ms or ISO string to readable date */
export function formatDate(val: unknown): string {
  if (val == null) return '—';
  let d: Date;
  if (typeof val === 'number') {
    // Epoch ms (> 1e12) or epoch seconds (< 1e12)
    d = new Date(val > 1e12 ? val : val * 1000);
  } else if (typeof val === 'string') {
    d = new Date(val);
  } else {
    return String(val);
  }
  if (isNaN(d.getTime())) return String(val);
  return formatDt(val, 'date');
}

/** Fields that should be formatted as dates */
export const DATE_FIELDS = new Set(['dt_created', 'dt_modified', 'dt_needed', 'Date Ord', 'Need By']);

/** Convert any date value to YYYY-MM-DD for <input type="date"> */
function toISODate(val: unknown): string {
  if (val == null) return '';
  let d: Date;
  if (typeof val === 'number') {
    d = new Date(val > 1e12 ? val : val * 1000);
  } else if (typeof val === 'string') {
    if (/^\d{4}-\d{2}-\d{2}$/.test(val)) return val;
    d = new Date(val);
  } else {
    return '';
  }
  if (isNaN(d.getTime())) return '';
  return d.toISOString().slice(0, 10);
}

/** Fields that should be formatted as phone numbers */
const PHONE_FIELDS = new Set(['phone', 'phone_cell', 'fax', 'number']);

/** Detect format type from field name */
function detectFormatType(field: string, label: string): string | null {
  const fl = field.toLowerCase();
  const ll = label.toLowerCase();
  if (PHONE_FIELDS.has(fl) || fl.includes('phone') || fl.includes('fax') || ll === 'phone' || ll === 'fax') return 'phone';
  if (fl === 'email' || fl.includes('email') || ll === 'email') return 'email';
  if (fl === 'zip' || fl === 'postal_code' || ll === 'zip') return 'zip';
  return null;
}

// ---------------------------------------------------------------------------
// Label styles
// ---------------------------------------------------------------------------

// Label style convention: select=blue, action=green, search=bold, readonly=italic, editable=normal
// Colors from company prefs.layout.label_styles, with dark mode variants
export const LABEL_STYLES: Record<string, { light: string; dark: string; fontWeight?: number; fontStyle?: string }> = {
  select:   { light: '#1e40af', dark: '#60a5fa' },
  action:   { light: '#166534', dark: '#4ade80' },
  search:   { light: '#64748b', dark: '#94a3b8', fontWeight: 700 },
  readonly: { light: '#94a3b8', dark: '#64748b', fontStyle: 'italic' },
  editable: { light: '#64748b', dark: '#94a3b8' },
};

export const useLabelStyle = (fieldType?: string) => {
  // Check both Tailwind dark class AND DataBrowser data-theme attribute
  const isDark = document.documentElement.classList.contains('dark')
    || !!document.querySelector('[data-theme="dark"]');
  const style = LABEL_STYLES[fieldType || 'editable'] || LABEL_STYLES.editable;
  return {
    color: isDark ? style.dark : style.light,
    fontWeight: style.fontWeight,
    fontStyle: style.fontStyle as any,
  };
};

// ---------------------------------------------------------------------------
// FieldRow component
// ---------------------------------------------------------------------------

export interface FieldRowProps {
  field: string;
  label: string;
  data: any;
  isEditing: boolean;
  options?: string[];
  fieldType?: string;  // select | action | search | readonly | editable
  help?: string;       // Shift+hover shows Alice's field help
  onChange: (field: string, value: unknown) => void;
}

const FieldRow: React.FC<FieldRowProps> = ({ field, label, data, isEditing, options, fieldType, help, onChange }) => {
  const [showHelp, setShowHelp] = useState(false);
  const val = field.includes('.') ? getNestedValue(data, field) : data?.[field];

  // Label click: Shift=help, Cmd=copy path, Cmd+Shift=behavior override
  const handleLabelClick = (e: React.MouseEvent) => {
    if ((e.metaKey || e.ctrlKey) && !e.shiftKey) {
      // Cmd/Ctrl+click → copy field path to clipboard
      e.preventDefault();
      e.stopPropagation();
      navigator.clipboard.writeText(field).catch(() => {});
      return;
    }
    if (e.shiftKey && !(e.metaKey || e.ctrlKey)) {
      // Shift+click → field help (if available)
      e.preventDefault();
      e.stopPropagation();
      if (help) setShowHelp(prev => !prev);
      return;
    }
  };
  const isDate = field.startsWith('dt_') || DATE_FIELDS.has(field) || DATE_FIELDS.has(label);
  const fmtType = detectFormatType(field, label);
  const displayVal = val == null ? '—'
    : isDate ? formatDate(val)
    : fmtType ? formatField(val, fmtType, field) || '—'
    : typeof val === 'object' ? (val as any)?.name || (val as any)?.display_name || (val as any)?.ida || JSON.stringify(val)
    : String(val);
  // Derive field type: explicit > has options > calculated fields always readonly
  const resolvedType = fieldType || (options ? 'select' : 'editable');
  const labelStyle = useLabelStyle(resolvedType);
  const isClickable = resolvedType === 'select' || resolvedType === 'action' || resolvedType === 'search';
  // Show field path: always as title tooltip, visible subscript when data-show-paths is set
  const pathDisplay = field;

  return (
    <div className="flex items-baseline gap-2 py-0.5 relative group" data-field-path={field}>
      {/* For select fields in edit mode: label IS the select */}
      {isEditing && options ? (
        <>
          <select
            value={val || ''}
            onChange={(e) => onChange(field, e.target.value)}
            className="text-[10px] font-semibold bg-transparent border-none cursor-pointer outline-none"
            style={{ ...labelStyle, fontSize: 'inherit', padding: 0 }}
            title={`${label} → ${pathDisplay}`}
            onMouseEnter={(e) => { if (e.shiftKey && help) setShowHelp(true); }}
            onMouseLeave={() => setShowHelp(false)}
          >
            <option value="">{label}</option>
            {options.map(o => <option key={o} value={o}>{o.split('|')[0]}</option>)}
          </select>
          {showHelp && help && (
            <div className="absolute left-20 top-0 z-50 bg-slate-800 text-white text-[10px] px-2 py-1 rounded shadow-lg max-w-64 whitespace-normal leading-relaxed">
              {help}
            </div>
          )}
        </>
      ) : (
      <>
      <span
        className={`text-[10px] font-medium w-16 shrink-0 text-right ${isClickable ? 'hover:underline cursor-pointer' : ''}`}
        style={labelStyle}
        title={`${label} → ${pathDisplay}  |  Cmd+click: copy path`}
        onMouseDown={(e) => { if (e.shiftKey) e.preventDefault(); }}
        onClick={handleLabelClick}
        onMouseEnter={(e) => { if (e.shiftKey && help) setShowHelp(true); }}
        onMouseLeave={() => setShowHelp(false)}
        onMouseMove={(e) => { if (!e.shiftKey) setShowHelp(false); else if (help) setShowHelp(true); }}
      >{label}</span>
      {showHelp && help && (
        <div className="absolute left-20 top-0 z-50 bg-slate-800 text-white text-[10px] px-2 py-1 rounded shadow-lg max-w-64 whitespace-normal leading-relaxed">
          {help}
        </div>
      )}
      {isEditing ? (
        <input
          type={isDate ? 'date' : 'text'}
          value={isDate ? toISODate(val) : (displayVal === '—' ? '' : displayVal)}
          onChange={(e) => onChange(field, e.target.value)}
          className="flex-1 text-xs px-2 py-0.5 rounded"
          style={{ border: '1px solid var(--db-border, #cbd5e1)', background: 'var(--db-surface-alt, #fff)', color: 'var(--db-text, #1e293b)' }}
          title={pathDisplay}
          data-source={pathDisplay}
        />
      ) : (
        <span className="flex-1 text-xs" style={{ color: 'var(--db-text, #1e293b)' }} title={pathDisplay}>{typeof displayVal === 'string' ? displayVal.split('|')[0] : displayVal}</span>
      )}
      </>
      )}
    </div>
  );
};

export default FieldRow;
