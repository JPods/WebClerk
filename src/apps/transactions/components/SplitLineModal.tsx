/**
 * SplitLineModal - Split a line item into multiple shipments/allocations
 * Allows dividing quantity across multiple lines with different ship dates or warehouses
 */
import React, { useState, useEffect, useCallback } from 'react';
import { 
  FaTimes, 
  FaSave,
  FaPlus,
  FaTrash,
  FaExchangeAlt,
  FaWarehouse,
  FaTruck,
  FaCalendarAlt
} from 'react-icons/fa';
import type { TransactionLine } from '../types/transactionTypes';

interface SplitAllocation {
  id: number;
  quantity: number;
  warehouseId?: number;
  warehouseName?: string;
  shipDate?: string;
  notes?: string;
}

interface SplitLineModalProps {
  line: TransactionLine | null;
  isOpen: boolean;
  onClose: () => void;
  onSave?: (originalLine: TransactionLine, splits: SplitAllocation[]) => void;
  warehouses?: { id: number; name: string }[];
}

const SplitLineModal: React.FC<SplitLineModalProps> = ({
  line,
  isOpen,
  onClose,
  onSave,
  warehouses = [
    { id: 1, name: 'Main Warehouse' },
    { id: 2, name: 'East Distribution' },
    { id: 3, name: 'West Distribution' },
  ],
}) => {
  const [splits, setSplits] = useState<SplitAllocation[]>([]);
  const [nextId, setNextId] = useState(1);

  // Get line quantity safely
  const getLineQty = useCallback((): number => {
    if (!line) return 0;
    const lineRecord = line as unknown as Record<string, unknown>;
    return Number(lineRecord.qty ?? line.quantity?.ordered ?? 0);
  }, [line]);

  // Initialize splits when line changes
  useEffect(() => {
    if (line && isOpen) {
      const totalQty = getLineQty();
      // Start with two splits, each half
      const half = Math.floor(totalQty / 2);
      setSplits([
        { id: 1, quantity: half, warehouseId: warehouses[0]?.id, warehouseName: warehouses[0]?.name },
        { id: 2, quantity: totalQty - half, warehouseId: warehouses[0]?.id, warehouseName: warehouses[0]?.name },
      ]);
      setNextId(3);
    }
  }, [line, isOpen, getLineQty, warehouses]);

  if (!isOpen || !line) return null;

  const totalQty = getLineQty();
  const allocatedQty = splits.reduce((sum, s) => sum + s.quantity, 0);
  const remainingQty = totalQty - allocatedQty;

  // Get line item info
  const lineRecord = line as unknown as Record<string, unknown>;
  const itemCode = String(lineRecord.ida_item ?? line.item?.ida_item ?? '--');
  const description = String(lineRecord.description ?? line.item?.description ?? '--');

  // Add a new split
  const addSplit = () => {
    setSplits(prev => [
      ...prev,
      { 
        id: nextId, 
        quantity: Math.max(0, remainingQty),
        warehouseId: warehouses[0]?.id,
        warehouseName: warehouses[0]?.name,
      }
    ]);
    setNextId(prev => prev + 1);
  };

  // Remove a split
  const removeSplit = (id: number) => {
    if (splits.length <= 2) return; // Keep at least 2 splits
    setSplits(prev => prev.filter(s => s.id !== id));
  };

  // Update a split
  const updateSplit = (id: number, field: keyof SplitAllocation, value: unknown) => {
    setSplits(prev => prev.map(s => {
      if (s.id !== id) return s;
      
      if (field === 'warehouseId') {
        const warehouse = warehouses.find(w => w.id === value);
        return { ...s, warehouseId: value as number, warehouseName: warehouse?.name };
      }
      
      return { ...s, [field]: value };
    }));
  };

  // Distribute evenly
  const distributeEvenly = () => {
    const count = splits.length;
    if (count === 0) return;
    
    const baseQty = Math.floor(totalQty / count);
    const remainder = totalQty % count;
    
    setSplits(prev => prev.map((s, idx) => ({
      ...s,
      quantity: baseQty + (idx < remainder ? 1 : 0)
    })));
  };

  // Handle save
  const handleSave = () => {
    if (onSave && allocatedQty === totalQty) {
      onSave(line, splits);
    }
    onClose();
  };

  // Check if valid
  const isValid = allocatedQty === totalQty && splits.every(s => s.quantity > 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative w-full max-w-2xl max-h-[90vh] bg-white dark:bg-slate-800 rounded-lg shadow-xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <FaExchangeAlt className="text-purple-600 dark:text-purple-400" size={16} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                Split Line Item
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {itemCode} - {description}
              </p>
            </div>
          </div>
          
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
          >
            <FaTimes size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 max-h-[60vh] overflow-auto">
          {/* Summary bar */}
          <div className="flex items-center justify-between mb-6 p-4 bg-slate-50 dark:bg-slate-900/50 rounded-lg">
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">Total Quantity</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{totalQty}</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-slate-500 dark:text-slate-400">Allocated</p>
              <p className={`text-2xl font-bold ${allocatedQty === totalQty ? 'text-green-600' : 'text-amber-600'}`}>
                {allocatedQty}
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm text-slate-500 dark:text-slate-400">Remaining</p>
              <p className={`text-2xl font-bold ${remainingQty === 0 ? 'text-green-600' : 'text-red-600'}`}>
                {remainingQty}
              </p>
            </div>
          </div>

          {/* Quick actions */}
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Split Allocations ({splits.length})
            </h3>
            <div className="flex items-center gap-2">
              <button
                onClick={distributeEvenly}
                className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 rounded hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
              >
                Distribute Evenly
              </button>
              <button
                onClick={addSplit}
                className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 rounded hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors"
              >
                <FaPlus size={10} />
                Add Split
              </button>
            </div>
          </div>

          {/* Splits list */}
          <div className="space-y-4">
            {splits.map((split, idx) => (
              <div 
                key={split.id}
                className="p-4 border border-slate-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800"
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                    Split #{idx + 1}
                  </span>
                  {splits.length > 2 && (
                    <button
                      onClick={() => removeSplit(split.id)}
                      className="p-1 text-slate-400 hover:text-red-500 transition-colors"
                      title="Remove split"
                    >
                      <FaTrash size={12} />
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {/* Quantity */}
                  <div>
                    <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">
                      Quantity
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={totalQty}
                      value={split.quantity}
                      onChange={(e) => updateSplit(split.id, 'quantity', parseInt(e.target.value) || 0)}
                      className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  {/* Warehouse */}
                  <div>
                    <label className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400 mb-1">
                      <FaWarehouse size={10} />
                      Warehouse
                    </label>
                    <select
                      value={split.warehouseId || ''}
                      onChange={(e) => updateSplit(split.id, 'warehouseId', parseInt(e.target.value))}
                      className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {warehouses.map(wh => (
                        <option key={wh.id} value={wh.id}>{wh.name}</option>
                      ))}
                    </select>
                  </div>

                  {/* Ship Date */}
                  <div>
                    <label className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400 mb-1">
                      <FaCalendarAlt size={10} />
                      Ship Date
                    </label>
                    <input
                      type="date"
                      value={split.shipDate || ''}
                      onChange={(e) => updateSplit(split.id, 'shipDate', e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  {/* Notes */}
                  <div>
                    <label className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400 mb-1">
                      <FaTruck size={10} />
                      Notes
                    </label>
                    <input
                      type="text"
                      value={split.notes || ''}
                      onChange={(e) => updateSplit(split.id, 'notes', e.target.value)}
                      placeholder="e.g., Ship with order #123"
                      className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Validation message */}
          {!isValid && (
            <div className="mt-4 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
              <p className="text-sm text-amber-700 dark:text-amber-400">
                {remainingQty > 0 && `${remainingQty} units still need to be allocated.`}
                {remainingQty < 0 && `Allocated quantity exceeds total by ${Math.abs(remainingQty)} units.`}
                {splits.some(s => s.quantity === 0) && ' All splits must have quantity greater than 0.'}
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-600 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!isValid}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <FaSave size={14} />
            Apply Split
          </button>
        </div>
      </div>
    </div>
  );
};

export default SplitLineModal;
