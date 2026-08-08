/* LastChecked: 2026-08-02 | WhereUsed: TransactionDetail | WhoCreated: Claude */
import React, { useState } from 'react';

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
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

/** Fields that should be formatted as dates */
export const DATE_FIELDS = new Set(['dt_created', 'dt_modified', 'dt_needed', 'Date Ord', 'Need By']);

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
  const isDark = document.documentElement.classList.contains('dark');
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
  const isDate = field.startsWith('dt_') || DATE_FIELDS.has(field) || DATE_FIELDS.has(label);
  const displayVal = val == null ? '—'
    : isDate ? formatDate(val)
    : typeof val === 'object' ? (val as any)?.name || (val as any)?.display_name || (val as any)?.ida || JSON.stringify(val)
    : String(val);
  // Derive field type: explicit > has options > calculated fields always readonly
  const resolvedType = fieldType || (options ? 'select' : 'editable');
  const labelStyle = useLabelStyle(resolvedType);
  const isClickable = resolvedType === 'select' || resolvedType === 'action' || resolvedType === 'search';
  return (
    <div className="flex items-baseline gap-2 py-0.5 relative">
      {/* For select fields in edit mode: label IS the select */}
      {isEditing && options ? (
        <>
          <select
            value={val || ''}
            onChange={(e) => onChange(field, e.target.value)}
            className="text-[10px] font-semibold bg-transparent border-none cursor-pointer outline-none"
            style={{ ...labelStyle, fontSize: 'inherit', padding: 0 }}
            title={help || label}
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
          type="text"
          value={displayVal === '—' ? '' : displayVal}
          onChange={(e) => onChange(field, e.target.value)}
          className="flex-1 text-xs px-2 py-0.5 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
        />
      ) : (
        <span className="flex-1 text-xs text-slate-900 dark:text-white">{typeof displayVal === 'string' ? displayVal.split('|')[0] : displayVal}</span>
      )}
      </>
      )}
    </div>
  );
};

export default FieldRow;
