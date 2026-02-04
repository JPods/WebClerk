/**
 * RawDataPanel - Display raw JSON data for admin/developer debugging
 * 
 * Role-based access:
 * - View: Admin only (default)
 * - Edit: Admin only (default)
 * 
 * @example
 * <RawDataPanel
 *   entityType="contact"
 *   entityId={123}
 *   data={contact}
 * />
 */
import React, { useState, useMemo } from 'react';
import { FaCode, FaChevronDown, FaChevronUp, FaCopy, FaCheck, FaDownload } from 'react-icons/fa';
import { usePermissions } from './usePermissions';
import type { BasePanelProps } from './types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RawDataPanelProps extends BasePanelProps<unknown> {
  /** Sections to highlight (e.g., ['metadata', 'refs', 'prefs']) */
  highlightSections?: string[];
  /** Max height for JSON display */
  maxHeight?: string;
}

// ---------------------------------------------------------------------------
// JSON Syntax Highlighter
// ---------------------------------------------------------------------------

const syntaxHighlight = (json: string): string => {
  return json.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
    (match) => {
      let cls = 'text-purple-600 dark:text-purple-400'; // number
      if (/^"/.test(match)) {
        if (/:$/.test(match)) {
          cls = 'text-blue-600 dark:text-blue-400'; // key
        } else {
          cls = 'text-green-600 dark:text-green-400'; // string
        }
      } else if (/true|false/.test(match)) {
        cls = 'text-amber-600 dark:text-amber-400'; // boolean
      } else if (/null/.test(match)) {
        cls = 'text-red-600 dark:text-red-400'; // null
      }
      return `<span class="${cls}">${match}</span>`;
    }
  );
};

// ---------------------------------------------------------------------------
// Section Navigator
// ---------------------------------------------------------------------------

interface SectionNavProps {
  sections: string[];
  onNavigate: (section: string) => void;
}

const SectionNav: React.FC<SectionNavProps> = ({ sections, onNavigate }) => {
  if (sections.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1 mb-3">
      {sections.map((section) => (
        <button
          key={section}
          onClick={() => onNavigate(section)}
          className="px-2 py-0.5 text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded hover:bg-slate-200 dark:hover:bg-slate-600"
        >
          .{section}
        </button>
      ))}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main RawDataPanel Component
// ---------------------------------------------------------------------------

const RawDataPanel: React.FC<RawDataPanelProps> = ({
  entityType,
  entityId,
  data,
  readOnly: _readOnly = true, // Raw data is typically read-only
  viewRoles,
  editRoles,
  className = '',
  compact = false,
  title = 'Raw Data',
  defaultCollapsed = true,
  highlightSections = ['metadata', 'refs', 'prefs', 'comments', 'financials'],
  maxHeight = '400px',
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [copied, setCopied] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  // Check permissions (admin only by default)
  const { canView } = usePermissions({
    panelType: 'rawData',
    viewRoles,
    editRoles,
    forceReadOnly: true,
  });

  // Don't render if user can't view
  if (!canView) return null;

  // Format JSON
  const jsonString = useMemo(() => {
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return 'Unable to serialize data';
    }
  }, [data]);

  // Find available sections
  const availableSections = useMemo(() => {
    if (typeof data !== 'object' || data === null) return [];
    return highlightSections.filter((section) => section in (data as Record<string, unknown>));
  }, [data, highlightSections]);

  // Filter JSON if search term provided
  const displayJson = useMemo(() => {
    if (!searchTerm) return jsonString;
    
    const lines = jsonString.split('\n');
    const matchingLines: number[] = [];
    
    lines.forEach((line, idx) => {
      if (line.toLowerCase().includes(searchTerm.toLowerCase())) {
        // Include surrounding context
        for (let i = Math.max(0, idx - 2); i <= Math.min(lines.length - 1, idx + 2); i++) {
          if (!matchingLines.includes(i)) matchingLines.push(i);
        }
      }
    });
    
    if (matchingLines.length === 0) return jsonString;
    
    matchingLines.sort((a, b) => a - b);
    return matchingLines.map((i) => lines[i]).join('\n');
  }, [jsonString, searchTerm]);

  // Highlighted JSON HTML
  const highlightedJson = useMemo(() => {
    return syntaxHighlight(displayJson);
  }, [displayJson]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(jsonString);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${entityType}_${entityId}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleNavigateToSection = (section: string) => {
    const el = document.getElementById(`raw-section-${section}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    setSearchTerm(`"${section}":`);
  };

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-lg border border-slate-300 dark:border-slate-600 ${className}`}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-slate-100 dark:bg-slate-700 border-b border-slate-300 dark:border-slate-600 cursor-pointer rounded-t-lg"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaCode className="text-slate-500" size={14} />
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">{title}</h3>
          <span className="px-1.5 py-0.5 text-xs bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-300 rounded">
            Admin/Dev
          </span>
          <span className="text-xs text-slate-500">
            {jsonString.length.toLocaleString()} chars
          </span>
        </div>
        <div className="flex items-center gap-2">
          {!isCollapsed && (
            <>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleCopy();
                }}
                className="p-1 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-600 rounded"
                title="Copy to clipboard"
              >
                {copied ? <FaCheck size={12} className="text-green-500" /> : <FaCopy size={12} />}
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDownload();
                }}
                className="p-1 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-600 rounded"
                title="Download JSON"
              >
                <FaDownload size={12} />
              </button>
            </>
          )}
          {isCollapsed ? <FaChevronDown size={12} /> : <FaChevronUp size={12} />}
        </div>
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className={`${compact ? 'p-2' : 'p-4'}`}>
          {/* Section Navigator */}
          <SectionNav sections={availableSections} onNavigate={handleNavigateToSection} />

          {/* Search */}
          <div className="mb-3">
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search JSON..."
              className="w-full px-2 py-1 text-xs border rounded bg-white dark:bg-slate-700 dark:border-slate-600"
            />
          </div>

          {/* JSON Display */}
          <div
            className="overflow-auto rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
            style={{ maxHeight }}
          >
            <pre
              className="p-3 text-xs font-mono leading-relaxed"
              dangerouslySetInnerHTML={{ __html: highlightedJson }}
            />
          </div>

          {/* Stats */}
          <div className="mt-2 flex items-center gap-4 text-xs text-slate-400">
            <span>Entity: {entityType}</span>
            <span>ID: {entityId}</span>
            <span>Sections: {availableSections.length}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default RawDataPanel;
