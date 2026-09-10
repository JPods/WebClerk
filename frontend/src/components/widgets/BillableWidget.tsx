/**
 * BillableWidget — form/detail widget for action.config.billable
 *
 * Renders billing configuration: who is billed, rate, estimates vs actuals,
 * product set, invoice linkage, Alice learning signal.
 *
 * Data shape: ActionBillable schema from action.py
 */
import React, { useCallback, useMemo, useState, useEffect } from "react";
import type { WidgetProps } from "./types";
import { getRecords, getTimeBillingItems } from "@/api/wcapi";
import { OrgLookup } from "./OrgLookupWidget";

interface ActionBillable {
  customer_id?: number | null;
  contact_id?: number | null;
  company?: string;
  attention?: string;
  is_billable?: boolean;
  rate?: number | null;
  rate_unit?: string;
  currency?: string;
  skill_category?: string;
  activity?: string;
  hours_estimated?: number | null;
  hours_actual?: number | null;
  total_estimated?: number | null;
  total_actual?: number | null;
  variance_pct?: number | null;
  product_set?: number[];
  invoice_id?: number | null;
  invoice_line?: number | null;
  estimate_source?: string | null;
  estimate_confidence?: number | null;
}

const RATE_UNITS = ["hour", "day", "flat", "unit"];
const ESTIMATE_SOURCES = ["alice", "user", "historical"];

function ensureBillable(raw: any): ActionBillable {
  if (!raw || typeof raw !== "object") return { is_billable: true, rate_unit: "hour", currency: "USD" };
  return {
    is_billable: raw.is_billable ?? true,
    rate_unit: raw.rate_unit || "hour",
    currency: raw.currency || "USD",
    ...raw,
  };
}

function formatCurrency(val: number | null | undefined, currency: string): string {
  if (val == null) return "---";
  return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(val);
}

// ── Field row helper ───────────────────────────────────────────────────

interface FieldRowProps {
  label: string;
  children: React.ReactNode;
  half?: boolean;
}

const FieldRow: React.FC<FieldRowProps> = ({ label, children, half }) => (
  <div className={half ? "flex-1 min-w-[140px]" : "w-full"}>
    <label className="block text-[10px] font-medium mb-0.5" style={{ color: "var(--db-text-dim)" }}>
      {label}
    </label>
    {children}
  </div>
);

const inputClass =
  "w-full rounded border px-2 py-1 text-xs";
const inputStyle: React.CSSProperties = {
  borderColor: "var(--db-border)",
  background: "var(--db-surface)",
  color: "var(--db-text)",
};

// ── Rate select from time_billing items ────────────────────────────────

interface RateSelectProps {
  billable: ActionBillable;
  patch: (updates: Partial<ActionBillable>) => void;
  disabled?: boolean;
  inputClass: string;
  inputStyle: React.CSSProperties;
}

