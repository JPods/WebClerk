/* LastChecked: 2026-08-03 | WhereUsed: UiDetail | WhoCreated: Claude */
import React, { useState, useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useAppSelector } from '@/store/hooks';
import DataGrid from '@/components/common/DataGrid';
import { useLineCard } from '@/hooks/useLineCard';
import { useWindowManager } from '@/context/WindowManagerContext';
import { showToast } from '@/store/slices/toastSlice';
import InventoryPanel from '../panels/InventoryPanel';
import MarginPanel from '../panels/MarginPanel';
import SpecPanel from '../panels/SpecPanel';
import XRefPanel from '../panels/XRefPanel';
import CommissionPanel from '../panels/CommissionPanel';
import { TransactionItemSearch, resolveItemCode, resolveItemDescription, resolveUnitPrice, resolveUnitCost, resolveQtyOnHand } from '../TransactionItemSearch';
import type { ItemSearchResult } from '../TransactionItemSearch';
import { getNextLineNumber } from '../../utils/lineHelpers';
import type { LineCardSection } from '@/hooks/useDetailLayout';
import type { TransactionLine } from '../../types/transactionTypes';
import { formatCurrency } from '@/utils/stringUtils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface LineCardRendererProps {
  section: LineCardSection;
  data: any;
  isEditing: boolean;
  isLocked: boolean;
  onLinesChange: (lines: TransactionLine[]) => void;
  onEnterPayment?: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/** Render the line card -- DataGrid with line card config, no LinesCard component */
