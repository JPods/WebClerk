/* LastChecked: 2026-08-02 | WhereUsed: UiDetail | WhoCreated: Claude */
import React, { useState } from 'react';
import { formatDt, formatField } from '@/utils/fieldFormatters';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Resolve a dot-notation field path with optional [N] leaf extraction.
 *
 * "config.ship_to.company"  → data.config.ship_to.company
 * "assigned_to[0]"          → first value of data.assigned_to (object or array)
 * "comments.process[0]"     → first value of data.comments.process
 *
 * [N] on an object returns Object.values(obj)[N].
 * [N] on an array returns arr[N].
 * Result is always a scalar — if the leaf is still an object, recurse to first scalar.
 */
export function getNestedValue(data: any, path: string): unknown {
  if (!data || !path) return undefined;

  // Split off trailing [N] index
  const bracketMatch = path.match(/^(.+)\[(\d+)\]$/);
  const cleanPath = bracketMatch ? bracketMatch[1] : path;
  const leafIndex = bracketMatch ? parseInt(bracketMatch[2], 10) : null;

  const val = cleanPath.split('.').reduce((obj: any, key: string) => obj?.[key], data);

  if (leafIndex === null) return val;
  if (val == null) return undefined;

  // Extract the Nth value from object or array
  const values = Array.isArray(val) ? val : typeof val === 'object' ? Object.values(val) : [val];
  let leaf = values[leafIndex];

  // If the leaf is still an object, drill to first scalar
  while (leaf != null && typeof leaf === 'object' && !Array.isArray(leaf)) {
    const inner = Object.values(leaf);
    if (inner.length === 0) break;
    leaf = inner[0];
  }

  return leaf;
}

