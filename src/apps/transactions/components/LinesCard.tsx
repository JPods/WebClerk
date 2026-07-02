/* LastChecked: 2026-06-30 | WhereUsed: OrderDetail, InvoiceDetail, ProposalDetail, PurchaseDetail, WorkorderDetail, ReceiptDetail | WhoCreated: Unknown */
// Shared line items component for all transaction types.
// Uses DataGrid for rendering; conditional columns based on transactionType (sell-side vs exec-side).
import React from "react";
import {
  FaShoppingCart,
  FaChevronDown,
  FaChevronRight,
  FaStickyNote,
  FaEdit,
  FaExternalLinkAlt,
  FaCopy,
  FaTrash,
  FaBoxes,
} from "react-icons/fa";
import LineDetailsModal from "../components/LineDetailsModal";
import InventoryCheckDialog from "../components/InventoryCheckDialog";
import OrderItemSearch from "../models/order/components/OrderItemSearch";
import { lineKey } from "../utils/lineHelpers";
import { withDevIdentifier } from '@/components/common/DevIdentifier';
import { getModelDetailPath, getModelWindowTitle } from '@/apps/common/components/panels/getModelDetailPath';
import { useWindowManager } from '@/context/WindowManagerContext';
import DataGrid, { type RichColumn } from '@/components/common/DataGrid';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface LinesCardProps {
  lines: any[];
  isEditing: boolean;
  isLocked?: boolean;
  priceLevel?: string | null;
  transactionType?: string;
  onDeleteLine?: (lineId: number) => void;
  onUpdateLine?: (lineId: number, field: string, value: unknown) => void;
  onUpdateFullLine?: (line: any) => void;
  onDuplicateLine?: (lineId: number) => void;
  onAddItem?: (item: any, quantity: number) => void;
  onLinesChange?: (lines: any[]) => void;
}

// ---------------------------------------------------------------------------
// Theme for DataGrid (matches the green-header style of the original table)
// ---------------------------------------------------------------------------

const linesTheme = {
  surface: '#fff',
  surfaceAlt: '#f8fafc',
  text: '#1e293b',
  textMuted: '#64748b',
  border: '#e2e8f0',
  borderLight: '#f1f5f9',
  accent: '#2563eb',
  accentGold: '#d97706',
  accentRed: '#dc2626',
  rowActive: '#2563eb',
  rowChecked: '#eff6ff',
  rowHover: '#f8fafc',
  inputBg: '#fff',
  inputBorder: '#cbd5e1',
  resizeHandle: '#94a3b8',
};