const LineCardRenderer: React.FC<LineCardRendererProps> = ({ section, data, isEditing, isLocked, onLinesChange, onEnterPayment }) => {
  const lines = data?.lines || [];
  const windowManager = useWindowManager();
  const dispatch = useDispatch();
  const [showItemSearch, setShowItemSearch] = useState(false);
  const isSellSide = section.family === 'sell';
  const companyInventory = useSelector((s: any) => s.company?.inventory) || {};
  const authUser = useAppSelector((s) => s.auth.user);
  const isStaff = authUser?.is_staff || authUser?.is_superuser || false;

  const handleAddItem = useCallback((item: ItemSearchResult, quantity: number) => {
    const itemId = item.id || item.item_id || item.itemId || 0;
    const itemCode = resolveItemCode(item);
    const description = resolveItemDescription(item);

    // 1. Price level resolution — use order's price level, resolve from item's price matrix
    const priceLevel = data?.price_level || '';
    const unitPrice = resolveUnitPrice(item, priceLevel);
    const unitCost = resolveUnitCost(item);

    // 2. Minimum qty — enforce item's minimum order quantity
    const minQty = Number((item as any).qty_sale_default || (item as any).qtySaleDefault || (item as any).min_order_qty || 0);
    let effectiveQty = quantity;
    if (minQty > 0 && quantity < minQty) {
      effectiveQty = minQty;
      dispatch(showToast({ message: `Minimum quantity for ${itemCode} is ${minQty}. Adjusted.`, type: 'info' }));
    }

    // 3. Available qty alert — warn if ordering more than available
    const onHand = resolveQtyOnHand(item);
    const onOrder = Number((item as any).qty_on_sales_order || (item as any).qtyOnSalesOrder || 0);
    const available = onHand - onOrder;
    if (available >= 0 && effectiveQty > available) {
      dispatch(showToast({ message: `${itemCode}: ordering ${effectiveQty} but only ${available} available`, type: 'info' }));
    }

    // 4. Serial tracking — flag line if item is serialized and system tracks serials
    const isSerialized = Boolean((item as any).serialized || (item as any).is_serialized);
    const trackSerials = companyInventory.do_serial_nums === true;

    // Item alert message
    const alertMsg = (item as any).alert_message || (item as any).alertMessage || '';
    if (alertMsg) {
      dispatch(showToast({ message: `${itemCode}: ${alertMsg}`, type: 'info', duration: 5000 }));
    }

    // 5. Ship-on date — calculate from need date minus lead time
    const leadTimeDays = Number((item as any).lead_time_sales || (item as any).leadTimeSales || (item as any).time_lead || 0);
    const needDate = data?.dt_needed;
    let shipOnDate: string | null = null;
    if (needDate && leadTimeDays > 0) {
      const nd = new Date(typeof needDate === 'number' ? needDate : needDate);
      if (!isNaN(nd.getTime())) {
        nd.setDate(nd.getDate() - leadTimeDays);
        shipOnDate = nd.toISOString().split('T')[0];
      }
    }

    // 6. Linked items — prompt if item has cross-references
    const hasLinks = Boolean((item as any).linked || (item as any).has_xrefs);
    if (hasLinks) {
      dispatch(showToast({ message: `${itemCode} has linked items — check XR panel`, type: 'info' }));
    }

    // 7. Commission — from item commission rate
    const commRate = Number((item as any).commission_rate || (item as any).commissionRate || 0);

    const lineConfig: any = {};
    if (isSerialized && trackSerials) lineConfig.serial_tracking = true;
    if (shipOnDate) lineConfig.ship_on_date = shipOnDate;

    const newLine: any = {
      id: -Date.now(),
      line_number: getNextLineNumber(lines),
      price_level: priceLevel,
      status: '',
      is_active: true,
      item: {
        item_id: itemId,
        ida_item: itemCode,
        description,
        unit_measure: item.unit_of_measure || item.unitOfMeasure || item.unit_measure || 'EA',
        is_serialized: isSerialized,
      },
      quantity: { active: effectiveQty, remaining: effectiveQty, staged: effectiveQty },
      price: { unit: unitPrice, extended: unitPrice * effectiveQty, discount_percent: 0 },
      cost: { unit: unitCost, extended: unitCost * effectiveQty },
      commission: commRate > 0 ? { rate: commRate, amount: unitPrice * effectiveQty * commRate / 100 } : {},
      comments: { process: (item as any).li_comment || (item as any).liComment || '' },
      config: lineConfig,
      _dirty: true,
    };

    onLinesChange([...lines, newLine]);
  }, [lines, data?.price_level, onLinesChange, dispatch, companyInventory]);

  const lc = useLineCard({
    lines,
    family: section.family,
    isEditing,
    isLocked,
    priceLevel: data?.price_level,
    onLinesChange,
    onOpenItem: (itemId, itemCode) => {
      const path = `/item?id=${itemId}`;
      windowManager.ensureWindow(path, `Item ${itemCode || itemId}`, { maximized: false });
    },
  });


  const formatNumber = (v: number) => v.toLocaleString();

  // ── Line type toggle ─────────────────────────────────────────────
  const LINE_TYPE_OPTIONS = [
    { value: 'shipping', label: 'Ship', color: 'blue' },
    { value: 'tax',      label: 'Tax',  color: 'amber' },
    { value: 'discount', label: 'Disc', color: 'red' },
  ] as const;

  const selectedLine = lc.selectedId != null
    ? lines.find((_: any, i: number) => lc.records[i]?.id === lc.selectedId)
    : null;
  const selectedLineType = selectedLine?.line_type || 'product';

  const handleLineTypeToggle = useCallback((type: string) => {
    if (!lc.canEdit || lc.selectedId == null) return;
    const newLines = lines.map((l: any, i: number) => {
      if (lc.records[i]?.id !== lc.selectedId) return l;
      // Toggle: click same type reverts to product
      const newType = (l.line_type || 'product') === type ? 'product' : type;
      return { ...l, line_type: newType, _dirty: true };
    });
    onLinesChange(newLines);
  }, [lc.canEdit, lc.selectedId, lines, lc.records, onLinesChange]);

  // Selection-aware footer calculations
  const activeRecords = lc.selectedLineIds.size > 0
    ? lc.records.filter(r => lc.selectedLineIds.has(r.id))
    : lc.records;
  const footerQty = activeRecords.reduce((s, r) => s + (r.qty ?? 0), 0);
  const footerExtended = activeRecords.reduce((s, r) => s + (r.extended ?? 0), 0);
  const footerBacklog = activeRecords.reduce((s, r) => s + (r._hasBacklog ? r.remaining * (lc.isSellSide ? r.discounted_unit : r.unit_cost) : 0), 0);
  const selectionLabel = lc.selectedLineIds.size > 0 ? ` (${lc.selectedLineIds.size} selected)` : '';

  if (!lines.length && !isEditing) {
    return (
      <div className="text-center py-12 text-slate-400">
        <p>No line items</p>
      </div>
    );
  }

  const footerBar = (
    <div className="px-2 py-2" style={{ background: 'var(--wc-surface-alt, #f8f9fa)', borderTop: '2px solid var(--wc-border, #dee2e6)', fontSize: 'inherit' }}>
      <div className="flex items-center gap-3 mb-1">
        {/* Tools — left side (user's focus) */}
        {lc.canEdit && (
          <button type="button" onClick={() => setShowItemSearch(prev => !prev)}
            className={`px-2 py-0.5 font-medium rounded transition-colors ${showItemSearch ? 'bg-green-600 text-white' : 'text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/30 border border-green-300 dark:border-green-700'}`}
            style={{ fontSize: 'inherit' }}
            title="Search and add items">+ Item</button>
        )}
        <span className="flex items-center gap-1 font-bold">
          <button type="button" onClick={() => lc.togglePanel('inventory')}
            className={`px-1.5 py-0.5 rounded transition-colors ${lc.activePanel === 'inventory' ? 'bg-blue-600 text-white' : 'text-slate-500 dark:text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30'}`}
            title="Inventory lookup (L)">L</button>
          <button type="button" onClick={() => lc.togglePanel('spec')}
            className={`px-1.5 py-0.5 rounded transition-colors ${lc.activePanel === 'spec' ? 'bg-blue-600 text-white' : 'text-slate-500 dark:text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30'}`}
            title="Specification (S)">S</button>
          <button type="button" onClick={() => lc.togglePanel('xref')}
            className={`px-1.5 py-0.5 rounded transition-colors ${lc.activePanel === 'xref' ? 'bg-blue-600 text-white' : 'text-slate-500 dark:text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30'}`}
            title="Cross-references (XR)">XR</button>
          <button type="button" onClick={() => lc.togglePanel('margin')}
            className={`px-1.5 py-0.5 rounded transition-colors ${lc.activePanel === 'margin' ? 'bg-green-600 text-white' : 'text-slate-500 dark:text-slate-400 hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-900/30'}`}
            title="Margin view (M)">M</button>
          {isSellSide && isStaff && (
            <button type="button" onClick={() => lc.setShowCommission(!lc.showCommission)}
              className={`px-1.5 py-0.5 rounded transition-colors ${lc.showCommission ? 'bg-purple-600 text-white' : 'text-slate-500 dark:text-slate-400 hover:text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-900/30'}`}
              title="Commission columns (C)">C</button>
          )}
        </span>
        {lc.selectedId != null && (
          <span className="flex items-center gap-1 ml-1">
            <button type="button" onClick={() => { const line = lc.records.find(r => r.id === lc.selectedId); if (line?._line) lc.setSelectedId(line.id); }}
              className="px-1.5 py-0.5 text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded" title="Edit line details">edit</button>
            {lc.canEdit && (
              <button type="button" onClick={() => { lc.selectedLineIds.forEach(id => onLinesChange?.(lines.filter((_: any, i: number) => lc.records[i]?.id !== id))); lc.setSelectedLineIds(new Set()); }}
                className="px-1.5 py-0.5 text-slate-500 dark:text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded" title="Delete selected (Del)">del</button>
            )}
          </span>
        )}
        {lc.canEdit && lc.selectedId != null && (
          <span className="flex items-center gap-0.5 ml-1">
            <span className="text-slate-400 dark:text-slate-500 mr-0.5">Type:</span>
            {LINE_TYPE_OPTIONS.map(opt => {
              const isActive = selectedLineType === opt.value;
              const colorMap = { blue: 'bg-blue-500 text-white', amber: 'bg-amber-500 text-white', red: 'bg-red-500 text-white' };
              const hoverMap = { blue: 'hover:bg-blue-50 hover:text-blue-600', amber: 'hover:bg-amber-50 hover:text-amber-600', red: 'hover:bg-red-50 hover:text-red-600' };
              return (
                <button key={opt.value} type="button" onClick={() => handleLineTypeToggle(opt.value)}
                  className={`px-1.5 py-0.5 rounded transition-colors border-b-2 ${
                    isActive
                      ? `${colorMap[opt.color]} border-${opt.color}-700`
                      : `text-slate-500 dark:text-slate-400 border-transparent ${hoverMap[opt.color]}`
                  }`}
                  title={`${isActive ? 'Revert to product' : `Mark as ${opt.value}`} line`}>
                  {opt.label}
                </button>
              );
            })}
          </span>
        )}
        {/* Line summary — right side */}
        <span className="flex-1" />
        <span className="font-medium text-[var(--wc-text-muted,#6c757d)]">Lns: {lc.lineCount}</span>
        <span className="text-[var(--wc-text-muted,#6c757d)]">Items: {formatNumber(footerQty)}</span>
        {selectionLabel && <span className="text-blue-600 font-medium">{selectionLabel}</span>}
      </div>
      <div className="flex items-center gap-2 italic justify-end" style={{ fontSize: 'inherit' }}>
        <span className="text-slate-400 dark:text-slate-500">tax:</span>
        <span className="font-mono text-slate-600 dark:text-slate-300 w-14 text-right">{formatCurrency(data?.totals?.tax ?? 0)}</span>
        <span className="text-slate-400 dark:text-slate-500">ship:</span>
        <span className="font-mono text-slate-600 dark:text-slate-300 w-14 text-right">{formatCurrency(data?.totals?.shipping ?? 0)}</span>
        <span className="text-slate-400 dark:text-slate-500">other:</span>
        <span className="font-mono text-slate-600 dark:text-slate-300 w-14 text-right">{formatCurrency(data?.totals?.other ?? 0)}</span>
        {lc.showCommission && isStaff && (
          <>
            <span className="text-purple-400 dark:text-purple-300">comm:</span>
            <span className="font-mono text-purple-600 dark:text-purple-300 w-14 text-right">{formatCurrency(data?.commission?.total ?? 0)}</span>
          </>
        )}
        <span className="text-slate-300 dark:text-slate-600 not-italic">|</span>
        {onEnterPayment ? (
          <>
            <button
              type="button"
              onClick={onEnterPayment}
              className="not-italic px-2 py-0.5 font-medium rounded bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400 hover:bg-green-100 dark:hover:bg-green-900/50 border border-green-200 dark:border-green-700 transition-colors"
              style={{ fontSize: 'inherit' }}
              title="Enter a payment or apply an existing one"
            >
              Payment
            </button>
            <span
              className="font-mono text-green-700 dark:text-green-400 w-16 text-right not-italic cursor-default"
              title={`Paid: ${formatCurrency(data?.totals?.received ?? 0)}\nBalance: ${formatCurrency(data?.totals?.balance ?? 0)}`}
            >
              <span className="text-slate-400 dark:text-slate-500 italic mr-0.5" style={{ fontSize: '0.85em' }}>bal:</span>
              {formatCurrency(data?.totals?.balance ?? 0)}
            </span>
          </>
        ) : (
          <>
            <span className="text-slate-500 dark:text-slate-400">deposit:</span>
            <span className="font-mono font-medium text-slate-800 dark:text-slate-200 w-16 text-right">{formatCurrency(data?.totals?.deposit ?? 0)}</span>
          </>
        )}
        {footerBacklog > 0 && (
          <>
            <span className="text-red-500 dark:text-red-400">backlog:</span>
            <span className="font-mono font-medium text-red-600 dark:text-red-400 w-16 text-right">{formatCurrency(footerBacklog)}</span>
          </>
        )}
        <span className="text-slate-700 dark:text-slate-200 not-italic font-semibold">total:</span>
        <span className="font-bold text-slate-900 dark:text-white w-24 text-right not-italic">{formatCurrency(footerExtended)}</span>
      </div>
    </div>
  );

  const panelContent = (
    <>
      {showItemSearch && lc.canEdit && (
        <div className="border-t-2 border-green-300 p-3" style={{ background: 'var(--db-surface, #fff)' }}>
          <TransactionItemSearch
            onAddItem={handleAddItem}
            useCost={!isSellSide}
            defaultQuantity={1}
          />
        </div>
      )}
      {lc.activePanel === 'margin' && (
        <MarginPanel lines={lines} selectedIds={lc.selectedLineIds} isSellSide={lc.isSellSide} />
      )}
      {lc.showCommission && isSellSide && (
        <div className="border-t border-purple-200 max-h-[300px] overflow-y-auto" style={{ background: 'var(--db-surface, #fff)' }}>
          <CommissionPanel lines={lines} selectedIds={lc.selectedLineIds} headerCommission={data?.commission} />
        </div>
      )}
      {lc.activePanel !== 'none' && lc.activePanel !== 'margin' && (
        <div className="max-h-[250px] overflow-y-auto" style={{ borderTop: '1px solid var(--db-border, #dee2e6)', background: 'var(--db-surface, #fff)' }}>
          {lc.activePanel === 'inventory' && <InventoryPanel itemIds={lc.inventoryItemIds} itemCodes={[]} />}
          {lc.activePanel === 'spec' && <SpecPanel itemId={lc.selectedLineRecord?._itemId ?? null} itemCode={lc.selectedLineRecord?.item_code ?? ''} />}
          {lc.activePanel === 'xref' && <XRefPanel itemId={lc.selectedLineRecord?._itemId ?? null} itemCode={lc.selectedLineRecord?.item_code ?? ''} />}
        </div>
      )}
    </>
  );

  return (
    <DataGrid
      hideToolbar
      disableReorder
      records={lc.activePanel === 'margin' ? [] : lc.records}
      columns={lc.richColumns.map(c => c.name)}
      richColumns={lc.richColumns}
      colWidths={lc.colWidths}
      fieldBehaviors={lc.fieldBehaviors}
      selectedId={lc.selectedId}
      selectedRowIds={lc.selectedLineIds}
      sort={null}
      onSelectRecord={(id) => { lc.setSelectedId(id); if (id != null) lc.setSelectedLineIds(new Set([id])); }}
      onToggleRow={(id) => { lc.setSelectedLineIds(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; }); }}
      onSelectAll={() => { lc.setSelectedLineIds(new Set(lc.records.map(r => r.id).filter((id): id is number => id != null))); }}
      onClearSelection={() => lc.setSelectedLineIds(new Set())}
      onSort={() => {}}
      onColumnDrop={() => {}}
      onResizeStart={() => {}}
      onCellEdit={lc.canEdit ? lc.handleCellEdit : undefined}
      numId={(v: unknown) => typeof v === 'number' ? v : null}
      theme={lc.theme}
      fontSize={12}
      footerBar={footerBar}
      panelContent={panelContent}
      onHeaderClick={lc.canEdit ? lc.openBulkEdit : undefined}
      headerEditField={lc.bulkEditField}
      headerEditValue={lc.bulkEditValue}
      onHeaderEditChange={lc.setBulkEditValue}
      onHeaderEditApply={lc.applyBulkEdit}
      onHeaderEditCancel={lc.cancelBulkEdit}
    />
  );
};

export default LineCardRenderer;
