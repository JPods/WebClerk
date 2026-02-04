/**
 * LinkagesPanel - Cross-table record linkage viewer
 * 
 * Displays the records from multiple tables that are linked together through
 * a Linkage hub. Tracks document/record relationships as items flow through
 * business processes (e.g., Proposal → Order → Invoice → Payment).
 * 
 * The Linkage record acts as a central hub connecting IDs from multiple tables,
 * allowing tracking of the full "paper trail" of an item through the system.
 * 
 * @see /webClerk3/apps/docs/models/linkage.py - Django Linkage model
 * @see README.md for panel documentation
 */

import React, { useMemo, useState } from 'react';
import { 
  FiLink2, 
  FiExternalLink, 
  FiChevronRight,
  FiChevronDown,
  FiPackage,
  FiFileText,
  FiShoppingCart,
  FiDollarSign,
  FiClipboard,
  FiTruck,
  FiBox,
  FiUsers,
  FiFolder,
} from 'react-icons/fi';
import { usePermissions } from './usePermissions';
import type { BasePanelProps, UserRole } from './types';
import { ADMIN_ROLES, ALL_ROLES } from './types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Linked record entry (minimal denormalized data) */
export interface LinkedRecord {
  id: number;
  ida?: string;
  name?: string;
  display?: string;
  status?: string;
  dt_created?: number;
  dt_modified?: number;
  [key: string]: unknown;
}

/** Linkage data structure matching Django Linkage model */
export interface LinkageData {
  id: number;
  ida?: string;
  purpose?: string;
  name?: string;
  note?: string;
  refs?: {
    links?: Record<string, LinkedRecord[] | number[]>;
    [key: string]: unknown;
  };
  metadata?: {
    history?: {
      created?: { dt?: number; contact_id?: number };
      modified?: { dt?: number; contact_id?: number };
    };
    [key: string]: unknown;
  };
  dt_created?: number;
  dt_modified?: number;
}

/** Props for LinkagesPanel */
export interface LinkagesPanelProps extends Omit<BasePanelProps<LinkageData | null>, 'data'> {
  /** Linkage data (null if no linkage exists) */
  data: LinkageData | null;
  
  /** Callback when user clicks on a linked record */
  onRecordClick?: (tableName: string, recordId: number, record?: LinkedRecord) => void;
  
  /** Callback to view linkage details */
  onViewLinkage?: (linkageId: number) => void;
  
  /** Tables to highlight in the flow (ordered) */
  flowTables?: string[];
  
  /** Custom display names for tables */
  tableDisplayNames?: Record<string, string>;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Default permissions: viewable by all, editable by admin */
const DEFAULT_VIEW_ROLES: UserRole[] = ALL_ROLES;
const DEFAULT_EDIT_ROLES: UserRole[] = ADMIN_ROLES;

/** Icons for common table types */
const TABLE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  proposal: FiClipboard,
  proposal_line: FiClipboard,
  order: FiShoppingCart,
  order_line: FiShoppingCart,
  sales_order: FiShoppingCart,
  sales_order_line: FiShoppingCart,
  invoice: FiDollarSign,
  invoice_line: FiDollarSign,
  purchase: FiPackage,
  purchase_line: FiPackage,
  purchase_order: FiPackage,
  purchase_order_line: FiPackage,
  workorder: FiTruck,
  work_order: FiTruck,
  workorder_line: FiTruck,
  work_order_line: FiTruck,
  item: FiBox,
  document: FiFileText,
  contact: FiUsers,
  default: FiFolder,
};

/** Default table display names */
const DEFAULT_TABLE_NAMES: Record<string, string> = {
  proposal: 'Proposals',
  proposal_line: 'Proposal Lines',
  order: 'Orders',
  order_line: 'Order Lines',
  sales_order: 'Sales Orders',
  sales_order_line: 'Sales Order Lines',
  invoice: 'Invoices',
  invoice_line: 'Invoice Lines',
  purchase: 'Purchases',
  purchase_line: 'Purchase Lines',
  purchase_order: 'Purchase Orders',
  purchase_order_line: 'PO Lines',
  workorder: 'Work Orders',
  workorder_line: 'Work Order Lines',
  work_order: 'Work Orders',
  work_order_line: 'Work Order Lines',
  item: 'Items',
  document: 'Documents',
  contact: 'Contacts',
};

