/* LastChecked: 2026-08-01 | WhereUsed: DbForm | WhoCreated: Claude */
/**
 * useLineCard — returns DataGrid props for rendering transaction lines.
 *
 * This is NOT a component. It's a hook that produces the configuration
 * for DataGrid to render as a line card. LinesCard.tsx is eliminated.
 * DataGrid IS the line card.
 *
 * Usage in UiDetail:
 *   const lineCard = useLineCard({ lines, family, isEditing, ... });
 *   <DataGrid {...lineCard.gridProps} />
 *   {lineCard.footerBar}
 *   {lineCard.panelContent}
 *   {lineCard.modals}
 */
import React, { useState, useCallback, useMemo } from 'react';
import { useSelector } from 'react-redux';
import { selectCurrency } from '@/store/slices/companySlice';
import { lineKey } from '@/apps/transactions/utils/lineHelpers';
import { dec } from '@/apps/transactions/services/dec';
import type { RichColumn } from '@/components/common/DataGrid';
import { useItemImagePopup } from '@/components/common/ItemImagePopup';
import { useItemCard } from '@/components/common/ItemCard';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface UseLineCardOptions {
  lines: any[];
  family: 'sell' | 'exec';
  modelName?: string;  // for model-specific columns (e.g., receipt)
  isEditing: boolean;
  isLocked: boolean;
  priceLevel?: string;
  onLinesChange?: (lines: any[]) => void;
  onDeleteLine?: (lineId: number) => void;
  onDuplicateLine?: (lineId: number) => void;
  onOpenItem?: (itemId: number, itemCode?: string) => void;
  onOpenLineDetails?: (line: any) => void;
}

// ---------------------------------------------------------------------------
// Theme
// ---------------------------------------------------------------------------

/**
 * Row colouring for a line the user removed — greyed out and inert until the
 * save deletes the row. Matches the flattened record's own `_removed` flag, so
 * nothing is added to the grid and the user keeps control of their columns.
 */
const DELETED_ROW_RULES = [
  {
    field: '_removed',
    operator: 'eq' as const,
    value: true,
    bg: 'rgba(148, 163, 184, 0.16)',
    text: 'var(--wc-text-muted, #94a3b8)',
  },
];