/** Extract first scalar value from an object/array. Shows value only, no key. */
function _firstScalar(val: any): string {
  if (val == null) return '—';
  if (typeof val !== 'object') return String(val);
  const values = Array.isArray(val) ? val : Object.values(val);
  for (const v of values) {
    if (v == null) continue;
    if (typeof v !== 'object') return String(v);
    return _firstScalar(v);
  }
  return '—';
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

// Label style convention:
//   readonly/system = italic (system-managed, admin edits via JSON)
//   action          = green  (phone/email/address/url — click launches)
//   select          = blue   (dropdown)
//   search          = bold   (reserved for toolbar search)
//   editable        = normal
// Colors from company prefs.layout.label_styles, with dark mode variants
export const LABEL_STYLES: Record<string, { light: string; dark: string; fontWeight?: number; fontStyle?: string }> = {
  select:   { light: '#1e40af', dark: '#60a5fa' },
  action:   { light: '#166534', dark: '#4ade80' },
  search:   { light: '#64748b', dark: '#94a3b8', fontWeight: 700 },
  readonly: { light: '#94a3b8', dark: '#64748b', fontStyle: 'italic' },
  editable: { light: '#64748b', dark: '#94a3b8' },
};

// Map behavior types to label style categories
const BEHAVIOR_TO_LABEL: Record<string, string> = {
  // System-managed — italic
  readonly: 'readonly', hidden: 'readonly',
  timestamp: 'readonly',    // dt_created, dt_modified, etc.
  // Actionable — green (click launches something)
  email: 'action', phone: 'action', address: 'action',
  url: 'action', geo: 'action',
  // Select — blue
  select: 'select', lookup: 'select',
  // Search — bold (toolbar, not field labels)
  search: 'search',
  // Everything else (text, textarea, number, i18n, json, json-tree, currency,
  // boolean, date, percentage, editor) → editable (normal gray)
};

// Detect label style from field name or label — universal conventions
// These fire regardless of model or behavior config
// Checked against both field leaf name AND label prop
const _NAME_TO_TYPE: Record<string, string> = {
  phone: 'action', phone_cell: 'action', fax: 'action',
  number: 'action',   // phones.*.number
  email: 'action',
  address: 'action', address_full: 'action', full_address: 'action',
  website: 'action', url: 'action',
};

/** Resolve label style from behavior type. */
export function labelStyleForBehavior(behaviorType?: string): string {
  if (!behaviorType) return 'editable';
  return BEHAVIOR_TO_LABEL[behaviorType] || 'editable';
}

/** Get label style object — callable from loops (not a hook). */
export function getLabelStyle(fieldType?: string): { color: string; fontWeight?: number; fontStyle?: string } {
  const isDark = document.documentElement.classList.contains('dark')
    || !!document.querySelector('[data-theme="dark"]');
  const style = LABEL_STYLES[fieldType || 'editable'] || LABEL_STYLES.editable;
  return {
    color: isDark ? style.dark : style.light,
    fontWeight: style.fontWeight,
    fontStyle: style.fontStyle as any,
  };
}

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
  const [copyNote, setCopyNote] = useState<string | null>(null);
  const val = (field.includes('.') || field.includes('[')) ? getNestedValue(data, field) : data?.[field];

  // Label click: plain=action launch, Shift=help, Cmd=copy path
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
    // Plain click on action labels — launch tel/mailto/maps + copy to clipboard
    const leafN = field.split('.').pop()?.replace(/\[\d+\]$/, '') || '';
    const actionKey = leafN || label;  // check both
    const strVal = typeof val === 'string' ? val : _firstScalar(val);
    if (!strVal || strVal === '—') return;
    if (['phone', 'phone_cell', 'fax', 'number'].includes(actionKey) || label === 'phone') {
      navigator.clipboard.writeText(strVal).catch(() => {});
      setCopyNote(`Copied ${strVal}`);
      setTimeout(() => setCopyNote(null), 3000);
    } else if (actionKey === 'email' || label === 'email') {
      navigator.clipboard.writeText(strVal).catch(() => {});
      setCopyNote('Copied — opening email');
      setTimeout(() => setCopyNote(null), 2000);
      window.open(`mailto:${strVal}`, '_blank');
    } else if (['address', 'address_full', 'full_address'].includes(actionKey) || label === 'address') {
      navigator.clipboard.writeText(strVal).catch(() => {});
      setCopyNote('Copied — opening maps');
      setTimeout(() => setCopyNote(null), 2000);
      window.open(`https://maps.apple.com/?q=${encodeURIComponent(strVal)}`, '_blank');
    } else if (['website', 'url'].includes(actionKey)) {
      const href = strVal.startsWith('http') ? strVal : `https://${strVal}`;
      window.open(href, '_blank');
    }
  };
  const isDate = field.startsWith('dt_') || DATE_FIELDS.has(field) || DATE_FIELDS.has(label)
    || fieldType === 'date' || fieldType === 'timestamp';
  const fmtType = detectFormatType(field, label);
  const displayVal = val == null ? '—'
    : isDate ? formatDate(val)
    : fmtType ? formatField(val, fmtType, field) || '—'
    : typeof val === 'object' ? (val as any)?.name || (val as any)?.display_name || (val as any)?.ida || _firstScalar(val)
    : String(val);
  // Derive field type: explicit > name convention > has options > editable
  // Check both field path leaf AND label for actionable field detection
  const leafName = field.split('.').pop()?.replace(/\[\d+\]$/, '') || field;
  const nameType = _NAME_TO_TYPE[leafName] || _NAME_TO_TYPE[label];
  const resolvedType = fieldType || nameType || (options ? 'select' : 'editable');
  const labelStyle = useLabelStyle(resolvedType);
  const isClickable = resolvedType === 'select' || resolvedType === 'action' || resolvedType === 'search';
  // Show field path: always as title tooltip, visible subscript when data-show-paths is set
  const pathDisplay = field;

  return (
    <div className="flex items-baseline gap-2 py-0.5 relative group" data-field-path={field}>
      {/* Label always visible — value area changes based on edit mode and field type */}
      <span
        className={`db-font-xs font-medium shrink-0 text-right truncate ${isClickable ? 'hover:underline cursor-pointer' : ''}`}
        style={{ ...labelStyle, width: 110, maxWidth: 110 }}
        title={`${label} → ${pathDisplay}  |  Cmd+click: copy path`}
        onMouseDown={(e) => { if (e.shiftKey) e.preventDefault(); }}
        onClick={handleLabelClick}
        onMouseEnter={(e) => { if (e.shiftKey && help) setShowHelp(true); }}
        onMouseLeave={() => setShowHelp(false)}
        onMouseMove={(e) => { if (!e.shiftKey) setShowHelp(false); else if (help) setShowHelp(true); }}
      >{label}</span>
      {showHelp && help && (
        <div className="absolute left-20 top-0 z-50 db-font-xs px-2 py-1 rounded shadow-lg max-w-64 whitespace-normal leading-relaxed"
          style={{ background: 'var(--db-surface-alt, #1e293b)', color: 'var(--db-text, #fff)', border: '1px solid var(--db-border, #334155)' }}>
          {help}
        </div>
      )}
      {copyNote && (
        <div className="absolute left-20 top-0 z-50 db-font-xs px-2 py-1 rounded shadow-lg whitespace-nowrap"
          style={{ background: '#166534', color: '#fff', border: '1px solid #22c55e' }}>
          {copyNote}
        </div>
      )}
      {options ? (
        <select
          value={typeof val === 'object' ? _firstScalar(val) : (val || '')}
          onChange={(e) => onChange(field, e.target.value)}
          className="flex-1 db-font-sm px-2 py-0.5 rounded cursor-pointer min-w-0"
          style={{ border: '1px solid var(--db-border, #cbd5e1)', background: 'var(--db-surface-alt, #fff)', color: 'var(--db-text, #1e293b)', maxWidth: 240 }}
          title={pathDisplay}
          data-source={pathDisplay}
        >
          <option value="">—</option>
          {options.map(o => <option key={o} value={o}>{o.split('|')[0]}</option>)}
        </select>
      ) : isEditing ? (
        <input
          type={isDate ? 'date' : 'text'}
          value={isDate ? toISODate(val) : (displayVal === '—' ? '' : displayVal)}
          onChange={(e) => onChange(field, e.target.value)}
          className="flex-1 db-font-sm px-2 py-0.5 rounded min-w-0"
          style={{ border: '1px solid var(--db-border, #cbd5e1)', background: 'var(--db-surface-alt, #fff)', color: 'var(--db-text, #1e293b)', maxWidth: 240 }}
          title={pathDisplay}
          data-source={pathDisplay}
        />
      ) : (
        <span className="flex-1 db-font-sm min-w-0 truncate" style={{ color: 'var(--db-text, #1e293b)', maxWidth: 240 }} title={pathDisplay}>{typeof displayVal === 'string' ? displayVal.split('|')[0] : displayVal}</span>
      )}
    </div>
  );
};

export default FieldRow;