/** Common business flow order */
const DEFAULT_FLOW_ORDER = [
  'proposal',
  'proposal_line',
  'order',
  'sales_order',
  'order_line',
  'sales_order_line',
  'invoice',
  'invoice_line',
  'purchase',
  'purchase_order',
  'purchase_line',
  'purchase_order_line',
  'workorder',
  'work_order',
  'workorder_line',
  'work_order_line',
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Get icon for table type */
const getTableIcon = (tableName: string): React.ComponentType<{ className?: string }> => {
  const normalized = tableName.toLowerCase().replace(/s$/, ''); // Remove trailing 's'
  return TABLE_ICONS[normalized] || TABLE_ICONS.default;
};

/** Get display name for table */
const getTableDisplayName = (
  tableName: string, 
  customNames?: Record<string, string>
): string => {
  if (customNames?.[tableName]) return customNames[tableName];
  const normalized = tableName.toLowerCase();
  if (DEFAULT_TABLE_NAMES[normalized]) return DEFAULT_TABLE_NAMES[normalized];
  // Convert snake_case to Title Case
  return tableName
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
};

/** Format timestamp */
const formatDate = (ts?: number): string => {
  if (!ts) return '';
  const date = new Date(ts);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
};

/** Sort tables by flow order */
const sortTablesByFlow = (
  tables: string[], 
  flowOrder: string[] = DEFAULT_FLOW_ORDER
): string[] => {
  return [...tables].sort((a, b) => {
    const aIndex = flowOrder.indexOf(a.toLowerCase());
    const bIndex = flowOrder.indexOf(b.toLowerCase());
    // Items in flow order come first, sorted by flow order
    if (aIndex !== -1 && bIndex !== -1) return aIndex - bIndex;
    if (aIndex !== -1) return -1;
    if (bIndex !== -1) return 1;
    // Others sorted alphabetically
    return a.localeCompare(b);
  });
};

// ---------------------------------------------------------------------------
// Subcomponents
// ---------------------------------------------------------------------------

interface LinkedTableSectionProps {
  tableName: string;
  records: (LinkedRecord | number)[];
  displayName: string;
  isExpanded: boolean;
  onToggle: () => void;
  onRecordClick?: (tableName: string, recordId: number, record?: LinkedRecord) => void;
  isInFlow?: boolean;
}

const LinkedTableSection: React.FC<LinkedTableSectionProps> = ({
  tableName,
  records,
  displayName,
  isExpanded,
  onToggle,
  onRecordClick,
  isInFlow,
}) => {
  const Icon = getTableIcon(tableName);
  const recordCount = records.length;

  return (
    <div className={`border rounded-lg ${isInFlow ? 'border-violet-200 dark:border-violet-800' : 'border-gray-200 dark:border-gray-700'}`}>
      {/* Header */}
      <button
        onClick={onToggle}
        className={`w-full flex items-center justify-between p-3 text-left hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors ${
          isInFlow ? 'bg-violet-50 dark:bg-violet-900/20' : ''
        }`}
      >
        <div className="flex items-center gap-2">
          <Icon className={`w-4 h-4 ${isInFlow ? 'text-violet-600 dark:text-violet-400' : 'text-gray-500 dark:text-gray-400'}`} />
          <span className="font-medium text-gray-900 dark:text-gray-100">{displayName}</span>
          <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded-full">
            {recordCount}
          </span>
          {isInFlow && (
            <span className="text-xs text-violet-600 dark:text-violet-400 bg-violet-100 dark:bg-violet-900/40 px-2 py-0.5 rounded-full">
              Flow
            </span>
          )}
        </div>
        {isExpanded ? (
          <FiChevronDown className="w-4 h-4 text-gray-400" />
        ) : (
          <FiChevronRight className="w-4 h-4 text-gray-400" />
        )}
      </button>

      {/* Records list */}
      {isExpanded && (
        <div className="border-t border-gray-200 dark:border-gray-700">
          {records.map((record, index) => {
            const isNumber = typeof record === 'number';
            const recordId = isNumber ? record : record.id;
            const recordData = isNumber ? undefined : record;
            const display = recordData?.display || recordData?.name || recordData?.ida || `#${recordId}`;

            return (
              <div
                key={recordId}
                className={`flex items-center justify-between p-2 pl-10 ${
                  index !== records.length - 1 ? 'border-b border-gray-100 dark:border-gray-800' : ''
                } hover:bg-gray-50 dark:hover:bg-gray-800`}
              >
                <div className="flex flex-col">
                  <span className="text-sm text-gray-900 dark:text-gray-100">
                    {display}
                  </span>
                  {recordData?.status && (
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      Status: {recordData.status}
                    </span>
                  )}
                  {recordData?.dt_created && (
                    <span className="text-xs text-gray-400 dark:text-gray-500">
                      Created: {formatDate(recordData.dt_created)}
                    </span>
                  )}
                </div>
                {onRecordClick && (
                  <button
                    onClick={() => onRecordClick(tableName, recordId, recordData)}
                    className="p-1 text-gray-400 hover:text-violet-600 dark:hover:text-violet-400 transition-colors"
                    title={`View ${tableName} #${recordId}`}
                  >
                    <FiExternalLink className="w-4 h-4" />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

const LinkagesPanel: React.FC<LinkagesPanelProps> = ({
  entityType,
  entityId: _entityId,
  data,
  onChange: _onChange,
  readOnly: _readOnly,
  viewRoles = DEFAULT_VIEW_ROLES,
  editRoles = DEFAULT_EDIT_ROLES,
  className = '',
  compact = false,
  title = 'Linkages',
  defaultCollapsed = false,
  onRecordClick,
  onViewLinkage,
  flowTables = DEFAULT_FLOW_ORDER,
  tableDisplayNames,
}) => {
  const { canView } = usePermissions({ viewRoles, editRoles });
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());

  // Parse and organize links
  const organizedLinks = useMemo(() => {
    if (!data?.refs?.links) return { tables: [], linksByTable: {} as Record<string, (LinkedRecord | number)[]> };

    const links = data.refs.links;
    const tables = Object.keys(links).filter(
      (key) => Array.isArray(links[key]) && links[key]!.length > 0
    );

    const sortedTables = sortTablesByFlow(tables, flowTables);
    const linksByTable: Record<string, (LinkedRecord | number)[]> = {};

    for (const table of sortedTables) {
      linksByTable[table] = links[table] || [];
    }

    return { tables: sortedTables, linksByTable };
  }, [data, flowTables]);

  // Calculate stats
  const stats = useMemo(() => {
    const totalRecords = Object.values(organizedLinks.linksByTable).reduce(
      (sum, records) => sum + records.length,
      0
    );
    const flowTableCount = organizedLinks.tables.filter((t) =>
      flowTables.some((f) => f.toLowerCase() === t.toLowerCase())
    ).length;

    return { totalRecords, tableCount: organizedLinks.tables.length, flowTableCount };
  }, [organizedLinks, flowTables]);

  // Toggle table expansion
  const toggleTable = (tableName: string) => {
    setExpandedTables((prev) => {
      const next = new Set(prev);
      if (next.has(tableName)) {
        next.delete(tableName);
      } else {
        next.add(tableName);
      }
      return next;
    });
  };

  // Expand/collapse all
  const expandAll = () => setExpandedTables(new Set(organizedLinks.tables));
  const collapseAll = () => setExpandedTables(new Set());

  // Permission check
  if (!canView) {
    return null;
  }

  // No linkage data
  if (!data) {
    return (
      <div className={`bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 ${className}`}>
        <div className="flex items-center gap-2 p-4 border-b border-gray-200 dark:border-gray-700">
          <FiLink2 className="w-5 h-5 text-violet-600 dark:text-violet-400" />
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
        </div>
        <div className="p-4 text-center text-gray-500 dark:text-gray-400">
          <FiLink2 className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p>No linkage associated with this {entityType}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white dark:bg-gray-900 rounded-lg border border-violet-200 dark:border-violet-800 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-violet-200 dark:border-violet-800 bg-violet-50 dark:bg-violet-900/20">
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="flex items-center gap-2 hover:opacity-80 transition-opacity"
        >
          <FiLink2 className="w-5 h-5 text-violet-600 dark:text-violet-400" />
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
          {data.purpose && (
            <span className="text-sm text-violet-600 dark:text-violet-400">
              ({data.purpose})
            </span>
          )}
          {isCollapsed ? (
            <FiChevronRight className="w-4 h-4 text-gray-400" />
          ) : (
            <FiChevronDown className="w-4 h-4 text-gray-400" />
          )}
        </button>

        <div className="flex items-center gap-3">
          {/* Stats badges */}
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-500 dark:text-gray-400">
              {stats.totalRecords} records
            </span>
            <span className="text-gray-300 dark:text-gray-600">|</span>
            <span className="text-gray-500 dark:text-gray-400">
              {stats.tableCount} tables
            </span>
            {stats.flowTableCount > 0 && (
              <>
                <span className="text-gray-300 dark:text-gray-600">|</span>
                <span className="text-violet-600 dark:text-violet-400">
                  {stats.flowTableCount} in flow
                </span>
              </>
            )}
          </div>

          {/* View linkage button */}
          {onViewLinkage && (
            <button
              onClick={() => onViewLinkage(data.id)}
              className="text-xs text-violet-600 dark:text-violet-400 hover:underline"
            >
              View Linkage #{data.id}
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className="p-4">
          {/* Linkage info */}
          {(data.name || data.note) && !compact && (
            <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
              {data.name && (
                <p className="font-medium text-gray-900 dark:text-gray-100">{data.name}</p>
              )}
              {data.note && (
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{data.note}</p>
              )}
            </div>
          )}

          {/* Expand/collapse controls */}
          {organizedLinks.tables.length > 1 && (
            <div className="flex justify-end gap-2 mb-3">
              <button
                onClick={expandAll}
                className="text-xs text-violet-600 dark:text-violet-400 hover:underline"
              >
                Expand All
              </button>
              <span className="text-gray-300 dark:text-gray-600">|</span>
              <button
                onClick={collapseAll}
                className="text-xs text-violet-600 dark:text-violet-400 hover:underline"
              >
                Collapse All
              </button>
            </div>
          )}

          {/* Linked tables */}
          <div className={`space-y-2 ${compact ? 'max-h-64 overflow-y-auto' : ''}`}>
            {organizedLinks.tables.length === 0 ? (
              <p className="text-center text-gray-500 dark:text-gray-400 py-4">
                No linked records
              </p>
            ) : (
              organizedLinks.tables.map((tableName) => (
                <LinkedTableSection
                  key={tableName}
                  tableName={tableName}
                  records={organizedLinks.linksByTable[tableName]}
                  displayName={getTableDisplayName(tableName, tableDisplayNames)}
                  isExpanded={expandedTables.has(tableName)}
                  onToggle={() => toggleTable(tableName)}
                  onRecordClick={onRecordClick}
                  isInFlow={flowTables.some(
                    (f) => f.toLowerCase() === tableName.toLowerCase()
                  )}
                />
              ))
            )}
          </div>

          {/* Timestamps */}
          {!compact && (data.dt_created || data.dt_modified) && (
            <div className="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-400 dark:text-gray-500 flex gap-4">
              {data.dt_created && <span>Created: {formatDate(data.dt_created)}</span>}
              {data.dt_modified && <span>Modified: {formatDate(data.dt_modified)}</span>}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default LinkagesPanel;
