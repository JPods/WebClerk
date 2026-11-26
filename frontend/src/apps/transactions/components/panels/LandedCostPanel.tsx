/* LastChecked: 2026-11-25 | WhereUsed: LineCardRenderer (receipt) | WhoCreated: Claude */
/**
 * A receipt line's landed costs (Bill, 2026-11-25: "We can show these in the detail dialog for
 * each receipt_line. Too much data for a line." / "If users edit in the dialog, it should affect
 * the line."). Labels are the stored names so users learn the data ("For users to learn the data,
 * we need consistency"): freight, duty, handling, vat, landed, method, unallocated.
 *
 * Bill's ruling, same day: a value typed on a line changes only that line; to recalculate, the
 * person presses Spread on the receipt's toolbar. Nothing spreads on its own (Bill, 2026-11-26:
 * "switch the auto spreading to a button. So users see what we are doing"). Per charge this shows
 * the receipt's amount (allocations.<comp>), the basis Spread uses (allocations.method.<comp>:
 * value | quantity | weight | manual — Spread leaves a manual charge alone, every share is
 * typed), this line's landed (cost.landed.<comp>, a plain number the person owns),
 * and what the lines leave unapplied (the receipt's totals.unallocated.<comp>, the server's; it may
 * be negative). Journalize asks before posting an unallocated amount.
 * Server is truth: once anything is unsaved, unallocated and the landed unit are the last save's.
 */
import React from 'react';

export const LANDED_COMPONENTS = ['freight', 'duty', 'handling', 'vat'] as const;
export type LandedComponent = typeof LANDED_COMPONENTS[number];
export const LANDED_BASES = ['value', 'quantity', 'weight', 'manual'] as const;

const num = (v: unknown): number => {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
};

/** The line with its landed share of `comp` set to `value` (an emptied input is 0). The whole
 *  cost.landed travels: a line save merges `cost` one level deep ({**held, **sent},
 *  save_line_processing._copy_line_fields), so cost.landed is replaced, not merged. */
export function withLanded(line: any, comp: LandedComponent, value: number): any {
  const landed = { ...(line?.cost?.landed || {}), [comp]: value };
  return { ...line, cost: { ...(line?.cost || {}), landed }, _dirty: true };
}

/** Per-unit landed cost from the server's line totals: discounted unit + each share ÷ qty
 *  (4 places per share, as totals_compute.landed_layer_cost carries the layer). Null without qty. */
export function landedUnit(line: any): number | null {
  const qty = num(line?.quantity?.active);
  const totals = line?.totals;
  if (!qty || !totals || typeof totals !== 'object') return null;
  const shares = totals.landed || {};
  const perUnit = LANDED_COMPONENTS.reduce((s, k) => s + Math.round((num(shares[k]) / qty) * 10000) / 10000, 0);
  return Math.round((num(totals.discounted_unit) + perUnit) * 10000) / 10000;
}

export interface LandedCostPanelProps {
  /** The selected receipt line, or null when none is selected. */
  line: any | null;
  /** The receipt's allocations (freight, duty, handling, vat, method). */
  allocations: any;
  /** The receipt's totals.unallocated as the server last saved it. */
  unallocated: any;
  /** Line edits (cost.landed). */
  canEditLine: boolean;
  /** Header edits (allocations.method). */
  canEditMethod: boolean;
  /** True when the receipt has unsaved changes: unallocated and the landed unit are the last save's. */
  changed: boolean;
  onLanded: (comp: LandedComponent, value: number) => void;
  onMethod: (comp: LandedComponent, basis: string) => void;
  formatMoney: (v: number) => string;
}

const cell: React.CSSProperties = { padding: '2px 6px', borderBottom: '1px solid var(--wc-border-light, #f1f5f9)' };
const head: React.CSSProperties = { ...cell, fontWeight: 600, color: 'var(--wc-text-muted, #64748b)', textAlign: 'left' };
const input: React.CSSProperties = {
  fontSize: 'inherit', background: 'var(--wc-surface, #fff)', border: '1px solid var(--wc-border, #cbd5e1)', borderRadius: 3,
};

const LandedCostPanel: React.FC<LandedCostPanelProps> = ({
  line, allocations, unallocated, canEditLine, canEditMethod, changed, onLanded, onMethod, formatMoney,
}) => {
  const method = (allocations && typeof allocations.method === 'object' && allocations.method) || {};
  const landed = line?.cost?.landed || {};
  const left = (unallocated && typeof unallocated === 'object') ? unallocated : {};
  const unit = line ? landedUnit(line) : null;
  const lineEditable = canEditLine && !!line && !line._removed;

  return (
    <div style={{ fontSize: 'inherit' }}>
      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead>
          <tr>
            <th style={head}></th>
            <th style={{ ...head, textAlign: 'right' }} title="The receipt's charge: allocations.<comp>">allocations</th>
            <th style={head} title="The basis Workflow → Spread uses for this charge: allocations.method.<comp>">method</th>
            <th style={{ ...head, textAlign: 'right' }} title="This line's share: cost.landed.<comp>. Typing changes this line only.">landed</th>
            <th style={{ ...head, textAlign: 'right' }} title="The receipt's charge minus the lines' landed, at the last save: totals.unallocated.<comp>">unallocated</th>
          </tr>
        </thead>
        <tbody>
          {LANDED_COMPONENTS.map((comp) => {
            const open = num(left[comp]);
            return (
              <tr key={comp}>
                <td style={{ ...cell, fontWeight: 600 }}>{comp}</td>
                <td style={{ ...cell, textAlign: 'right' }}>{formatMoney(num(allocations?.[comp]))}</td>
                <td style={cell}>
                  {canEditMethod ? (
                    <select value={method[comp] || 'value'} onChange={(e) => onMethod(comp, e.target.value)}
                      data-wc-field={`allocations.method.${comp}`} style={input}>
                      {LANDED_BASES.map((b) => <option key={b} value={b}>{b}</option>)}
                    </select>
                  ) : (method[comp] || 'value')}
                </td>
                <td style={{ ...cell, textAlign: 'right' }}>
                  {lineEditable ? (
                    <input type="number" step="0.01" value={landed[comp] ?? 0}
                      data-wc-field={`cost.landed.${comp}`}
                      onChange={(e) => onLanded(comp, e.target.value === '' ? 0 : Number(e.target.value))}
                      style={{ ...input, width: 90, textAlign: 'right' }} />
                  ) : (line ? formatMoney(num(landed[comp])) : '')}
                </td>
                <td style={{ ...cell, textAlign: 'right', color: open !== 0 ? 'var(--wc-warning, #b45309)' : undefined, fontWeight: open !== 0 ? 600 : undefined }}>
                  {formatMoney(open)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div style={{ display: 'flex', gap: 12, padding: '4px 6px', alignItems: 'baseline', flexWrap: 'wrap' }}>
        {!line && <span style={{ color: 'var(--wc-text-muted, #64748b)' }}>Select a line to see its landed.</span>}
        {line && (
          <span title="totals.discounted_unit + each totals.landed share ÷ quantity.active — what the layer carries">
            landed unit: <strong>{unit === null ? '—' : unit.toFixed(4)}</strong>
          </span>
        )}
        <span style={{ color: 'var(--wc-text-muted, #64748b)' }}>Workflow → Spread re-spreads every charge by its method.</span>
        {changed && (
          <span style={{ fontStyle: 'italic', color: 'var(--wc-text-muted, #64748b)' }}>
            unallocated and landed unit are the last save's; Save to recompute
          </span>
        )}
      </div>
    </div>
  );
};

export default LandedCostPanel;