const RateSelect: React.FC<RateSelectProps> = ({ billable, patch, disabled, inputClass, inputStyle }) => {
  const [items, setItems] = useState<any[]>([]);
  const [loaded, setLoaded] = useState(false);

  // Load time-billing items (cached — rarely changes)
  useEffect(() => {
    if (loaded) return;
    setLoaded(true);
    getTimeBillingItems()
      .then((list) => setItems(Array.isArray(list) ? list : []))
      .catch(() => {});
  }, [loaded]);

  const selectItem = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const itemId = Number(e.target.value);
    if (!itemId) return;
    const item = items.find((i: any) => i.id === itemId);
    if (!item) return;
    const svc = item.config?.service || {};
    const billing = svc.billing || {};
    patch({
      rate: item.price?.base ?? billing.rate ?? null,
      rate_unit: billing.rate_unit || (item.uom === 'HR' ? 'hour' : item.uom === 'DAY' ? 'day' : 'unit'),
      skill_category: svc.skill_category || '',
      activity: svc.activity || '',
      product_set: [item.id],
    });
  };

  // Find currently selected item by matching product_set
  const selectedId = String(billable.product_set?.[0] ?? '');

  // Selected item details
  const selectedItem = items.find((i: any) => String(i.id) === selectedId);

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border"
      style={{ borderColor: 'var(--db-border)', background: 'var(--db-surface-alt)' }}
      onClick={(e) => e.stopPropagation()}
    >
      <label className="text-[10px] flex-shrink-0" style={{ color: 'var(--db-text-dim)' }}>name</label>
      <select
        className="text-xs rounded border px-1.5 py-0.5"
        style={{ borderColor: 'var(--db-border)', background: 'var(--db-surface)', color: 'var(--db-text)', minWidth: 130 }}
        value={selectedId}
        onChange={selectItem}
        disabled={disabled}
      >
        <option value="">—</option>
        {items.map((item: any) => (
          <option key={item.id} value={String(item.id)}>{item.name}</option>
        ))}
      </select>
      <label className="text-[10px] flex-shrink-0" style={{ color: 'var(--db-text-dim)' }}>rate</label>
      <input
        className="text-xs rounded border px-1.5 py-0.5 font-medium"
        style={{ borderColor: 'var(--db-border)', background: 'var(--db-surface)', color: 'var(--db-text)', width: 60 }}
        type="number"
        step="1"
        value={billable.rate ?? ''}
        onChange={(e) => patch({ rate: e.target.value === '' ? null : Number(e.target.value) })}
        disabled={disabled}
      />
      <label className="text-[10px] flex-shrink-0" style={{ color: 'var(--db-text-dim)' }}>description</label>
      <input
        className="text-xs rounded border px-1.5 py-0.5 flex-1"
        style={{ borderColor: 'var(--db-border)', background: 'var(--db-surface)', color: 'var(--db-text)' }}
        type="text"
        value={billable.activity || selectedItem?.description || ''}
        onChange={(e) => patch({ activity: e.target.value })}
        disabled={disabled}
      />
    </div>
  );
};

// ── Bill-to — uses standard OrgLookup widget ──────────────────────────

interface BillToSectionProps {
  billable: ActionBillable;
  patch: (updates: Partial<ActionBillable>) => void;
  disabled?: boolean;
  inputClass: string;
  inputStyle: React.CSSProperties;
}

const BillToSection: React.FC<BillToSectionProps> = ({ billable, patch, disabled, inputClass, inputStyle }) => {
  const handleSelect = useCallback((c: any) => {
    patch({
      customer_id: c.id,
      contact_id: c.contact_id ?? c.id,
      company: c.company || c.display_name || '',
      attention: c.attention || c.display_name || '',
    });
  }, [patch]);

  return (
    <div
      className="rounded-lg border px-3 py-2"
      style={{ borderColor: 'var(--db-border)', background: 'var(--db-surface-alt)' }}
    >
      <div className="font-bold mb-2 pb-1 flex items-center gap-2 db-font-sm"
        style={{ color: 'var(--db-text)', borderBottom: '1px solid var(--db-border-light)' }}>
        <span>bill to</span>
        <OrgLookup
          searchModel="customer"
          current={billable.company}
          currentId={billable.customer_id}
          onSelect={handleSelect}
          disabled={disabled}
        />
      </div>
      <div className="flex items-center gap-2">
        <label className="text-[10px] flex-shrink-0" style={{ color: 'var(--db-text-dim)' }}>company</label>
        <input
          className="text-xs rounded border px-1.5 py-0.5 flex-1"
          style={{ borderColor: 'var(--db-border)', background: 'var(--db-surface)', color: 'var(--db-text)' }}
          value={billable.company || ''}
          onChange={(e) => patch({ company: e.target.value })}
          disabled={disabled}
        />
        <label className="text-[10px] flex-shrink-0" style={{ color: 'var(--db-text-dim)' }}>attention</label>
        <input
          className="text-xs rounded border px-1.5 py-0.5 flex-1"
          style={{ borderColor: 'var(--db-border)', background: 'var(--db-surface)', color: 'var(--db-text)' }}
          value={billable.attention || ''}
          onChange={(e) => patch({ attention: e.target.value })}
          disabled={disabled}
        />
      </div>
    </div>
  );
};

// ── Main widget ────────────────────────────────────────────────────────

