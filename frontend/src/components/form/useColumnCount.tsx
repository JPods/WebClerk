/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useState, useEffect } from "react";

/**
 * useColumnCount - Hook for managing column count preference with localStorage persistence
 * 
 * @param storageKey - Unique key for localStorage (e.g., "serviceDetail_columnCount")
 * @param defaultValue - Default column count (2 or 3)
 * @returns [columnCount, setColumnCount]
 */
export function useColumnCount(storageKey: string, defaultValue: number = 3): [number, (value: number) => void] {
  const [columnCount, setColumnCountState] = useState<number>(() => {
    if (typeof window === 'undefined') return defaultValue;
    const saved = localStorage.getItem(storageKey);
    return saved ? parseInt(saved, 10) : defaultValue;
  });

  useEffect(() => {
    localStorage.setItem(storageKey, String(columnCount));
  }, [storageKey, columnCount]);

  return [columnCount, setColumnCountState];
}

/**
 * ColumnSelector - Toggle buttons for 2 or 3 column layouts
 */
interface ColumnSelectorProps {
  columnCount: number;
  setColumnCount: (value: number) => void;
  className?: string;
}

export function ColumnSelector({ columnCount, setColumnCount, className = "" }: ColumnSelectorProps) {
  return (
    <div className={`flex items-center gap-1 ${className}`}>
      <span className="text-xs text-slate-500 dark:text-slate-400 mr-1">Cols:</span>
      {[2, 3].map((cols) => (
        <button
          key={cols}
          type="button"
          onClick={() => setColumnCount(cols)}
          className={`px-2 py-0.5 text-xs rounded transition-colors ${
            columnCount === cols
              ? "bg-brand-500 text-white"
              : "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600"
          }`}
        >
          {cols}
        </button>
      ))}
    </div>
  );
}

/**
 * getGridClassName - Returns the grid class string based on column count
 */
export function getGridClassName(columnCount: number): string {
  return `grid grid-cols-1 ${columnCount === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-2'} gap-x-6 gap-y-1`;
}

export default useColumnCount;
