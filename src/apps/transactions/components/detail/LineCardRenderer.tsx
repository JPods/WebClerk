/* LastChecked: 2026-08-03 | WhereUsed: TransactionDetail | WhoCreated: Claude */
import React, { useState, useCallback } from 'react';
import DataGrid from '@/components/common/DataGrid';
import { useLineCard } from '@/hooks/useLineCard';
import { useWindowManager } from '@/context/WindowManagerContext';
import InventoryPanel from '../panels/InventoryPanel';
import MarginPanel from '../panels/MarginPanel';
import SpecPanel from '../panels/SpecPanel';
import XRefPanel from '../panels/XRefPanel';
import { TransactionItemSearch, resolveItemCode, resolveItemDescription, resolveUnitPrice, resolveUnitCost } from '../TransactionItemSearch';
import type { ItemSearchResult } from '../TransactionItemSearch';
import { getNextLineNumber } from '../../utils/lineHelpers';
import type { LineCardSection } from '@/hooks/useDetailLayout';
import type { TransactionLine } from '../../types/transactionTypes';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface LineCardRendererProps {
  section: LineCardSection;
  data: any;
  isEditing: boolean;
  isLocked: boolean;
  onLinesChange: (lines: TransactionLine[]) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/** Render the line card -- DataGrid with line card config, no LinesCard component */
const LineCardRenderer: React.FC<LineCardRendererProps> = ({ section, data, isEditing, isLocked, onLinesChange }) => {
  const lines = data?.lines || [];
  const windowManager = useWindowManager();
  const [showItemSearch, setShowItemSearch] = useState(false);
  const isSellSide = section.family === 'sell';

  const handleAddItem = useCallback((item: ItemSearchResult, quantity: number) => {
    const itemId = item.id || item.item_id || item.itemId || 0;
    const itemCode = resolveItemCode(item);
    const description = resolveItemDescription(item);
    const unitPrice = resolveUnitPrice(item, data?.price_level);
    const unitCost = resolveUnitCost(item);

    const newLine: any = {
      id: -Date.now(), // temp negative id for new lines
      line_number: getNextLineNumber(lines),
      item_fk: itemId,
      item_fk_id: itemId,
      price_level: data?.price_level || '',
      status: '',
      is_active: true,
      item: { item_id: itemId, ida_item: itemCode, description, unit_measure: item.unit_of_measure || item.unitOfMeasure || item.unit_measure || 'EA' },
      quantity: { active: quantity, remaining: quantity, staged: quantity },
      price: { unit: unitPrice, extended: unitPrice * quantity, discount_percent: 0 },
      cost: { unit: unitCost, extended: unitCost * quantity },
      comments: {},
      config: {},
      _dirty: true,
    };

    onLinesChange([...lines, newLine]);
  }, [lines, data?.price_level, onLinesChange]);

  const lc = useLineCard({
    lines,
    family: section.family,
    isEditing,
    isLocked,
    priceLevel: data?.price_level,
    onLinesChange,
    onOpenItem: (itemId, itemCode) => {
      const path = `/db/item?id=${itemId}`;
      windowManager.ensureWindow(path, `Item ${itemCode || itemId}`, { maximized: false });
    },
  });

  const formatCurrency = (v: number) => '$' + v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const formatNumber = (v: number) => v.toLocaleString();

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
    <div className="bg-slate-50 dark:bg-slate-900/50 border-t-2 border-slate-300 dark:border-slate-600 text-xs px-2 py-2">
      <div className="flex items-center gap-4 mb-1">
        <span className="font-medium text-slate-600">Lns: {lc.lineCount}</span>
        <span className="text-slate-600">Items: {formatNumber(footerQty)}</span>
        {selectionLabel && <span className="text-blue-600 font-medium">{selectionLabel}</span>}
        {lc.selectedId != null && (
          <span className="flex items-center gap-1 ml-2 text-[10px]">
            <button type="button" onClick={() => { const line = lc.records.find(r => r.id === lc.selectedId); if (line?._line) lc.setSelectedId(line.id); }}
              className="px-1.5 py-0.5 text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded" title="Edit line details">edit</button>
            {lc.canEdit && (
              <button type="button" onClick={() => { lc.selectedLineIds.forEach(id => onLinesChange?.(lines.filter((_: any, i: number) => lc.records[i]?.id !== id))); lc.setSelectedLineIds(new Set()); }}
                className="px-1.5 py-0.5 text-slate-500 hover:text-red-600 hover:bg-red-50 rounded" title="Delete selected (Del)">del</button>
            )}
          </span>
        )}
        <span className="flex-1" />
        {lc.canEdit && (
          <button type="button" onClick={() => setShowItemSearch(prev => !prev)}
            className={`px-2 py-0.5 text-[10px] font-medium rounded transition-colors ${showItemSearch ? 'bg-green-600 text-white' : 'text-green-600 hover:bg-green-50 border border-green-300'}`}
            title="Search and add items">+ Item</button>
        )}
        <span className="flex items-center gap-1 text-[9px] font-bold">
          <button type="button" onClick={() => lc.togglePanel('inventory')}
            className={`px-1.5 py-0.5 rounded transition-colors ${lc.activePanel === 'inventory' ? 'bg-blue-600 text-white' : 'text-slate-500 hover:text-blue-600 hover:bg-blue-50'}`}
            title="Inventory lookup (L)">L</button>
          <button type="button" onClick={() => lc.togglePanel('spec')}
            className={`px-1.5 py-0.5 rounded transition-colors ${lc.activePanel === 'spec' ? 'bg-blue-600 text-white' : 'text-slate-500 hover:text-blue-600 hover:bg-blue-50'}`}
            title="Specification (S)">S</button>
          <button type="button" onClick={() => lc.togglePanel('xref')}
            className={`px-1.5 py-0.5 rounded transition-colors ${lc.activePanel === 'xref' ? 'bg-blue-600 text-white' : 'text-slate-500 hover:text-blue-600 hover:bg-blue-50'}`}
            title="Cross-references (XR)">XR</button>
          <button type="button" onClick={() => lc.togglePanel('margin')}
            className={`px-1.5 py-0.5 rounded transition-colors ${lc.activePanel === 'margin' ? 'bg-green-600 text-white' : 'text-slate-500 hover:text-green-600 hover:bg-green-50'}`}
            title="Margin view (M)">M</button>
        </span>
      </div>
      <div className="flex items-center gap-3 justify-end italic">
        <span className="text-slate-400">Tax:</span>
        <span className="font-mono text-slate-700 w-16 text-right">{formatCurrency(data?.totals?.tax ?? 0)}</span>
        <span className="text-slate-400">Ship:</span>
        <span className="font-mono text-slate-700 w-16 text-right">{formatCurrency(data?.totals?.shipping ?? 0)}</span>
        <span className="text-slate-400">Other:</span>
        <span className="font-mono text-slate-700 w-16 text-right">{formatCurrency(data?.totals?.other ?? 0)}</span>
        <span className="text-slate-300 not-italic">|</span>
        <span className="text-slate-500">Deposit:</span>
        <span className="font-bold text-slate-900 w-20 text-right">{formatCurrency(data?.totals?.deposit ?? 0)}</span>
        {footerBacklog > 0 && (
          <>
            <span className="text-red-500">Backlog:</span>
            <span className="font-bold text-red-600 w-20 text-right">{formatCurrency(footerBacklog)}</span>
          </>
        )}
        <span className="text-slate-700">Total:</span>
        <span className="font-bold text-slate-900 w-24 text-right">{formatCurrency(footerExtended)}</span>
      </div>
    </div>
  );

  const panelContent = (
    <>
      {showItemSearch && lc.canEdit && (
        <div className="border-t-2 border-green-300 bg-white dark:bg-slate-900 p-3">
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
      {lc.activePanel !== 'none' && lc.activePanel !== 'margin' && (
        <div className="border-t border-slate-200 bg-white max-h-[250px] overflow-y-auto">
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
