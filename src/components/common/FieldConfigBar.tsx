/**
 * FieldConfigBar — collapsible field selection + ordering bar for list pages.
 *
 * Drop this above any AdvancedDataTable to let users pick which columns
 * to show and drag-reorder them. Same UX as the DataBrowser.
 *
 * Usage:
 *   <FieldConfigBar
 *     show={fieldConfig.showPanel}
 *     allKeys={fieldConfig.allKeys}
 *     effectiveKeys={fieldConfig.effectiveKeys}
 *     onToggle={fieldConfig.toggleField}
 *     onAll={fieldConfig.setAll}
 *     onClear={fieldConfig.clearAll}
 *     onMove={fieldConfig.moveField}
 *     onClose={fieldConfig.togglePanel}
 *   />
 */

import React from 'react';

interface FieldConfigBarProps {
  show: boolean;
  allKeys: string[];
  effectiveKeys: string[];
  onToggle: (key: string) => void;
  onAll: () => void;
  onClear: () => void;
  onMove: (key: string, direction: 'up' | 'down') => void;
  onClose: () => void;
}

const FieldConfigBar: React.FC<FieldConfigBarProps> = ({
  show, allKeys, effectiveKeys, onToggle, onAll, onClear, onMove, onClose,
}) => {
  if (!show) return null;

  return (
    <div className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-4 py-2">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wider">
          Columns
        </span>
        <button onClick={onAll}
          className="px-2 py-0.5 text-[10px] rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300">
          All
        </button>
        <button onClick={onClear}
          className="px-2 py-0.5 text-[10px] rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300">
          Min
        </button>
        <span className="text-[10px] text-gray-400">{effectiveKeys.length}/{allKeys.length}</span>
        <span className="flex-1" />
        <button onClick={onClose}
          className="px-2 py-0.5 text-[10px] rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300 font-medium">
          Done
        </button>
      </div>
      <div className="flex flex-wrap gap-1 max-h-20 overflow-auto">
        {allKeys.map((key, idx) => {
          const active = effectiveKeys.includes(key);
          return (
            <span key={key} className="inline-flex items-center gap-0.5">
              {active && (
                <>
                  <button onClick={() => onMove(key, 'up')} disabled={effectiveKeys.indexOf(key) === 0}
                    className="text-[9px] text-gray-400 hover:text-gray-600 disabled:opacity-20 px-0.5">
                    ◀
                  </button>
                  <button onClick={() => onMove(key, 'down')} disabled={effectiveKeys.indexOf(key) === effectiveKeys.length - 1}
                    className="text-[9px] text-gray-400 hover:text-gray-600 disabled:opacity-20 px-0.5">
                    ▶
                  </button>
                </>
              )}
              <button
                onClick={() => onToggle(key)}
                className={`px-2 py-0.5 text-[10px] font-medium rounded border transition ${
                  active
                    ? 'bg-blue-600 text-white border-blue-600 dark:bg-blue-700 dark:border-blue-700'
                    : 'bg-white dark:bg-gray-700 text-gray-500 dark:text-gray-400 border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-600'
                }`}
              >
                {key}
              </button>
            </span>
          );
        })}
      </div>
    </div>
  );
};

export default FieldConfigBar;
