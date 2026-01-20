/**
 * JsonEnvelopesPanel - Admin/Developer view for transaction JSON envelopes
 * 
 * Shows totals, cost, sell, finance, flow, source, action fields
 * for debugging and process control.
 * 
 * Only visible when isAdmin or isDeveloper is true.
 */
import React, { useState, useCallback, useMemo } from 'react';
import { FaChevronDown, FaChevronRight, FaDatabase } from 'react-icons/fa';

// JSON field paths for transaction headers (from TransactionBaseModel.JSON_DEFAULT_FACTORIES)
const TRANSACTION_JSON_FIELDS = [
  'totals',
  'cost', 
  'sell',
  'finance',
  'flow',
  'source',
  'action',
] as const;

// These fields are read-only (calculated by backend services)
const READONLY_FIELDS = new Set([
  'totals',
  'cost',
  'sell',
  'finance',
  'flow',
  'source',
  'action',
]);

type JsonFieldName = typeof TRANSACTION_JSON_FIELDS[number];

interface JsonEnvelopesPanelProps {
  /** Transaction data object */
  data: Record<string, unknown>;
  /** Whether component is visible (admin/developer only) */
  isVisible?: boolean;
  /** Whether fields are editable */
  isEditing?: boolean;
  /** Callback when a field changes */
  onChange?: (field: string, value: unknown) => void;
  /** Initially collapsed */
  defaultCollapsed?: boolean;
  /** Additional JSON fields to display */
  additionalFields?: string[];
  /** Custom title */
  title?: string;
}

const JsonEnvelopesPanel: React.FC<JsonEnvelopesPanelProps> = ({
  data,
  isVisible = true,
  isEditing = false,
  onChange,
  defaultCollapsed = true,
  additionalFields = [],
  title = 'JSON Envelopes (Admin)',
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [jsonDrafts, setJsonDrafts] = useState<Record<string, string>>({});
  const [jsonErrors, setJsonErrors] = useState<Record<string, string>>({});

  // Combine default fields with additional fields
  const allFields = useMemo(() => {
    const fields = [...TRANSACTION_JSON_FIELDS];
    additionalFields.forEach(f => {
      if (!fields.includes(f as JsonFieldName)) {
        fields.push(f as JsonFieldName);
      }
    });
    return fields;
  }, [additionalFields]);

  // Get formatted JSON for a field
  const getFieldJson = useCallback((fieldName: string): string => {
    if (jsonDrafts[fieldName] !== undefined) {
      return jsonDrafts[fieldName];
    }
    const value = data[fieldName];
    if (value === null || value === undefined) {
      return '{}';
    }
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return '{}';
    }
  }, [data, jsonDrafts]);

  // Handle JSON text change
  const handleJsonChange = useCallback((fieldName: string, text: string) => {
    setJsonDrafts(prev => ({ ...prev, [fieldName]: text }));
    
    // Validate JSON
    try {
      JSON.parse(text);
      setJsonErrors(prev => {
        const next = { ...prev };
        delete next[fieldName];
        return next;
      });
    } catch (e) {
      setJsonErrors(prev => ({
        ...prev,
        [fieldName]: 'Invalid JSON syntax',
      }));
    }
  }, []);

  // Handle blur - commit changes
  const handleJsonBlur = useCallback((fieldName: string) => {
    const text = jsonDrafts[fieldName];
    if (text === undefined || jsonErrors[fieldName]) return;
    
    try {
      const parsed = JSON.parse(text);
      onChange?.(fieldName, parsed);
      // Clear draft after successful commit
      setJsonDrafts(prev => {
        const next = { ...prev };
        delete next[fieldName];
        return next;
      });
    } catch {
      // Error already set in handleJsonChange
    }
  }, [jsonDrafts, jsonErrors, onChange]);

  if (!isVisible) return null;

  return (
    <div className="mt-6 border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
      {/* Header - collapsible */}
      <button
        type="button"
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 dark:bg-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
      >
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-600 dark:text-slate-300">
          <FaDatabase className="text-slate-400" size={14} />
          {title}
        </div>
        <div className="flex items-center gap-2 text-slate-400">
          <span className="text-xs">{allFields.length} fields</span>
          {isCollapsed ? <FaChevronRight size={12} /> : <FaChevronDown size={12} />}
        </div>
      </button>

      {/* Content */}
      {!isCollapsed && (
        <div className="p-4 bg-white dark:bg-slate-900">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {allFields.map((fieldName) => {
              const isReadOnly = READONLY_FIELDS.has(fieldName) || !isEditing;
              const errorMessage = jsonErrors[fieldName];
              const jsonValue = getFieldJson(fieldName);
              
              return (
                <div key={fieldName} className="space-y-1">
                  <label 
                    htmlFor={`json-${fieldName}`}
                    className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"
                  >
                    {fieldName}
                    {READONLY_FIELDS.has(fieldName) && (
                      <span className="text-[10px] font-normal text-slate-400">(read-only)</span>
                    )}
                  </label>
                  <textarea
                    id={`json-${fieldName}`}
                    className={`w-full min-h-[120px] rounded-lg border px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                      errorMessage 
                        ? 'border-red-500 bg-red-50 dark:bg-red-900/20' 
                        : 'border-slate-200 dark:border-slate-700'
                    } ${
                      isReadOnly
                        ? 'bg-slate-50 dark:bg-slate-800/50 text-slate-600 dark:text-slate-400'
                        : 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white'
                    }`}
                    value={jsonValue}
                    onChange={(e) => handleJsonChange(fieldName, e.target.value)}
                    onBlur={() => handleJsonBlur(fieldName)}
                    readOnly={isReadOnly}
                    spellCheck={false}
                  />
                  {errorMessage && (
                    <p className="text-xs text-red-500">{errorMessage}</p>
                  )}
                </div>
              );
            })}
          </div>
          
          {/* Legend */}
          <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
            <p className="text-xs text-slate-400">
              These JSON envelopes are auto-populated on save via <code className="text-slate-500">JSON_DEFAULT_FACTORIES</code>.
              Fields marked read-only are calculated by backend services.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default JsonEnvelopesPanel;
