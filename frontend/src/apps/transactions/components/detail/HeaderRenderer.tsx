/* LastChecked: 2026-11-05 | WhereUsed: DbForm | WhoCreated: Claude */
import React from 'react';
import { communicationField } from '@/utils/communicationFields';
import { selectOptionsOf } from '@/utils/fieldBehaviorsOf';
import FieldRow, { lockedFieldsForRecord } from './FieldRow';
import { getNestedValue } from './FieldRow';
import CardRenderer from '@/components/cards/CardRenderer';
import type { CardSpec } from '@/components/cards';
import { WIDGETS } from '@/components/widgets';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CustSearchProps {
  /** customer or vendor — what the search finds and sets. */
  party: 'customer' | 'vendor';
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
  /** Field behaviors from Setting config.behaviors — drives label styles and select options */
  behaviors?: Record<string, any>;
  /** A field kept in another record (a contact's phone, address, domain, email; an org's from
   *  its primary contact) opens that record's card instead of an input (Bill, 2026-11-03). */
  onOpenField?: (field: string, el: HTMLElement) => void;
  /** Which fields open a card; the model's communication fields when not given. */
  opensField?: (field: string) => boolean;
  /** A contact whose org search finds nothing makes the org (Bill, 2026-10-16). */
  onCreateOrg?: (field: string, typed: string) => void | Promise<void>;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/** Render header — supports card-based layout, three-column layout, and rows layout */
const HeaderRenderer: React.FC<HeaderRendererProps> = ({ section, data, isEditing, modelName, onChange, custSearch, cardSpecs, behaviors = {}, onOpenField, opensField, onCreateOrg }) => {
  const opens = opensField ?? ((field: string) => !!communicationField(modelName, field));

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
              behaviors={behaviors}
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
        {section.columns.map((col: any, colIdx: number) => {
          // Detect single-widget columns — render widget directly, no FieldRow
          const isSingleWidget = col.fields?.length === 1 && col.fields[0].type && WIDGETS[col.fields[0].type];
          const widgetField = isSingleWidget ? col.fields[0] : null;
          const widgetType = widgetField?.type;
          const Widget = widgetType ? WIDGETS[widgetType] : null;
          const widgetVal = widgetField ? getNestedValue(data, widgetField.field) : undefined;

          return (
          <div
            key={colIdx}
            className="rounded-lg p-3"
            style={{ background: 'var(--db-surface, #fff)', border: '1px solid var(--db-border, #dee2e6)' }}
            data-component="HeaderRenderer"
            data-model={modelName}
            data-column={col.title}
            data-source={`setting.config.layout.form.default.sections[${0}].columns[${colIdx}]`}
          >
            <div className="font-bold mb-2 pb-1 flex items-center gap-2 db-font-sm"
              style={{ color: 'var(--db-text, #212529)', borderBottom: '1px solid var(--db-border-light, #e9ecef)' }}>
              <span>{col.title}</span>
              {col.title_ida && custSearch && data?.[custSearch.party] && (
                <span className="font-mono font-normal db-font-xs" style={{ color: 'var(--db-text-dim)' }}>
                  {custSearch.party === 'vendor' ? 'vendor ' : ''}#{typeof data[custSearch.party] === 'object' ? data[custSearch.party].id : data[custSearch.party]}
                </span>
              )}
              {col.title_ida && isEditing && custSearch && !custSearch.open && (
                <button
                  type="button"
                  className="ml-auto db-font-xs text-slate-400 hover:text-blue-600 px-1 py-0.5 rounded hover:bg-blue-50"
                  title={`Search ${custSearch.party}s`}
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
                    className="db-font-sm px-2 py-0.5 w-44 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                    style={{ border: '1px solid var(--db-accent)', background: 'var(--db-input-bg, #fff)', color: 'var(--db-text, #212529)' }}
                  />
                  {custSearch.searching && <span className="absolute right-2 top-0.5 db-font-xs text-slate-400">...</span>}
                  {custSearch.results.length > 0 && (
                    <div className="absolute top-6 left-0 w-96 rounded shadow-lg z-50 max-h-60 overflow-y-auto"
                      style={{ background: 'var(--db-surface, #fff)', border: '1px solid var(--db-border, #dee2e6)' }}>
                      {custSearch.results.map((c: any) => (
                        <button
                          key={c.id}
                          type="button"
                          className="w-full text-left px-3 py-2 db-font-sm last:border-0"
                          style={{ borderBottom: '1px solid var(--db-border-light, #e9ecef)' }}
                          onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--db-row-hover)')}
                          onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                          onClick={() => custSearch.onSelect(c)}
                        >
                          <div className="flex items-baseline gap-2">
                            <span className="font-medium" style={{ color: 'var(--db-text)' }}>{c.company || c.display_name || `#${c.id}`}</span>
                            <span className="font-mono db-font-xs" style={{ color: 'var(--db-text-dim)' }}>#{c.id}</span>
                          </div>
                          <div className="db-font-xs mt-0.5" style={{ color: 'var(--db-text-muted)' }}>
                            {[c.attention, c.phone, c.address_full || c.email].filter(Boolean).join(' · ')}
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                  {custSearch.query.length >= 2 && !custSearch.searching && custSearch.results.length === 0 && (
                    <div className="absolute top-6 left-0 w-52 rounded shadow-lg z-50 px-3 py-2 db-font-sm"
                      style={{ background: 'var(--db-surface, #fff)', border: '1px solid var(--db-border, #dee2e6)', color: 'var(--db-text-muted)' }}>
                      No customers found
                    </div>
                  )}
                </div>
              )}
            </div>
            {/* An item's picture (layout column type item_image) */}
            {col.type === 'item_image' && data?.ida ? (
              <div className="flex justify-center items-center h-full">
                <img
                  src={`/wcapi/_image/item/${encodeURIComponent(data.ida)}/md.jpg`}
                  alt={data.ida}
                  style={{ maxWidth: '100%', maxHeight: 240, objectFit: 'contain', borderRadius: 4 }}
                  onError={(e: any) => { e.target.onerror = null; e.target.src = '/images/no-image.svg'; }}
                />
              </div>
            ) : isSingleWidget && Widget ? (
              <Widget
                name={widgetField!.field}
                value={widgetVal}
                onChange={(v: unknown) => onChange(widgetField!.field, v)}
                disabled={!isEditing}
                record={data}
              />
            ) : col.fields.map((f: any) => {
              // The behavior names the type when the field def doesn't; a select's options are the
              // definition's list and only that (Bill, 2026-11-05) — a layout carries none.
              const beh = behaviors[f.field] || {};
              const fieldType = f.type || beh.type;
              const options = selectOptionsOf(beh);
              return (
                <FieldRow
                  key={f.field}
                  field={f.field}
                  label={(f.label === f.field && communicationField(modelName, f.field)?.label) || f.label || beh.label || f.field}
                  data={data}
                  isEditing={isEditing}
                  options={options}
                  fieldType={fieldType}
                  lookup={beh.type === 'lookup' && beh.model ? { model: beh.model, valueField: beh.value, display: beh.display } : undefined}
                  lockedFields={lockedFieldsForRecord(data)}
                  help={f.help}
                  onChange={onChange}
                  onOpen={onOpenField && opens(f.field) ? (el: HTMLElement) => onOpenField(f.field, el) : undefined}
                  onCreateOrg={onCreateOrg}
                />
              );
            })}
            {col.action_summary && (
              <div className="mt-2 pt-2" style={{ borderTop: '1px solid var(--db-border-light, #e9ecef)' }}>
                <div
                  className="db-font-xs font-medium text-slate-400 cursor-pointer hover:text-blue-600 hover:underline"
                  onClick={() => {
                    const actionId = data?.actions?.items?.[0]?.id;
                    if (actionId) {
                      window.open(`/action?id=${actionId}`, '_blank');
                    }
                  }}
                  title="Click to open action record"
                >Next Action</div>
                <div className="db-font-sm" style={{ color: 'var(--db-text, #212529)' }}>
                  {data?.actions?.items?.[0]
                    ? `${typeof data.actions.items[0].action === 'object' ? data.actions.items[0].action?.en : data.actions.items[0].action} — ${data.actions.items[0].status || 'pending'}`
                    : '—'}
                </div>
                {data?.actions?.items?.[0]?.assigned_to && (
                  <div className="db-font-xs text-slate-400 mt-0.5">
                    {data.actions.items[0].assigned_to}
                  </div>
                )}
              </div>
            )}
          </div>
          );
        })}
      </div>
    );
  }

  // ── Default rows layout ──
  return (
    <div className="rounded-lg p-3 space-y-2" style={{ background: 'var(--db-surface, #fff)', border: '1px solid var(--db-border, #dee2e6)' }}>
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
                <label className="db-font-xs font-medium" style={{ color: 'var(--db-text-muted)' }}>{label}</label>
                {isEditing ? (
                  <input
                    type="text"
                    value={displayVal === '—' ? '' : displayVal}
                    onChange={(e) => onChange(field, e.target.value)}
                    className="db-font-sm px-2 py-1 rounded"
                    style={{ border: '1px solid var(--db-input-border, #ced4da)', background: 'var(--db-input-bg, #fff)', color: 'var(--db-text, #212529)' }}
                  />
                ) : (
                  <span className="db-font-sm" style={{ color: 'var(--db-text, #212529)' }}>{displayVal}</span>
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