const linesTheme = {
  surface: 'var(--wc-surface, #ffffff)',
  surfaceAlt: 'var(--wc-surface-alt, #e8edf3)',
  text: 'var(--wc-text, #1e293b)',
  textMuted: 'var(--wc-text-muted, #64748b)',
  border: 'var(--wc-border, #e2e8f0)',
  borderLight: 'var(--wc-border-light, #f1f5f9)',
  accent: '#2563eb',
  accentGold: '#d97706',
  accentRed: '#dc2626',
  rowActive: '#2563eb',
  rowChecked: 'color-mix(in srgb, var(--wc-accent, #2563eb) 10%, var(--wc-surface, #fff))',
  rowHover: 'var(--wc-surface-alt, #f8fafc)',
  inputBg: 'var(--wc-surface, #fff)',
  inputBorder: 'var(--wc-border, #cbd5e1)',
  resizeHandle: 'var(--wc-text-muted, #94a3b8)',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------


/** Extract a flat record from a nested line for DataGrid consumption. */
function flattenLine(line: any, idx: number): any {
  const lineRecord = line as unknown as Record<string, unknown>;
  const itemCode = String(lineRecord.ida_item ?? line.item?.ida_item ?? "--");
  const tnUrl = itemCode && itemCode !== '--' ? `/wcapi/_image/item/${encodeURIComponent(itemCode)}/tn.jpg` : '';
  const description = String(lineRecord.description ?? line.item?.description ?? "--");
  const qty = Number(lineRecord.qty ?? line.quantity?.active ?? 0);
  const remaining = Number(line.quantity?.remaining ?? 0);
  const isComplete = Boolean(line.quantity?.is_complete);
  const uom = String(lineRecord.unit_measure ?? line.item?.unit_measure ?? "EA");
  const priceLevel = String(line.price_level ?? lineRecord.price_level ?? "");

  const priceRecord = lineRecord.price as Record<string, unknown> | undefined;
  const unitPrice = Number(priceRecord?.sell ?? priceRecord?.unit ?? line.price?.unit ?? 0);
  const discountPct = Number(priceRecord?.discount_percent ?? line.price?.discount_percent ?? 0);

  const costRecord = lineRecord.cost as Record<string, unknown> | undefined;
  const unitCost = Number(costRecord?.unit ?? line.cost?.unit ?? 0);

  // line.totals is the server's as saved; while editing, the browser engine's by the same rule
  // (useRecordForm.currentData, readme 107) — one formula, never a local one here.
  const discountedUnit = Number(line.totals?.discounted_unit ?? 0);
  const extended = Number(line.totals?.amount ?? 0);

  const weight = Number(line.physical?.weight ?? 0);

  // A line the user removed stays visible — greyed out, struck through and
  // inert — with its active quantity zeroed. These are DISPLAY values only:
  // the record keeps its real quantity and goes over the wire with its id
  // and `_delete: true`.
  const isRemoved = line._removed === true;
  const lineType = String(line.line_type || 'product');

  return {
    id: lineKey(line, idx),
    _idx: idx,
    _line: line,
    _removed: isRemoved,
    tn_url: tnUrl,
    item_code: itemCode,
    description,
    qty: isRemoved ? 0 : qty,
    // What the source asked of this line when it was made; asked − active did not ship or arrive.
    asked: isRemoved ? 0 : Number(line.quantity?.staged ?? 0),
    short: isRemoved ? 0 : Math.max(Number(line.quantity?.staged ?? 0) - Number(line.quantity?.active ?? 0), 0),
    received: Number(line.quantity?.active ?? 0),
    remaining: isRemoved ? 0 : remaining,
    remain: isRemoved ? 0 : remaining,
    is_complete: isComplete,
    uom,
    price_level: priceLevel,
    unit_price: unitPrice,
    discount_pct: discountPct,
    discounted_unit: discountedUnit,
    unit_cost: unitCost,
    amount: isRemoved ? 0 : extended,
    weight,
    _itemId: Number(line.item_id ?? line.item?.id ?? line.item?.item_id ?? 0),
    _itemIsActive: line.item?.is_active !== false,
    _hasBacklog: !isRemoved && remaining > 0 && !isComplete,
    line_type: lineType,
    tax_rate: Number(line.totals?.tax_rate ?? line.tax?.sales_rate ?? 0),
    // Commission — from commission.reps[] envelope
    comm_total: Number(line.commission?.total ?? 0),
    comm_rate: Number(line.commission?.reps?.[0]?.rate_pct ?? 0),
    comm_eff_rate: Number(line.commission?.reps?.[0]?.effective_rate ?? 0),
    comm_basis: String(line.commission?.basis || ''),
    _commReps: line.commission?.reps || [],
    // Receipt-specific fields
    warehouse: line.warehouse?.name || line.warehouse_name || '',
    lot: line.lot || '',
    serial_batch: line.serial_batch || '',
  };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useLineCard(options: UseLineCardOptions) {
  const { lines, family, modelName, isEditing, isLocked, onLinesChange } = options;
  const isSellSide = family === 'sell';
  const isExecSide = !isSellSide;
  const isReceipt = modelName === 'receipt';
  const isInvoice = modelName === 'invoice';
  const canEdit = isEditing && !isLocked;
  const currency = useSelector(selectCurrency);

  // ── Image popup (cmd-click on item_code) ─────────────────────────
  const [imagePopup, showImagePopup] = useItemImagePopup();
  // ── Item card (click on item_code) ──────────────────────────────
  const [itemCard, showItemCard] = useItemCard();

  // ── State ────────────────────────────────────────────────────────
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedLineIds, setSelectedLineIds] = useState<Set<number>>(new Set());
  const [activePanel, setActivePanel] = useState<'none' | 'inventory' | 'margin' | 'spec' | 'xref'>('none');
  const [showDiscountDialog, setShowDiscountDialog] = useState(false);
  const [discountInput, setDiscountInput] = useState('');
  const [bulkEditField, setBulkEditField] = useState<string | null>(null);
  const [bulkEditValue, setBulkEditValue] = useState('');
  const [showCommission, setShowCommission] = useState(false);
  const [viewMode, setViewMode] = useState<'list' | 'cards' | 'detail'>('list');

  const togglePanel = (panel: typeof activePanel) =>
    setActivePanel(prev => prev === panel ? 'none' : panel);

  // ── Flatten lines ────────────────────────────────────────────────
  const records = useMemo(
    () => lines.map((l, i) => flattenLine(l, i)),
    [lines]
  );

  // ── Field update ─────────────────────────────────────────────────
  const applyFieldUpdate = useCallback((line: any, field: string, value: unknown): any => {
    const updated = { ...line, _dirty: true };
    switch (field) {
      case "qty": {
        const newQty = Number(value);
        const isComplete = updated.quantity?.is_complete;
        const remaining = isComplete ? 0 : newQty;
        // A saved invoice line keeps what its order asked (staged): asked − qty did not ship.
        // So does a proposed line of any converted document, before its first save.
        const staged = (isInvoice && updated.id) || updated._from != null ? updated.quantity?.staged : newQty;
        return { ...updated, quantity: { ...updated.quantity, active: newQty, staged, remaining } };
      }
      case "received": {
        // Saving a receipt receives the goods (Bill, 2026-11-11, readme 108 R1): the number typed
        // is what is on the shelf at the save. A saved line keeps what its purchase asked.
        const got = Number(value);
        const staged = updated.id || updated._from != null ? updated.quantity?.staged : got;
        return { ...updated, quantity: { ...updated.quantity, active: got, staged } };
      }
      case "description":
        return { ...updated, item: { ...updated.item, description: String(value) } };
      case "unit_price": {
        return { ...updated, price: { ...updated.price, unit: Number(value) } };
      }
      case "discount_pct": {
        return { ...updated, price: { ...updated.price, discount_percent: Number(value) } };
      }
      case "is_complete": {
        const complete = Boolean(value);
        const newQuantity = { ...updated.quantity, is_complete: complete };
        if (complete) { newQuantity.remaining = 0; } else {
          const active = newQuantity.active ?? 0;
          const childrenSum = newQuantity.children_active?.sum ?? 0;
          newQuantity.remaining = active - childrenSum;
        }
        return { ...updated, quantity: newQuantity };
      }
      case "unit_cost": {
        return { ...updated, cost: { ...updated.cost, unit: Number(value) } };
      }
      case "tax_rate": {
        const newRate = Number(value);
        return { ...updated, tax: { ...updated.tax, sales_rate: newRate, rate_source: 'line' } };
      }
      case "comm_rate": {
        // A preview for speed of view. The save recomputes every commission amount on the
        // server from the rate (commission_compute.settle_line_commission, readme 111); the
        // figures below mirror its formula, half-up, and are replaced by the server's.
        const newRate = Number(value);
        const priceExt = updated.totals?.amount ?? 0;
        const costExt = updated.totals?.cost ?? 0;
        const existingComm = updated.commission || {};
        const existingReps = existingComm.reps || [];
        const basis = existingComm.basis || 'revenue';
        const levelFactor = existingReps[0]?.level_factor ?? 1.0;
        const splitPct = existingReps[0]?.split_pct ?? 100;
        const baseAmount = basis === 'margin' ? (priceExt - costExt) : priceExt;
        const amount = dec(baseAmount, -1).mul(dec(newRate, -1)).div(dec(100)).mul(dec(levelFactor, -1))
          .mul(dec(splitPct, -1)).div(dec(100)).quantize(2).toNumber();
        const effRate = dec(newRate, -1).mul(dec(levelFactor, -1)).mul(dec(splitPct, -1)).div(dec(100)).quantize(4).toNumber();
        const newRep = {
          ...(existingReps[0] || {}),
          rate_pct: newRate,
          level_factor: levelFactor,
          split_pct: splitPct,
          effective_rate: effRate,
          amount,
          override: true,
          override_reason: 'manual',
        };
        const otherReps = existingReps.slice(1);
        const otherTotal = otherReps.reduce((s: number, r: any) => s + (r.amount ?? 0), 0);
        return {
          ...updated,
          commission: {
            ...existingComm,
            reps: [newRep, ...otherReps],
            total: dec(amount).add(dec(otherTotal)).toNumber(),
            basis,
          },
        };
      }
      default:
        return updated;
    }
  }, [isExecSide, isSellSide]);

  const handleCellEdit = useCallback((recordId: number, field: string, value: unknown) => {
    if (!canEdit || !onLinesChange) return;

    // A line marked deleted is inert — it is on screen only so the user can
    // see what the save will delete. To escape the delete, close the window.
    const target = lines.find((l: any, i: number) => lineKey(l, i) === recordId);
    if (target?._removed) return;

    // Zero-quantity check — ask user to remove or keep the line
    if (field === 'qty' && Number(value) === 0) {
      const line = lines.find((l: any, i: number) => lineKey(l, i) === recordId);
      const itemCode = line?.item?.ida_item || line?.item?.sku || `line #${recordId}`;
      const remove = confirm(`Quantity set to zero for ${itemCode}.\n\nOK = Remove line from transaction\nCancel = Keep line at zero quantity`);
      if (remove) {
        // Mark removed — at save a never-saved line disappears, while a
        // persisted line goes to the backend marked `_delete` to be deleted.
        onLinesChange(lines.map((l: any, i: number) =>
          (lineKey(l, i) === recordId ? { ...l, _removed: true } : l)));
        return;
      }
      // Keep at zero — fall through to normal update
    }

    const newLines = lines.map((l: any, i: number) => {
      if (lineKey(l, i) !== recordId) return l;
      return applyFieldUpdate(l, field, value);
    });
    onLinesChange(newLines);
  }, [canEdit, onLinesChange, lines, applyFieldUpdate]);

  // ── Selection ────────────────────────────────────────────────────
  const selectedLineRecord = useMemo(() => {
    if (selectedId == null) return null;
    return records.find(r => r.id === selectedId) ?? null;
  }, [selectedId, records]);

  const inventoryItemIds = useMemo(() => {
    const source = selectedLineIds.size > 0 ? records.filter(r => selectedLineIds.has(r.id)) : records;
    return [...new Set(source.map(r => r._itemId).filter((id: number) => id > 0))];
  }, [records, selectedLineIds]);

  // ── Column definitions ───────────────────────────────────────────
  const richColumns = useMemo((): RichColumn[] => {
    const cols: RichColumn[] = [];

    cols.push({
      name: '',
      field: 'tn_url',
      width: '36px',
      sortable: false,
      cell: (row: any) => row.tn_url
        ? React.createElement('img', {
            src: row.tn_url,
            alt: '',
            style: { width: 28, height: 28, objectFit: 'cover', borderRadius: 3 },
            loading: 'lazy',
            onError: (e: any) => { e.target.onerror = null; e.target.src = '/images/no-image.svg'; },
          })
        : null,
    });
    cols.push({
      name: 'item_code',
      field: 'item_code',
      width: '120px',
      sortable: true,
      cell: (row: any) => React.createElement('span', {
        style: {
          cursor: row.item_code && row.item_code !== '--' && !row._removed ? 'pointer' : 'default',
          color: row._removed ? 'inherit' : (row.item_code && row.item_code !== '--' ? 'var(--wc-accent, #2563eb)' : 'inherit'),
          // Struck through when the line is marked for deletion — the grey
          // row alone reads as "inactive"; the strike reads as "going away".
          textDecoration: row._removed ? 'line-through' : undefined,
        },
        onClick: (e: React.MouseEvent) => {
          if (!row.item_code || row.item_code === '--' || row._removed) return;
          e.stopPropagation();
          if (e.metaKey || e.ctrlKey) {
            showImagePopup(row.item_code, (e.target as HTMLElement).getBoundingClientRect());
          } else {
            showItemCard(row.item_code, (e.target as HTMLElement).getBoundingClientRect());
          }
        },
      }, row.item_code),
    });
    if (isReceipt) {
      // Received (active) is what the user edits and what a save puts on the shelf (Bill,
      // 2026-11-11, readme 108 R1); asked is what the purchase had left when the receipt was made.
      cols.push({ name: 'received', field: 'received', width: '80px', sortable: true });
      cols.push({ name: 'asked', field: 'asked', width: '70px', sortable: true });
    } else if (isInvoice) {
      // What the order asked and did not ship stays on the order; the invoice shows it (Bill, 2026-11-13).
      cols.push({ name: 'qty', field: 'qty', width: '80px', sortable: true });
      cols.push({ name: 'not shipped', field: 'short', width: '80px', sortable: true });
    } else {
      cols.push({ name: 'qty', field: 'qty', width: '80px', sortable: true });
      cols.push({ name: 'remain', field: 'remaining', width: '55px', sortable: true });
    }

    if (isSellSide) {
      cols.push({ name: 'c', field: 'is_complete', width: '28px', sortable: false });
    }

    cols.push({
      name: 'description',
      field: 'description',
      width: '300px',
      sortable: true,
      cell: (row: any) => row._removed
        ? React.createElement('span', { style: { textDecoration: 'line-through' } }, row.description)
        : row.description,
    });

    if (isSellSide) {
      cols.push({ name: 'pl', field: 'price_level', width: '30px', sortable: true });
      cols.push({ name: 'unit_price', field: 'unit_price', width: '100px', sortable: true });
      cols.push({ name: '%', field: 'discount_pct', width: '35px', sortable: true });
      cols.push({ name: 'disc price', field: 'discounted_unit', width: '85px', sortable: true });
    }

    if (isExecSide) {
      cols.push({ name: 'unit_cost', field: 'unit_cost', width: '100px', sortable: true });
    }

    cols.push({ name: 'amount', field: 'amount', width: '110px', sortable: true });
    // No tax% column: a line's tax rate is noise to 95% of companies (Bill, 2026-11-06); the
    // document's tax stays in finance and on the totals strip.

    // Commission columns — hidden unless toggled on
    if (showCommission && isSellSide) {
      cols.push({ name: 'comm%', field: 'comm_rate', width: '55px', sortable: true });
      cols.push({ name: 'eff%', field: 'comm_eff_rate', width: '55px', sortable: true });
      cols.push({ name: 'comm$', field: 'comm_total', width: '80px', sortable: true });
    }

    // Receipt-specific columns
    if (isReceipt) {
      cols.push({ name: 'warehouse', field: 'warehouse', width: '100px', sortable: true });
      cols.push({ name: 'lot', field: 'lot', width: '80px', sortable: true });
      cols.push({ name: 'serial', field: 'serial_batch', width: '100px', sortable: true });
    }

    return cols;
  }, [isSellSide, isExecSide, isReceipt, isInvoice, showCommission]);

  const colWidths = useMemo(() => {
    const w: Record<string, number> = {};
    richColumns.forEach(c => { if (c.width) w[c.name] = parseInt(c.width, 10) || 100; });
    return w;
  }, [richColumns]);

  const fieldBehaviors = useMemo(() => ({
    qty: { type: 'number', precision: currency.qty_precision, bulkEditable: true },
    asked: { type: 'number', precision: currency.qty_precision, calculated: true },
    short: { type: 'number', precision: currency.qty_precision, calculated: true },
    received: { type: 'number', precision: currency.qty_precision },
    remaining: { type: 'number', precision: currency.qty_precision, calculated: true },
    remain: { type: 'number', precision: currency.qty_precision, calculated: true },
    is_complete: { type: 'boolean' },
    price_level: { type: 'readonly' },
    unit_price: { type: 'currency', precision: currency.unit_price_precision, bulkEditable: true },
    discount_pct: { type: 'readonly', bulkEditable: true },
    discounted_unit: { type: 'currency', precision: currency.unit_price_precision, bulkEditable: true },
    unit_cost: { type: 'currency', precision: currency.unit_cost_precision },
    amount: { type: 'currency', precision: currency.total_precision, calculated: true },
    item_code: { type: 'readonly' },
    description: { type: 'readonly' },
    uom: { type: 'readonly' },
    warehouse: { type: 'readonly' },
    lot: { type: 'readonly' },
    serial_batch: { type: 'readonly' },
    tax_rate: { type: 'number', precision: 4, bulkEditable: true },
    comm_rate: { type: 'number', precision: 2, bulkEditable: true },
    comm_eff_rate: { type: 'number', precision: 2, calculated: true },
    comm_total: { type: 'currency', precision: currency.total_precision, calculated: true },
  }), [currency]);

  // ── Discount ─────────────────────────────────────────────────────
  const applyDiscount = useCallback(() => {
    const pct = parseFloat(discountInput);
    if (isNaN(pct) || pct <= 0) { setShowDiscountDialog(false); return; }
    const targetIds = selectedLineIds.size > 0
      ? selectedLineIds
      : new Set(records.map(r => r.id).filter((id): id is number => id != null));
    targetIds.forEach((id) => handleCellEdit(id, 'discount_pct', pct));
    setShowDiscountDialog(false);
    setDiscountInput('');
  }, [discountInput, selectedLineIds, records, handleCellEdit]);

  // ── Bulk edit from header click ─────────────────────────────────
  const BULK_EDITABLE = new Set(['unit_price', 'discount_pct', 'discounted_unit', 'qty', 'tax_rate', 'comm_rate']);

  const openBulkEdit = useCallback((field: string) => {
    if (!canEdit || !BULK_EDITABLE.has(field)) return;
    setBulkEditField(field);
    setBulkEditValue('');
  }, [canEdit]);

  const applyBulkEdit = useCallback(() => {
    if (!bulkEditField || !onLinesChange) return;
    const val = parseFloat(bulkEditValue);
    if (isNaN(val)) { setBulkEditField(null); return; }

    const targetIds = selectedLineIds.size > 0
      ? selectedLineIds
      : new Set(records.map(r => r.id).filter((id): id is number => id != null));

    // Apply all changes in one pass — avoids stale state from multiple handleCellEdit calls
    let updated = [...lines];
    updated = updated.map((l: any, i: number) => {
      const id = lineKey(l, i);
      if (!targetIds.has(id)) return l;

      if (bulkEditField === 'unit_price') {
        let result = applyFieldUpdate(l, 'unit_price', val);
        result = applyFieldUpdate(result, 'discount_pct', 0);
        return result;
      } else if (bulkEditField === 'discount_pct') {
        return applyFieldUpdate(l, 'discount_pct', val);
      } else if (bulkEditField === 'discounted_unit') {
        const unitP = l.price?.unit ?? 0;
        if (unitP > 0) {
          const pct = ((unitP - val) / unitP) * 100;
          return applyFieldUpdate(l, 'discount_pct', Math.round(pct * 100) / 100);
        }
        return l;
      } else if (bulkEditField === 'qty') {
        return applyFieldUpdate(l, 'qty', val);
      } else if (bulkEditField === 'tax_rate') {
        return applyFieldUpdate(l, 'tax_rate', val);
      } else if (bulkEditField === 'comm_rate') {
        return applyFieldUpdate(l, 'comm_rate', val);
      }
      return l;
    });

    onLinesChange(updated);
    setBulkEditField(null);
    setBulkEditValue('');
  }, [bulkEditField, bulkEditValue, selectedLineIds, records, lines, onLinesChange, applyFieldUpdate]);

  const cancelBulkEdit = useCallback(() => {
    setBulkEditField(null);
    setBulkEditValue('');
  }, []);

  // ── Return ───────────────────────────────────────────────────────
  return {
    records,
    richColumns,
    colWidths,
    fieldBehaviors,
    selectedId,
    setSelectedId,
    selectedLineIds,
    setSelectedLineIds,
    selectedLineRecord,
    inventoryItemIds,
    activePanel,
    togglePanel,
    showDiscountDialog,
    setShowDiscountDialog,
    discountInput,
    setDiscountInput,
    applyDiscount,
    handleCellEdit,
    canEdit,
    isSellSide,
    theme: linesTheme,
    // Inert-row convention: a deleted line is dimmed until the save removes it.
    colorRules: DELETED_ROW_RULES,
    lineCount: lines.length,
    totalQty: records.reduce((s, r) => s + (r.qty ?? 0), 0),
    bulkEditField,
    bulkEditValue,
    setBulkEditValue,
    openBulkEdit,
    applyBulkEdit,
    cancelBulkEdit,
    showCommission,
    setShowCommission,
    imagePopup,
    itemCard,
    viewMode,
    setViewMode,
  };
}