export const BillableWidget: React.FC<WidgetProps> = ({ value, onChange, disabled }) => {
  const billable = useMemo(() => ensureBillable(value), [value]);

  const patch = useCallback(
    (updates: Partial<ActionBillable>) => {
      const next = { ...billable, ...updates };
      // Auto-compute totals when rate and hours change
      if (next.rate != null && next.rate_unit === "hour") {
        if (next.hours_estimated != null) {
          next.total_estimated = Math.round(next.rate * next.hours_estimated * 100) / 100;
        }
        if (next.hours_actual != null) {
          next.total_actual = Math.round(next.rate * next.hours_actual * 100) / 100;
        }
      }
      // Auto-compute variance
      if (next.hours_estimated && next.hours_actual) {
        next.variance_pct =
          Math.round(((next.hours_actual - next.hours_estimated) / next.hours_estimated) * 10000) / 100;
      }
      onChange(next);
    },
    [billable, onChange]
  );

  const numChange = (field: keyof ActionBillable) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    patch({ [field]: raw === "" ? null : Number(raw) } as any);
  };

  const strChange = (field: keyof ActionBillable) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    patch({ [field]: e.target.value } as any);
  };

  const inp = "text-xs rounded border px-1.5 py-0.5";
  const is = { borderColor: 'var(--db-border)', background: 'var(--db-surface)', color: 'var(--db-text)' } as React.CSSProperties;
  const lbl = "text-[10px] flex-shrink-0";
  const ls = { color: 'var(--db-text-dim)' };
  const val = "text-xs";
  const row = "flex items-center gap-2 py-0.5";

  return (
    <div className="space-y-1">
      {/* Row 1: bill to — customer search + company + attention */}
      <BillToSection billable={billable} patch={patch} disabled={disabled} inputClass={inputClass} inputStyle={inputStyle} />

      {/* Row 2: name [select] rate [$] description [text] + item ida */}
      <RateSelect billable={billable} patch={patch} disabled={disabled} inputClass={inputClass} inputStyle={inputStyle} />

      {/* Row 3: hours est/actual + totals est/actual + variance */}
      <div className={row}>
        <label className={lbl} style={ls}>hrs_est</label>
        <input className={inp} style={{ ...is, width: 55 }} type="number" step="0.25"
          value={billable.hours_estimated ?? ''} onChange={numChange('hours_estimated')} disabled={disabled} />
        <label className={lbl} style={ls}>hrs_act</label>
        <input className={inp} style={{ ...is, width: 55 }} type="number" step="0.25"
          value={billable.hours_actual ?? ''} onChange={numChange('hours_actual')} disabled={disabled} />
        <label className={lbl} style={ls}>tot_est</label>
        <span className={val} style={{ color: 'var(--db-text)' }}>{formatCurrency(billable.total_estimated, billable.currency || 'USD')}</span>
        <label className={lbl} style={ls}>tot_act</label>
        <span className={val} style={{ color: 'var(--db-text)' }}>{formatCurrency(billable.total_actual, billable.currency || 'USD')}</span>
        {billable.variance_pct != null && (
          <>
            <label className={lbl} style={ls}>var</label>
            <span className="text-xs font-semibold" style={{
              color: billable.variance_pct > 10 ? 'var(--db-accent-red)'
                : billable.variance_pct < -10 ? 'var(--db-accent-green)' : 'var(--db-text)',
            }}>
              {billable.variance_pct > 0 ? '+' : ''}{billable.variance_pct.toFixed(1)}%
            </span>
          </>
        )}
      </div>

      {/* Row 4: source + confidence + linkage */}
      <div className={row}>
        <label className={lbl} style={ls}>source</label>
        <select className={inp} style={{ ...is, minWidth: 70 }}
          value={billable.estimate_source || ''} onChange={strChange('estimate_source')} disabled={disabled}>
          <option value="">—</option>
          {ESTIMATE_SOURCES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <label className={lbl} style={ls}>confidence</label>
        <input className={inp} style={{ ...is, width: 40 }} type="number" min={1} max={10}
          value={billable.estimate_confidence ?? ''} onChange={numChange('estimate_confidence')} disabled={disabled} />
        {billable.invoice_id && (
          <><label className={lbl} style={ls}>invoice</label><span className={val} style={ls}>#{billable.invoice_id}</span></>
        )}
        {billable.product_set && billable.product_set.length > 0 && (
          <><label className={lbl} style={ls}>items</label><span className={val} style={ls}>{billable.product_set.join(', ')}</span></>
        )}
      </div>
    </div>
  );
};

export default BillableWidget;