const darkLinesTheme = {
  surface: '#1e293b',
  surfaceAlt: '#0f172a',
  text: '#f1f5f9',
  textMuted: '#94a3b8',
  border: '#334155',
  borderLight: '#1e293b',
  accent: '#3b82f6',
  accentGold: '#f59e0b',
  accentRed: '#ef4444',
  rowActive: '#2563eb',
  rowChecked: 'rgba(59,130,246,0.1)',
  rowHover: 'rgba(59,130,246,0.05)',
  inputBg: '#334155',
  inputBorder: '#475569',
  resizeHandle: '#64748b',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const formatCurrency = (value?: number | null): string => {
  if (value === undefined || value === null) return "--";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(value);
};

const formatNumber = (value?: number | null): string => {
  if (value === undefined || value === null) return "--";
  return value.toLocaleString();
};

/** Extract a flat record from a nested line for DataGrid consumption. */
function flattenLine(line: any, idx: number, isSellSide: boolean): any {
  const lineRecord = line as unknown as Record<string, unknown>;
  const itemCode = String(lineRecord.ida_item ?? line.item?.ida_item ?? "--");
  const description = String(lineRecord.description ?? line.item?.description ?? "--");
  const qty = Number(lineRecord.qty ?? line.quantity?.active ?? 0);
  const remaining = Number(line.quantity?.remaining ?? 0);
  const uom = String(lineRecord.unit_measure ?? line.item?.unit_measure ?? "EA");

  const priceRecord = lineRecord.price as Record<string, unknown> | undefined;
  const unitPrice = Number(priceRecord?.sell ?? priceRecord?.unit ?? line.price?.unit ?? 0);

  const costRecord = lineRecord.cost as Record<string, unknown> | undefined;
  const unitCost = Number(costRecord?.unit ?? line.cost?.unit ?? 0);

  const extended = isSellSide
    ? Number(priceRecord?.extended ?? line.price?.extended ?? qty * unitPrice)
    : Number(costRecord?.extended ?? line.cost?.extended ?? qty * unitCost);

  const notesObj = lineRecord.notes as Record<string, string> | undefined;
  const hasNotes = notesObj && (notesObj.public || notesObj.internal || notesObj.warehouse);

  return {
    id: lineKey(line, idx),
    _idx: idx,
    _line: line, // keep original for actions
    item_code: itemCode,
    description,
    qty,
    remaining,
    uom,
    unit_price: unitPrice,
    unit_cost: unitCost,
    extended,
    hasNotes: !!hasNotes,
    notesObj,
    _itemId: Number(line.item_id ?? line.item?.id ?? line.item?.item_id ?? 0),
    _itemIsActive: line.item?.is_active !== false,
  };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const LinesCard: React.FC<LinesCardProps> = ({
  lines,
  isEditing,
  isLocked = false,
  priceLevel,
  transactionType,
  onDeleteLine,
  onUpdateLine,
  onUpdateFullLine,
  onDuplicateLine,
  onAddItem,
  onLinesChange,
}) => {
  const windowManager = useWindowManager();

  // ── Transaction-type awareness ────────────────────────────────────
  const transType = (transactionType ?? '').toLowerCase();
  const isExecSide = ['purchase', 'workorder', 'receipt'].includes(transType);
  const isSellSide = !isExecSide;

  const [pendingDeleteId, setPendingDeleteId] = React.useState<number | null>(null);
  const [expandedRows, setExpandedRows] = React.useState<Set<number>>(new Set());
  const [selectedLine, setSelectedLine] = React.useState<any | null>(null);
  const [showLineModal, setShowLineModal] = React.useState(false);
  const [selectedLineIds, setSelectedLineIds] = React.useState<Set<number>>(new Set());
  const [inventoryCheck, setInventoryCheck] = React.useState<{ itemId: number; itemCode: string } | null>(null);
  const [sort, setSort] = React.useState<{ field: string; direction: 'asc' | 'desc' } | null>(null);
  const [selectedId, setSelectedId] = React.useState<number | null>(null);

  // Detect dark mode from document
  const isDark = typeof document !== 'undefined' && document.documentElement.classList.contains('dark');
  const theme = isDark ? darkLinesTheme : linesTheme;

  const canEdit = isEditing && !isLocked;

  const lineCount = lines.length;
  const totalQty = lines.reduce((sum, l) => {
    const lRecord = l as unknown as Record<string, unknown>;
    const qty = lRecord.qty ?? l.quantity?.active ?? 0;
    return sum + Number(qty);
  }, 0);

  // ── Flatten lines for DataGrid ────────────────────────────────────
  const records = React.useMemo(
    () => lines.map((l, i) => flattenLine(l, i, isSellSide)),
    [lines, isSellSide]
  );

  // ── Delete handler ────────────────────────────────────────────────
  const handleDeleteClick = (lineId: number) => {
    if (pendingDeleteId === lineId) {
      onDeleteLine?.(lineId);
      setPendingDeleteId(null);
    } else {
      setPendingDeleteId(lineId);
    }
  };

  const handleCancelPending = () => {
    setPendingDeleteId(null);
  };

  // ── Internal field-update handler (used when onUpdateLine not provided) ──
  const applyFieldUpdate = (line: any, field: string, value: unknown): any => {
    const updated = { ...line, _dirty: true };
    switch (field) {
      case "qty": {
        const newQty = Number(value);
        const hasParent = !!(updated.refs?.source?.converted_from || updated.metadata?.parent_link);
        const currentStaged = Number(updated.quantity?.staged ?? 0);
        const staged = hasParent && currentStaged > 0 ? currentStaged : newQty;
        const remaining = newQty;
        const result: any = {
          ...updated,
          quantity: { ...updated.quantity, active: newQty, staged, remaining },
        };
        if (updated.price) {
          result.price = { ...updated.price, extended: newQty * (updated.price?.unit ?? 0) };
        }
        if (isExecSide && updated.cost) {
          result.cost = { ...updated.cost, extended: newQty * (updated.cost?.unit ?? 0) };
        }
        return result;
      }
      case "description":
        return { ...updated, item: { ...updated.item, description: String(value) } };
      case "unit_price": {
        const newPrice = Number(value);
        const qty = updated.quantity?.active ?? updated.quantity?.staged ?? 0;
        return {
          ...updated,
          price: { ...updated.price, unit: newPrice, extended: qty * newPrice },
        };
      }
      case "unit_cost": {
        const newCost = Number(value);
        const qty = updated.quantity?.active ?? updated.quantity?.staged ?? 0;
        return {
          ...updated,
          cost: { ...updated.cost, unit: newCost, extended: qty * newCost },
        };
      }
      default:
        return updated;
    }
  };

  // ── Cell edit handler for DataGrid ────────────────────────────────
  const handleCellEdit = React.useCallback((recordId: number, field: string, value: unknown) => {
    if (!canEdit) return;

    if (onUpdateLine) {
      onUpdateLine(recordId, field, value);
    } else if (onLinesChange) {
      const newLines = lines.map((l: any, i: number) => {
        if (lineKey(l, i) !== recordId) return l;
        return applyFieldUpdate(l, field, value);
      });
      onLinesChange(newLines);
    }
  }, [canEdit, onUpdateLine, onLinesChange, lines, isExecSide]);

  // ── Line details modal ────────────────────────────────────────────
  const handleOpenLineDetails = (line: any) => {
    setSelectedLine(line);
    setShowLineModal(true);
  };

  const handleLineModalSave = (updatedLine: any) => {
    if (onUpdateFullLine) {
      onUpdateFullLine(updatedLine);
    }
  };

  const handleOpenItem = (itemId: number, ida?: string) => {
    const path = getModelDetailPath("item", itemId);
    const title = getModelWindowTitle("item", itemId, ida);
    windowManager.ensureWindow(path, title, { maximized: false });
  };

  // ── Bulk actions ──────────────────────────────────────────────────
  const handleBulkDelete = () => {
    selectedLineIds.forEach((id) => onDeleteLine?.(id));
    setSelectedLineIds(new Set());
  };

  // ── Sort handler ──────────────────────────────────────────────────
  const handleSort = React.useCallback((field: string) => {
    setSort(prev => {
      if (prev?.field === field) {
        return prev.direction === 'asc' ? { field, direction: 'desc' as const } : null;
      }
      return { field, direction: 'asc' as const };
    });
  }, []);

  // ── Column definitions ────────────────────────────────────────────
  const richColumns = React.useMemo((): RichColumn[] => {
    const cols: RichColumn[] = [];

    // Expand/collapse column
    cols.push({
      name: '_expand',
      field: '_expand',
      width: '32px',
      sortable: false,
      cell: (row: any) => {
        if (row.hasNotes) {
          return (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); toggleRowExpansion(row.id); }}
              className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
              title={expandedRows.has(row.id) ? "Collapse notes" : "Expand notes"}
            >
              {expandedRows.has(row.id) ? <FaChevronDown size={12} /> : <FaChevronRight size={12} />}
            </button>
          );
        }
        return <span className="p-1 text-slate-200 dark:text-slate-700"><FaStickyNote size={10} /></span>;
      },
    });

    // Item Code
    cols.push({
      name: 'item_code',
      field: 'item_code',
      width: '120px',
      sortable: true,
      cell: (row: any) => (
        <span data-wc-field="item_code" className="font-mono font-medium text-slate-900 dark:text-white">
          {row.item_code}
        </span>
      ),
    });

    // Description
    cols.push({
      name: 'description',
      field: 'description',
      width: '200px',
      sortable: true,
      cell: (row: any) => {
        const full = String(row._line?.item?.description ?? row.description ?? '--');
        const truncated = full.length > 15 ? full.substring(0, 15) + '...' : full;
        return (
          <span
            data-wc-field="description"
            className="text-slate-600 dark:text-slate-300"
            title={full.length > 15 ? full : undefined}
          >
            {truncated}
          </span>
        );
      },
    });

    // Active (qty) — inline editable
    cols.push({
      name: 'qty',
      field: 'qty',
      width: '90px',
      sortable: true,
      cell: (row: any) => {
        if (canEdit && row._itemIsActive) {
          return (
            <QtyInput
              lineId={row.id}
              value={row.qty}
              onSave={(val) => handleCellEdit(row.id, 'qty', val)}
            />
          );
        }
        return <span data-wc-field="qty" className="text-right w-full block">{formatNumber(row.qty)}</span>;
      },
    });

    // Remaining
    cols.push({
      name: 'remaining',
      field: 'remaining',
      width: '90px',
      sortable: true,
      cell: (row: any) => (
        <span data-wc-field="remaining" className="text-right w-full block text-slate-500 dark:text-slate-400">
          {formatNumber(row.remaining)}
        </span>
      ),
    });

    // UOM
    cols.push({
      name: 'uom',
      field: 'uom',
      width: '70px',
      sortable: true,
      cell: (row: any) => (
        <span data-wc-field="uom" className="text-right w-full block text-slate-600 dark:text-slate-300">
          {row.uom}
        </span>
      ),
    });

    // Unit Price (sell-side only)
    if (isSellSide) {
      cols.push({
        name: 'unit_price',
        field: 'unit_price',
        width: '110px',
        sortable: true,
        cell: (row: any) => {
          if (canEdit) {
            return (
              <EditableCell
                lineId={row.id}
                field="unit_price"
                value={row.unit_price}
                displayValue={formatCurrency(row.unit_price)}
                isNumeric
                onSave={(val) => handleCellEdit(row.id, 'unit_price', Number(val))}
              />
            );
          }
          return (
            <span data-wc-field="unit_price" className="text-right w-full block text-slate-900 dark:text-white">
              {formatCurrency(row.unit_price)}
            </span>
          );
        },
      });
    }

    // Unit Cost
    cols.push({
      name: 'unit_cost',
      field: 'unit_cost',
      width: '110px',
      sortable: true,
      cell: (row: any) => {
        if (canEdit && isExecSide) {
          return (
            <EditableCell
              lineId={row.id}
              field="unit_cost"
              value={row.unit_cost}
              displayValue={formatCurrency(row.unit_cost)}
              isNumeric
              onSave={(val) => handleCellEdit(row.id, 'unit_cost', Number(val))}
            />
          );
        }
        return (
          <span data-wc-field="unit_cost" className="text-right w-full block text-slate-600 dark:text-slate-300">
            {formatCurrency(row.unit_cost)}
          </span>
        );
      },
    });

    // Extended
    cols.push({
      name: 'extended',
      field: 'extended',
      width: '110px',
      sortable: true,
      cell: (row: any) => (
        <span data-wc-field="extended" className="text-right w-full block font-medium text-slate-900 dark:text-white">
          {formatCurrency(row.extended)}
        </span>
      ),
    });

    // Actions column
    cols.push({
      name: '_actions',
      field: '_actions',
      width: '140px',
      sortable: false,
      cell: (row: any) => (
        <LineActions
          row={row}
          canEdit={canEdit}
          pendingDeleteId={pendingDeleteId}
          onOpenDetails={() => handleOpenLineDetails(row._line)}
          onOpenItem={() => {
            if (row._itemId) handleOpenItem(row._itemId, row.item_code !== '--' ? row.item_code : undefined);
          }}
          onInventoryCheck={() => {
            if (row._itemId && row.item_code !== '--') {
              setInventoryCheck({ itemId: row._itemId, itemCode: row.item_code });
            }
          }}
          onDuplicate={() => row._line?.id && onDuplicateLine?.(row._line.id)}
          onDelete={() => handleDeleteClick(row._line?.id)}
          onCancelDelete={handleCancelPending}
          hasDuplicate={!!onDuplicateLine && !!row._line?.id}
          hasDelete={!!onDeleteLine && !!row._line?.id}
          hasItemLink={row.item_code !== '--' && !!row._itemId}
        />
      ),
    });

    return cols;
  }, [isSellSide, isExecSide, canEdit, expandedRows, pendingDeleteId, handleCellEdit]);

  // ── Column field names for DataGrid ───────────────────────────────
  const columnFields = React.useMemo(
    () => richColumns.map(c => c.name),
    [richColumns]
  );

  const colWidths = React.useMemo(() => {
    const w: Record<string, number> = {};
    richColumns.forEach(c => {
      if (c.width) w[c.name] = parseInt(c.width, 10) || 100;
    });
    return w;
  }, [richColumns]);

  const fieldBehaviors = React.useMemo(() => {
    const b: Record<string, any> = {};
    b.qty = { type: 'number' };
    b.remaining = { type: 'number' };
    b.unit_price = { type: 'currency' };
    b.unit_cost = { type: 'currency' };
    b.extended = { type: 'currency' };
    b._expand = { type: 'readonly' };
    b._actions = { type: 'readonly' };
    b.item_code = { type: 'readonly' };
    b.description = { type: 'readonly' };
    b.uom = { type: 'readonly' };
    return b;
  }, []);

  // ── Expand/collapse ───────────────────────────────────────────────
  const toggleRowExpansion = (lineId: number) => {
    setExpandedRows(prev => {
      const next = new Set(prev);
      next.has(lineId) ? next.delete(lineId) : next.add(lineId);
      return next;
    });
  };

  // ── Noop handlers for DataGrid (we manage selection internally) ──
  const noop = React.useCallback(() => {}, []);
  const numId = React.useCallback((v: unknown) => (typeof v === 'number' ? v : null), []);

  return (
    <div className="space-y-6 my-2" data-wc="lines-card">
      {/* Line Details Drawer (right sidebar) */}
      {showLineModal && (
        <div className="pointer-events-none fixed inset-0 z-[200000] flex items-stretch justify-end">
          <div
            className="pointer-events-auto fixed inset-0"
            onClick={() => { setShowLineModal(false); setSelectedLine(null); }}
          />
          <div className="pointer-events-auto ml-auto flex h-full w-full max-h-screen flex-col overflow-hidden border-l border-blue-200 dark:border-blue-800 bg-white dark:bg-slate-800 shadow-2xl no-scrollbar sm:w-[640px] lg:w-[50vw] lg:min-w-[520px]">
            <LineDetailsModal
              line={selectedLine}
              isOpen={showLineModal}
              isEditing={canEdit}
              onClose={() => { setShowLineModal(false); setSelectedLine(null); }}
              onSave={handleLineModalSave}
              onOpenItem={handleOpenItem}
            />
          </div>
        </div>
      )}

      {/* Bulk Actions Bar */}
      {canEdit && selectedLineIds.size > 0 && (
        <div className="flex items-center gap-4 px-2 py-1 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <span className="text-xs font-medium text-blue-700 dark:text-blue-300">
            {selectedLineIds.size} line{selectedLineIds.size > 1 ? "s" : ""} selected
          </span>
          <button
            onClick={handleBulkDelete}
            className="px-3 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-colors"
          >
            Delete Selected
          </button>
          <button
            onClick={() => setSelectedLineIds(new Set())}
            className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition-colors"
          >
            Clear Selection
          </button>
        </div>
      )}

      {/* Item Search Panel */}
      {isEditing && !isLocked && onLinesChange && (
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-2">
          <OrderItemSearch
            onAddItem={(item, quantity) => {
              const itemId = item.id ?? item.item_id ?? item.itemId ?? null;
              const idaItem = item.ida_item ?? item.item_code ?? item.sku ?? item.item_num ?? item.itemNum ?? "";
              const description = item.description ?? item.description_text ?? item.name ?? "";
              const unitMeasure = item.unit_of_measure ?? item.unitOfMeasure ?? item.unit_measure ?? "EA";
              const level = priceLevel || "retail";
              let unitPrice = 0;
              if (typeof item.price === "number") {
                unitPrice = item.price;
              } else if (typeof item.price === "string") {
                unitPrice = parseFloat(item.price) || 0;
              } else if (item.price && typeof item.price === "object") {
                const priceObj = item.price as Record<string, unknown>;
                let levelValue = priceObj[level];
                if (levelValue === undefined || levelValue === null) {
                  if (level === "retail") levelValue = priceObj.base;
                  else if (level === "base") levelValue = priceObj.retail;
                  else levelValue = priceObj.base ?? priceObj.retail;
                }
                unitPrice = Number(levelValue ?? 0);
              }
              if (unitPrice === 0) {
                unitPrice = Number(item.unit_price ?? item.priceA ?? item.price_a ?? 0);
              }
              let unitCost = 0;
              if (typeof item.cost === "number") {
                unitCost = item.cost;
              } else if (typeof item.cost === "string") {
                unitCost = parseFloat(item.cost) || 0;
              } else if (item.cost && typeof item.cost === "object") {
                const costObj = item.cost as Record<string, unknown>;
                unitCost = Number(costObj.avg ?? costObj.last ?? costObj.unit ?? 0);
              }
              if (unitCost === 0) {
                unitCost = Number(item.unit_cost ?? item.costA ?? 0);
              }
              const newLine: any = {
                item: { item_id: itemId, ida_item: idaItem, description, unit_measure: unitMeasure },
                quantity: { active: quantity, staged: quantity, remaining: quantity },
                ...(isSellSide ? { price: { unit: unitPrice, extended: unitPrice * quantity } } : {}),
                cost: { unit: unitCost, ...(isExecSide ? { extended: unitCost * quantity } : {}) },
              };
              onLinesChange?.([...lines, newLine]);
              onAddItem?.(item, quantity);
            }}
          />
        </div>
      )}

      {/* Lines DataGrid */}
      {!lines.length ? (
        <div className="text-center py-12 text-slate-400">
          <FaShoppingCart size={32} className="mx-auto mb-3 opacity-50" />
          <p>No line items on this order</p>
          {isEditing && (
            <p className="mt-2 text-xs">Use the search above to find and add products</p>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto cus-bg-purple-light" data-wc-field="lines-table">
          <DataGrid
            records={records}
            columns={columnFields}
            richColumns={richColumns}
            colWidths={colWidths}
            fieldBehaviors={fieldBehaviors}
            selectedId={selectedId}
            selectedRowIds={selectedLineIds}
            sort={sort}
            onSelectRecord={(id) => setSelectedId(id)}
            onToggleRow={(id) => {
              setSelectedLineIds(prev => {
                const next = new Set(prev);
                next.has(id) ? next.delete(id) : next.add(id);
                return next;
              });
            }}
            onSelectAll={() => {
              setSelectedLineIds(new Set(records.map(r => r.id).filter((id): id is number => id != null)));
            }}
            onClearSelection={() => setSelectedLineIds(new Set())}
            onSort={handleSort}
            onColumnDrop={noop as any}
            onResizeStart={noop as any}
            onCellEdit={canEdit ? handleCellEdit : undefined}
            numId={numId}
            theme={theme}
            fontSize={12}
          />

          {/* Expanded notes rows — rendered below DataGrid as overlay panels */}
          {records.filter(r => r.hasNotes && expandedRows.has(r.id)).map(row => (
            <div key={`notes-${row.id}`} className="bg-amber-50 dark:bg-amber-900/20 px-6 py-3 border-t border-amber-200 dark:border-amber-800">
              <div className="flex flex-wrap gap-4 text-xs">
                {row.notesObj?.public && (
                  <div className="flex-1 min-w-50">
                    <span className="font-medium text-amber-700 dark:text-amber-400">Public: </span>
                    <span className="text-slate-600 dark:text-slate-300">{row.notesObj.public}</span>
                  </div>
                )}
                {row.notesObj?.internal && (
                  <div className="flex-1 min-w-50">
                    <span className="font-medium text-blue-700 dark:text-blue-400">Internal: </span>
                    <span className="text-slate-600 dark:text-slate-300">{row.notesObj.internal}</span>
                  </div>
                )}
                {row.notesObj?.warehouse && (
                  <div className="flex-1 min-w-50">
                    <span className="font-medium text-green-700 dark:text-green-400">Warehouse: </span>
                    <span className="text-slate-600 dark:text-slate-300">{row.notesObj.warehouse}</span>
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Footer totals */}
          <div className="bg-slate-50 dark:bg-slate-900/50 border-t-2 border-slate-300 dark:border-slate-600 flex items-center text-xs px-2 py-2 gap-4">
            <span className="font-medium text-slate-600 dark:text-slate-300">
              {lineCount} {lineCount === 1 ? "line" : "lines"}
            </span>
            <span className="text-slate-600 dark:text-slate-300">
              {formatNumber(totalQty)} items
            </span>
            <span className="flex-1" />
            <span className="font-medium text-slate-500 dark:text-slate-400">Total:</span>
            <span className="font-bold text-slate-900 dark:text-white" data-wc-field="lines-total">
              {formatCurrency(
                lines.reduce((sum, l) => {
                  const lRecord = l as unknown as Record<string, unknown>;
                  if (isSellSide) {
                    const lPrice = lRecord.price as Record<string, unknown> | undefined;
                    const ext = lPrice?.extended ?? l.price?.extended ?? 0;
                    return sum + Number(ext);
                  } else {
                    const lCost = lRecord.cost as Record<string, unknown> | undefined;
                    const ext = lCost?.extended ?? l.cost?.extended ?? 0;
                    return sum + Number(ext);
                  }
                }, 0),
              )}
            </span>
          </div>
        </div>
      )}

      {/* Inventory check dialog */}
      {inventoryCheck && (
        <InventoryCheckDialog
          itemId={inventoryCheck.itemId}
          itemCode={inventoryCheck.itemCode}
          onClose={() => setInventoryCheck(null)}
        />
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Sub-components: QtyInput (always-visible input for quantity)
// ---------------------------------------------------------------------------

const QtyInput: React.FC<{ lineId: number; value: number; onSave: (val: number) => void }> = ({
  lineId, value, onSave,
}) => {
  const [localVal, setLocalVal] = React.useState(String(value));
  const [editing, setEditing] = React.useState(false);

  React.useEffect(() => {
    if (!editing) setLocalVal(String(value));
  }, [value, editing]);

  return (
    <input
      type="text"
      inputMode="decimal"
      value={localVal}
      onChange={(e) => { setEditing(true); setLocalVal(e.target.value); }}
      onFocus={() => setEditing(true)}
      onBlur={() => {
        setEditing(false);
        const n = Number(localVal);
        if (!isNaN(n) && n !== value) onSave(n);
      }}
      onKeyDown={(e) => {
        if (e.key === 'Enter') {
          (e.target as HTMLInputElement).blur();
        } else if (e.key === 'Escape') {
          setEditing(false);
          setLocalVal(String(value));
        }
      }}
      data-wc-field="qty"
      className="w-20 px-2 py-0.5 text-xs text-right border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
    />
  );
};

// ---------------------------------------------------------------------------
// Sub-component: EditableCell (double-click to edit)
// ---------------------------------------------------------------------------

const EditableCell: React.FC<{
  lineId: number;
  field: string;
  value: number;
  displayValue: string;
  isNumeric?: boolean;
  onSave: (val: string) => void;
}> = ({ lineId, field, value, displayValue, isNumeric, onSave }) => {
  const [editing, setEditing] = React.useState(false);
  const [localVal, setLocalVal] = React.useState(String(value));

  if (editing) {
    return (
      <input
        type="text"
        inputMode={isNumeric ? "decimal" : "text"}
        value={localVal}
        onChange={(e) => setLocalVal(e.target.value)}
        onBlur={() => { setEditing(false); onSave(localVal); }}
        onKeyDown={(e) => {
          if (e.key === 'Enter') { setEditing(false); onSave(localVal); }
          else if (e.key === 'Escape') { setEditing(false); setLocalVal(String(value)); }
        }}
        autoFocus
        data-wc-field={field}
        className="w-full px-2 py-1 text-xs border border-blue-500 rounded bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        style={isNumeric ? { textAlign: "right" } : {}}
      />
    );
  }

  return (
    <span
      data-wc-field={field}
      className="text-right w-full block cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 px-1 py-0.5 rounded"
      onDoubleClick={() => { setEditing(true); setLocalVal(String(value)); }}
      title="Double-click to edit"
    >
      {displayValue}
    </span>
  );
};

// ---------------------------------------------------------------------------
// Sub-component: LineActions
// ---------------------------------------------------------------------------

const LineActions: React.FC<{
  row: any;
  canEdit: boolean;
  pendingDeleteId: number | null;
  onOpenDetails: () => void;
  onOpenItem: () => void;
  onInventoryCheck: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
  onCancelDelete: () => void;
  hasDuplicate: boolean;
  hasDelete: boolean;
  hasItemLink: boolean;
}> = ({ row, canEdit, pendingDeleteId, onOpenDetails, onOpenItem, onInventoryCheck, onDuplicate, onDelete, onCancelDelete, hasDuplicate, hasDelete, hasItemLink }) => (
  <div className="flex items-center justify-center gap-1">
    <button type="button" onClick={onOpenDetails} className="p-1 text-slate-400 hover:text-blue-500 transition-colors" title="View/Edit line details">
      <FaEdit size={14} />
    </button>
    {hasItemLink && (
      <button type="button" onClick={onInventoryCheck} className="p-1 text-slate-400 hover:text-amber-500 transition-colors" title="Check inventory">
        <FaBoxes size={13} />
      </button>
    )}
    {hasItemLink && (
      <button type="button" onClick={onOpenItem} className="p-1 text-slate-400 hover:text-green-500 transition-colors" title="Open item in new window">
        <FaExternalLinkAlt size={12} />
      </button>
    )}
    {canEdit && hasDuplicate && (
      <button type="button" onClick={onDuplicate} className="p-1 text-slate-400 hover:text-purple-500 transition-colors" title="Duplicate line">
        <FaCopy size={12} />
      </button>
    )}
    {canEdit && hasDelete && (
      pendingDeleteId === row._line?.id ? (
        <div className="flex items-center gap-1">
          <button type="button" onClick={onDelete} className="px-2 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600 transition-colors" title="Click to confirm delete">
            Yes
          </button>
          <button type="button" onClick={onCancelDelete} className="px-2 py-1 text-xs bg-slate-300 dark:bg-slate-600 text-slate-700 dark:text-slate-200 rounded hover:bg-slate-400 dark:hover:bg-slate-500 transition-colors" title="Cancel delete">
            No
          </button>
        </div>
      ) : (
        <button type="button" onClick={onDelete} className="p-1 text-slate-400 hover:text-red-500 transition-colors" title="Delete line">
          <FaTrash size={14} />
        </button>
      )
    )}
  </div>
);

export default withDevIdentifier(LinesCard, 'LinesCard', 'amber');
