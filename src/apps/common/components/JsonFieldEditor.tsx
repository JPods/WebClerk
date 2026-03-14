/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * JsonFieldEditor - Generic JSON editor for admin power users
 * Supports view/edit modes with syntax highlighting and validation
 */
import React, { useState, useEffect, useCallback } from 'react';
import { 
  FaEdit, 
  FaCheck, 
  FaTimes, 
  FaCopy, 
  FaExpand, 
  FaCompress,
  FaExclamationTriangle,
  FaCode
} from 'react-icons/fa';

interface JsonFieldEditorProps {
  label: string;
  value: unknown;
  onChange?: (value: unknown) => void;
  readonly?: boolean;
  collapsible?: boolean;
  defaultExpanded?: boolean;
  maxHeight?: string;
  showLineNumbers?: boolean;
}

const JsonFieldEditor: React.FC<JsonFieldEditorProps> = ({
  label,
  value,
  onChange,
  readonly = false,
  collapsible = true,
  defaultExpanded = false,
  maxHeight = '400px',
  showLineNumbers = true,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [editText, setEditText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Format JSON for display
  const formatJson = useCallback((val: unknown): string => {
    try {
      return JSON.stringify(val, null, 2);
    } catch {
      return String(val);
    }
  }, []);

  // Initialize edit text when entering edit mode
  useEffect(() => {
    if (isEditing) {
      setEditText(formatJson(value));
      setError(null);
    }
  }, [isEditing, value, formatJson]);

  // Validate and parse JSON
  const validateJson = (text: string): { valid: boolean; value?: unknown; error?: string } => {
    try {
      const parsed = JSON.parse(text);
      return { valid: true, value: parsed };
    } catch (e) {
      return { 
        valid: false, 
        error: e instanceof Error ? e.message : 'Invalid JSON' 
      };
    }
  };

  // Handle save
  const handleSave = () => {
    const result = validateJson(editText);
    if (result.valid && onChange) {
      onChange(result.value);
      setIsEditing(false);
      setError(null);
    } else {
      setError(result.error ?? 'Invalid JSON');
    }
  };

  // Handle cancel
  const handleCancel = () => {
    setIsEditing(false);
    setEditText('');
    setError(null);
  };

  // Handle copy
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(formatJson(value));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      console.error('Failed to copy');
    }
  };

  // Count lines and keys
  const formattedValue = formatJson(value);
  const lineCount = formattedValue.split('\n').length;
  const keyCount = typeof value === 'object' && value !== null 
    ? Object.keys(value).length 
    : 0;

  // Render line numbers
  const renderLineNumbers = (text: string): string => {
    return text
      .split('\n')
      .map((_, i) => String(i + 1).padStart(3, ' '))
      .join('\n');
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-50 dark:bg-slate-900/50 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-2">
          <FaCode className="text-slate-400" size={12} />
          <span className="font-medium text-sm text-slate-700 dark:text-slate-300">{label}</span>
          <span className="text-xs text-slate-400">
            {keyCount > 0 ? `${keyCount} keys` : ''} • {lineCount} lines
          </span>
        </div>
        
        <div className="flex items-center gap-1">
          {/* Copy Button */}
          <button
            onClick={handleCopy}
            className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
            title="Copy JSON"
          >
            <FaCopy size={12} />
          </button>
          {copied && (
            <span className="text-xs text-green-500 mr-2">Copied!</span>
          )}
          
          {/* Expand/Collapse */}
          {collapsible && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
              title={isExpanded ? 'Collapse' : 'Expand'}
            >
              {isExpanded ? <FaCompress size={12} /> : <FaExpand size={12} />}
            </button>
          )}
          
          {/* Edit/Save/Cancel */}
          {!readonly && (
            isEditing ? (
              <>
                <button
                  onClick={handleSave}
                  className="p-1.5 text-green-500 hover:text-green-600 transition-colors"
                  title="Save"
                >
                  <FaCheck size={12} />
                </button>
                <button
                  onClick={handleCancel}
                  className="p-1.5 text-red-500 hover:text-red-600 transition-colors"
                  title="Cancel"
                >
                  <FaTimes size={12} />
                </button>
              </>
            ) : (
              <button
                onClick={() => setIsEditing(true)}
                className="p-1.5 text-slate-400 hover:text-blue-500 transition-colors"
                title="Edit"
              >
                <FaEdit size={12} />
              </button>
            )
          )}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="px-4 py-2 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800 flex items-center gap-2 text-sm text-red-600 dark:text-red-400">
          <FaExclamationTriangle size={12} />
          {error}
        </div>
      )}

      {/* Content */}
      <div 
        className={`overflow-auto transition-all ${collapsible && !isExpanded ? 'max-h-32' : ''}`}
        style={!collapsible || isExpanded ? { maxHeight } : undefined}
      >
        {isEditing ? (
          // Edit Mode
          <div className="flex">
            {showLineNumbers && (
              <pre className="p-3 text-xs font-mono text-slate-400 bg-slate-100 dark:bg-slate-900 border-r border-slate-200 dark:border-slate-700 select-none">
                {renderLineNumbers(editText)}
              </pre>
            )}
            <textarea
              value={editText}
              onChange={(e) => {
                setEditText(e.target.value);
                setError(null);
              }}
              className={`
                flex-1 p-3 text-sm font-mono 
                bg-white dark:bg-slate-800 
                text-slate-800 dark:text-slate-200
                border-0 outline-none resize-none
                focus:ring-2 focus:ring-blue-500 focus:ring-inset
                ${error ? 'bg-red-50 dark:bg-red-900/10' : ''}
              `}
              style={{ minHeight: maxHeight }}
              spellCheck={false}
            />
          </div>
        ) : (
          // View Mode
          <div className="flex">
            {showLineNumbers && (
              <pre className="p-3 text-xs font-mono text-slate-400 bg-slate-100 dark:bg-slate-900 border-r border-slate-200 dark:border-slate-700 select-none">
                {renderLineNumbers(formattedValue)}
              </pre>
            )}
            <pre className="flex-1 p-3 text-sm font-mono text-slate-800 dark:text-slate-200 whitespace-pre-wrap break-words">
              <JsonHighlight value={formattedValue} />
            </pre>
          </div>
        )}
      </div>

      {/* Collapse Indicator */}
      {collapsible && !isExpanded && lineCount > 6 && (
        <div className="text-center py-1 bg-gradient-to-t from-slate-100 to-transparent dark:from-slate-900 text-xs text-slate-400">
          Click expand to see {lineCount - 6} more lines
        </div>
      )}
    </div>
  );
};

// Simple JSON syntax highlighting
const JsonHighlight: React.FC<{ value: string }> = ({ value }) => {
  const highlighted = value
    // Keys
    .replace(/"([^"]+)":/g, '<span class="text-purple-600 dark:text-purple-400">"$1"</span>:')
    // String values
    .replace(/: "([^"]*)"/g, ': <span class="text-green-600 dark:text-green-400">"$1"</span>')
    // Numbers
    .replace(/: (-?\d+\.?\d*)/g, ': <span class="text-blue-600 dark:text-blue-400">$1</span>')
    // Booleans
    .replace(/: (true|false)/g, ': <span class="text-amber-600 dark:text-amber-400">$1</span>')
    // Null
    .replace(/: (null)/g, ': <span class="text-slate-400">$1</span>');

  return <span dangerouslySetInnerHTML={{ __html: highlighted }} />;
};

export default JsonFieldEditor;
