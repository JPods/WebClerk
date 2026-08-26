/* LastChecked: 2026-08-16 | WhereUsed: UiDetail | WhoCreated: Claude */
import React from 'react';
import FieldRow from './FieldRow';
import { getNestedValue } from './FieldRow';
import CardRenderer from '@/components/cards/CardRenderer';
import type { CardSpec } from '@/components/cards';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CustSearchProps {
  open: boolean;
  query: string;
  results: any[];
  searching: boolean;
  inputRef: React.RefObject<HTMLInputElement | null>;
  onToggle: (open: boolean) => void;
  onSearch: (query: string) => void;
  onSelect: (cust: any) => void;
}

export interface HeaderRendererProps {
  section: any;
  data: any;
  isEditing: boolean;
  modelName: string;
  onChange: (field: string, value: unknown) => void;
  custSearch?: CustSearchProps;
  /** Named card specs from layout.card */
  cardSpecs?: Record<string, CardSpec>;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/** Render header — supports card-based layout, three-column layout, and rows layout */
const HeaderRenderer: React.FC<HeaderRendererProps> = ({ section, data, isEditing, onChange, custSearch, cardSpecs }) => {

  // ── Card-based layout (new: header.cards references named card specs) ──
  if (section.header?.cards && cardSpecs) {
    const cardNames: string[] = section.header.cards;
    const resolvedCards = cardNames
      .map((name: string) => cardSpecs[name])
      .filter(Boolean);

    if (resolvedCards.length > 0) {
      return (
        <div className={`grid grid-cols-${resolvedCards.length} gap-3`}>
          {resolvedCards.map((spec, idx) => (
            <CardRenderer
              key={spec.title || idx}
              spec={spec}
              data={data}
              isEditing={isEditing}
              onChange={onChange}
            />
          ))}
        </div>
      );
    }
  }

  // ── Three-column layout (legacy: section.columns inline) ──
  if (section.layout === 'three-column' && section.columns) {
    const colCount = section.columns.length;
    // Weight columns: use col.weight if specified, otherwise auto-weight by field count
    const weights = section.columns.map((col: any) => {
      if (col.weight) return col.weight;
      const fieldCount = (col.fields || []).length;
      return Math.max(fieldCount, 2);  // minimum 2 so link-only columns aren't crushed
    });
    const templateCols = weights.map((w: number) => `${w}fr`).join(' ');
    return (
      <div className="grid gap-3" style={{ gridTemplateColumns: colCount <= 1 ? '1fr' : templateCols }}>
        {section.columns.map((col: any, colIdx: number) => (
          <div key={colIdx} className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-3">
            <div className="text-xs font-bold text-slate-700 dark:text-slate-200 mb-2 border-b border-slate-100 dark:border-slate-700 pb-1 flex items-center gap-2">
              <span>{col.title}</span>
              {col.title_ida && data?.customer && (
                <span className="font-mono text-slate-400 dark:text-slate-500 font-normal text-[10px]">
                  #{typeof data.customer === 'object' ? data.customer.id : data.customer}
                </span>
              )}
              {col.title_ida && isEditing && custSearch && !custSearch.open && (
                <button
                  type="button"
                  className="ml-auto text-[10px] text-slate-400 hover:text-blue-600 px-1 py-0.5 rounded hover:bg-blue-50"
                  title="Search customers"
                  onClick={() => custSearch.onToggle(true)}
                >🔍</button>
              )}
              {col.title_ida && isEditing && custSearch?.open && (
                <div className="ml-auto relative">
                  <input
                    ref={custSearch.inputRef}
                    type="text"
                    value={custSearch.query}
                    onChange={(e) => custSearch.onSearch(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Escape') { custSearch.onToggle(false); custSearch.onSearch(''); } }}
                    placeholder="bil,jame or 612..."
                    className="text-[11px] px-2 py-0.5 w-44 border border-blue-400 rounded bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  {custSearch.searching && <span className="absolute right-2 top-0.5 text-[10px] text-slate-400">...</span>}
                  {custSearch.results.length > 0 && (
                    <div className="absolute top-6 left-0 w-96 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded shadow-lg z-50 max-h-60 overflow-y-auto">
                      {custSearch.results.map((c: any) => (
                        <button
                          key={c.id}
                          type="button"
                          className="w-full text-left px-3 py-2 text-[11px] hover:bg-blue-50 dark:hover:bg-slate-700 border-b border-slate-100 dark:border-slate-700 last:border-0"
                          onClick={() => custSearch.onSelect(c)}
                        >
                          <div className="flex items-baseline gap-2">
                            <span className="font-medium text-slate-900 dark:text-white">{c.company || c.display_name || `#${c.id}`}</span>
                            <span className="text-slate-400 font-mono text-[10px]">#{c.id}</span>
                          </div>
                          <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">
                            {[c.attention, c.phone, c.address_full || c.email].filter(Boolean).join(' · ')}
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                  {custSearch.query.length >= 2 && !custSearch.searching && custSearch.results.length === 0 && (
                    <div className="absolute top-6 left-0 w-52 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded shadow-lg z-50 px-3 py-2 text-[11px] text-slate-400">
                      No customers found
                    </div>
                  )}
                </div>
              )}
            </div>
            {col.fields.map((f: any) => (
              <FieldRow
                key={f.field}
                field={f.field}
                label={f.label}
                data={data}
                isEditing={isEditing}
                options={f.options}
                fieldType={f.type}
                help={f.help}
                onChange={onChange}
              />
            ))}
            {col.action_summary && (
              <div className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-700">
                <div
                  className="text-[10px] font-medium text-slate-400 cursor-pointer hover:text-blue-600 hover:underline"
                  onClick={() => {
                    const actionId = data?.actions?.items?.[0]?.id;
                    if (actionId) {
                      window.open(`/action?id=${actionId}`, '_blank');
                    }
                  }}
                  title="Click to open action record"
                >Next Action</div>
                <div className="text-xs text-slate-600 dark:text-slate-300">
                  {data?.actions?.items?.[0]
                    ? `${typeof data.actions.items[0].action === 'object' ? data.actions.items[0].action?.en : data.actions.items[0].action} — ${data.actions.items[0].status || 'pending'}`
                    : '—'}
                </div>
                {data?.actions?.items?.[0]?.assigned_to && (
                  <div className="text-[10px] text-slate-400 mt-0.5">
                    {data.actions.items[0].assigned_to}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    );
  }

  // ── Default rows layout ──
  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-3 space-y-2">
      {(section.rows || []).map((row: any, rowIdx: number) => (
        <div
          key={rowIdx}
          className="grid gap-3"
          style={{ gridTemplateColumns: `repeat(${row.cols}, 1fr)` }}
        >
          {row.fields.map((field: string, fieldIdx: number) => {
            const val = field.includes('.') ? getNestedValue(data, field) : data?.[field];
            const label = row.label?.[fieldIdx] || field.split('.').pop() || field;
            const displayVal = val == null ? '—'
              : typeof val === 'object' ? (val as any)?.name || (val as any)?.display_name || JSON.stringify(val)
              : String(val);
            return (
              <div key={field} className="flex flex-col gap-0.5">
                <label className="text-[10px] font-medium text-slate-500 dark:text-slate-400">{label}</label>
                {isEditing ? (
                  <input
                    type="text"
                    value={displayVal === '—' ? '' : displayVal}
                    onChange={(e) => onChange(field, e.target.value)}
                    className="text-xs px-2 py-1 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                  />
                ) : (
                  <span className="text-xs text-slate-900 dark:text-white">{displayVal}</span>
                )}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
};

export default HeaderRenderer;
