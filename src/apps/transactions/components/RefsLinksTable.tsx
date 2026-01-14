/**
 * RefsLinksTable - Generic table for displaying refs.links.* arrays
 * Supports contact, customer, vendor, item, and other link types
 */
import React from 'react';
import { FaTrash, FaPlus, FaEdit } from 'react-icons/fa';
import type { TransactionRefsLinks } from '../types/transactionTypes';

type LinkType = keyof TransactionRefsLinks;

interface ColumnDef<T = Record<string, unknown>> {
  key: string;
  label: string;
  render?: (item: T) => React.ReactNode;
  width?: string;
}

interface RefsLinksTableProps<T = Record<string, unknown>> {
  links: TransactionRefsLinks | undefined;
  linkType: LinkType;
  columns: ColumnDef<T>[];
  isEditing?: boolean;
  onAdd?: () => void;
  onEdit?: (item: T) => void;
  onRemove?: (id: number) => void;
  emptyMessage?: string;
  title?: string;
}

function RefsLinksTable<T extends { id?: number | string } = Record<string, unknown>>({
  links,
  linkType,
  columns,
  isEditing = false,
  onAdd,
  onEdit,
  onRemove,
  emptyMessage = 'No items',
  title,
}: RefsLinksTableProps<T>) {
  const items = (links?.[linkType] as T[] | undefined) || [];

  const getItemValue = (item: T, key: string): unknown => {
    if (key.includes('.')) {
      const parts = key.split('.');
      let value: unknown = item;
      for (const part of parts) {
        if (value && typeof value === 'object') {
          value = (value as Record<string, unknown>)[part];
        } else {
          return undefined;
        }
      }
      return value;
    }
    return (item as Record<string, unknown>)[key];
  };

  const extractId = (item: T): number | null => {
    const id = item.id;
    if (typeof id === 'number') return id;
    if (typeof id === 'string') {
      const parsed = parseInt(id, 10);
      return isNaN(parsed) ? null : parsed;
    }
    return null;
  };

  return (
    <div className="space-y-2">
      {title && (
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
            {title}
          </h4>
          {isEditing && onAdd && (
            <button
              onClick={onAdd}
              className="inline-flex items-center gap-1 text-xs text-blue-500 hover:text-blue-600"
            >
              <FaPlus size={10} /> Add
            </button>
          )}
        </div>
      )}
      
      {items.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400 italic py-2">
          {emptyMessage}
        </p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800">
              <tr>
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className="px-3 py-2 font-medium text-slate-700 dark:text-slate-300"
                    style={col.width ? { width: col.width } : undefined}
                  >
                    {col.label}
                  </th>
                ))}
                {isEditing && (onEdit || onRemove) && (
                  <th className="px-3 py-2 w-20 text-right">Actions</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {items.map((item, idx) => {
                const itemId = extractId(item);
                return (
                  <tr 
                    key={itemId ?? idx}
                    className="hover:bg-slate-50 dark:hover:bg-slate-800/50"
                  >
                    {columns.map((col) => (
                      <td key={col.key} className="px-3 py-2 text-slate-700 dark:text-slate-300">
                        {col.render 
                          ? col.render(item)
                          : String(getItemValue(item, col.key) ?? '--')
                        }
                      </td>
                    ))}
                    {isEditing && (onEdit || onRemove) && (
                      <td className="px-3 py-2 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {onEdit && (
                            <button
                              onClick={() => onEdit(item)}
                              className="text-blue-500 hover:text-blue-600"
                              title="Edit"
                            >
                              <FaEdit size={12} />
                            </button>
                          )}
                          {onRemove && itemId !== null && (
                            <button
                              onClick={() => onRemove(itemId)}
                              className="text-red-500 hover:text-red-600"
                              title="Remove"
                            >
                              <FaTrash size={12} />
                            </button>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default RefsLinksTable;
