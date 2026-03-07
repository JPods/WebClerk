/**
 * DetailTabs - Reusable tab navigation component for Detail pages
 *
 * Implements the standard tab layout from detail-page-standardization-plan.md:
 * - Overview, Comments, Actions, Documents, History (admin), Raw (admin)
 * - Model-specific tabs injected via additionalTabs prop
 * - Persists active tab to localStorage
 * - Role-based visibility for admin tabs
 *
 * @see readmes/detail-page-standardization-plan.md
 */
import React, { useState, useCallback } from "react";
import {
  FaCode,
  FaColumns,
  FaComments,
  FaDollarSign,
  FaFile,
  FaInfoCircle,
  FaTasks,
  FaUsers,
} from "react-icons/fa";
import { useAppSelector } from "@/store/hooks";

// Standard panels for automatic rendering
// DetailTabs auto-renders these 5 panels when `recordData` is provided:
//   - ActionsPanel        (tab: actions)
//   - CommentsPanel       (tab: comments)
//   - DocumentsPanel      (tab: documents)
//   - FinancialsPanel     (tab: financials)
//   - JsonFieldEditor     (tab: raw)
//
// Additional panels available via `additionalTabs[].content` (manual render):
//   - BasicInformationPanel, CommunicationsPanel, ContactPanel,
//     LinkagesPanel, MetadataPanel, PrefsPanel, QAPanel,
//     RawDataPanel, ShippingPanel
// Full inventory: src/apps/common/components/panels/index.ts
import {
  ActionsPanel,
  CommentsPanel,
  DocumentsPanel,
} from "@/apps/common/components/panels";
import type { EntityType } from "@/apps/common/components/panels/types";
import FinancialsPanel from "@/apps/common/components/panels/FinancialsPanel";
import JsonFieldEditor from "@/apps/common/components/JsonFieldEditor";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TabConfig {
  id: string;
  label: string;
  icon?: React.ReactNode;
  badge?: number | string;
  /** Only show for admin users */
  adminOnly?: boolean;
  /** Only show for specific roles */
  roles?: string[];
  /** Hide this tab */
  hidden?: boolean;
  /** Custom panel content rendered when this tab is active (for additional tabs) */
  content?: React.ReactNode;
}

export interface DetailTabsProps {
  /** Entity type for localStorage key (e.g., 'customer', 'order') */
  entityType: string;
  /** Currently active tab */
  activeTab: string;
  /** Tab change handler */
  onTabChange: (tabId: string) => void;
  /** Standard tabs to include (default: all standard) */
  standardTabs?: (
    | "actions"
    | "comments"
    | "contacts"
    | "documents"
    | "financials"
    | "overview"
    | "raw"
  )[];
  /** Additional model-specific tabs (inserted before admin tabs) */
  additionalTabs?: TabConfig[];
  /** Badges for standard tabs (e.g., { comments: 5, actions: 2 }) */
  badges?: Record<string, number | string>;
  /** Show column count selector */
  showColumnSelector?: boolean;
  /** Current column count */
  columnCount?: 2 | 3;
  /** Column count change handler */
  onColumnCountChange?: (count: 2 | 3) => void;
  /** Custom class for tab bar */
  className?: string;
  // ---- Panel rendering (when provided, DetailTabs auto-renders tab content) ----
  /** Entity ID passed to panel components */
  entityId?: string | number;
  /** Full record data – presence triggers automatic panel rendering */
  recordData?: any;
  /** Entity type used for panels (defaults to entityType) */
  panelEntityType?: string;
  /** Whether panels are in edit mode */
  isEditing?: boolean;
  /** Callback when a standard panel updates the record */
  onRecordChange?: (data: any) => void;
}

// ---------------------------------------------------------------------------
// Standard Tab Definitions
// ---------------------------------------------------------------------------

const STANDARD_TAB_CONFIGS: Record<string, TabConfig> = {
  actions: {
    id: "actions",
    label: "Actions",
    icon: <FaTasks size={14} />,
  },
  comments: {
    id: "comments",
    label: "Comments",
    icon: <FaComments size={14} />,
  },
  contacts: {
    id: "contacts",
    label: "Contacts",
    icon: <FaUsers size={14} />,
  },
  documents: {
    id: "documents",
    label: "Documents",
    icon: <FaFile size={14} />,
  },
  financials: {
    id: "financials",
    label: "Financials",
    icon: <FaDollarSign size={14} />,
  },
  overview: {
    id: "overview",
    label: "Overview",
    icon: <FaInfoCircle size={14} />,
  },
  raw: {
    id: "raw",
    label: "Raw",
    icon: <FaCode size={14} />,
    adminOnly: true,
  },
};

const DEFAULT_STANDARD_TABS: (keyof typeof STANDARD_TAB_CONFIGS)[] = [
  "actions",
  "comments",
  "documents",
  "raw",
];

// ---------------------------------------------------------------------------
// Column Selector Component
// ---------------------------------------------------------------------------

interface ColumnSelectorProps {
  value: 2 | 3;
  onChange: (count: 2 | 3) => void;
}

export const ColumnSelector: React.FC<ColumnSelectorProps> = ({
  value,
  onChange,
}) => (
  <div className="flex items-center gap-2 shrink-0 bg-slate-100 dark:bg-slate-700 rounded-md px-2 py-0">
    <FaColumns className="text-slate-500 dark:text-slate-400" size={12} />
    <span className="text-xs text-slate-500 dark:text-slate-400">Cols:</span>
    <div className="flex rounded border border-slate-300 dark:border-slate-600 overflow-hidden">
      {[2, 3].map((count) => (
        <button
          key={count}
          type="button"
          onClick={() => onChange(count as 2 | 3)}
          className={`px-2 py-0.5 text-xs font-medium transition-colors ${
            value === count
              ? "bg-blue-500 text-white"
              : "bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700"
          }`}
        >
          {count}
        </button>
      ))}
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// Tab Button Component
// ---------------------------------------------------------------------------

interface TabButtonProps {
  tab: TabConfig;
  isActive: boolean;
  onClick: () => void;
}

const TabButton: React.FC<TabButtonProps> = ({ tab, isActive, onClick }) => (
  <button
    type="button"
    onClick={onClick}
    className={`flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-all duration-200 whitespace-nowrap ${
      isActive
        ? "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border-b-2 border-blue-600"
        : "text-slate-500 hover:text-slate-700 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700"
    }`}
  >
    {tab.icon}
    {tab.label}
    {tab.badge !== undefined && tab.badge !== 0 && (
      <span className="ml-1 px-1.5 py-0.5 text-xs bg-slate-200 dark:bg-slate-600 rounded-full">
        {tab.badge}
      </span>
    )}
  </button>
);

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export const DetailTabs: React.FC<DetailTabsProps> = ({
  entityType,
  activeTab,
  onTabChange,
  standardTabs = DEFAULT_STANDARD_TABS,
  additionalTabs = [],
  badges = {},
  showColumnSelector = false,
  columnCount = 3,
  onColumnCountChange,
  className = "",
  entityId,
  recordData,
  panelEntityType,
  isEditing = false,
  onRecordChange,
}) => {
  // Get current user role for admin tab visibility
  const user = useAppSelector((state) => state.auth.user);
  // Normalize role to string for comparison (handle both string and string[])
  const userRole = Array.isArray(user?.role) ? user?.role[0] : user?.role;
  const isAdmin =
    userRole &&
    ["admin", "superadmin", "super_admin", "administrator"].includes(userRole);

  // Panel configuration
  const effectiveEntityType = (panelEntityType || entityType) as EntityType;
  const numericEntityId =
    typeof entityId === "string" ? parseInt(entityId, 10) : entityId;
  const rawLabel = React.useMemo(
    () =>
      `Full ${effectiveEntityType
        .split("_")
        .map((w: string) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(" ")} JSON`,
    [effectiveEntityType],
  );

  // Build tab list
  const tabs = React.useMemo(() => {
    const result: TabConfig[] = [];

    // Add standard tabs (non-admin)
    standardTabs.forEach((tabKey) => {
      const tabConfig = STANDARD_TAB_CONFIGS[tabKey];
      if (tabConfig && !tabConfig.adminOnly) {
        result.push({
          ...tabConfig,
          badge: badges[tabKey],
        });
      }
    });

    // Add additional model-specific tabs
    additionalTabs.forEach((tab) => {
      if (!tab.hidden) {
        // Check role-based visibility
        if (tab.roles && userRole && !tab.roles.includes(userRole)) {
          return;
        }
        if (tab.adminOnly && !isAdmin) {
          return;
        }
        result.push({
          ...tab,
          badge: badges[tab.id] ?? tab.badge,
        });
      }
    });

    // Add admin tabs at the end
    if (isAdmin) {
      standardTabs.forEach((tabKey) => {
        const tabConfig = STANDARD_TAB_CONFIGS[tabKey];
        if (tabConfig?.adminOnly) {
          result.push({
            ...tabConfig,
            badge: badges[tabKey],
          });
        }
      });
    }

    return result;
  }, [standardTabs, additionalTabs, badges, isAdmin, userRole]);

  // Handle tab change with localStorage persistence
  const handleTabChange = useCallback(
    (tabId: string) => {
      onTabChange(tabId);
      localStorage.setItem(`${entityType}Detail_activeTab`, tabId);
    },
    [entityType, onTabChange],
  );

  // Handle column count change with localStorage persistence
  const handleColumnChange = useCallback(
    (count: 2 | 3) => {
      onColumnCountChange?.(count);
      localStorage.setItem(`${entityType}Detail_columnCount`, String(count));
    },
    [entityType, onColumnCountChange],
  );

  return (
    <>
      <div
        className={`shrink-0  border-slate-200 dark:border-slate-700 ${className}`}
      >
        <nav className="px-0">
          <div className="flex items-center justify-between py-2 gap-4">
            <div className="flex gap-1 overflow-x-auto">
              {tabs.map((tab) => (
                <TabButton
                  key={tab.id}
                  tab={tab}
                  isActive={activeTab === tab.id}
                  onClick={() => handleTabChange(tab.id)}
                />
              ))}
            </div>
            {showColumnSelector && onColumnCountChange && (
              <ColumnSelector
                value={columnCount}
                onChange={handleColumnChange}
              />
            )}
          </div>
        </nav>
      </div>

      {/* ---- Standard Panel Content (auto-rendered when recordData is provided) ---- */}
      {recordData !== undefined && (
        <div className="mt-4">
          {activeTab === "actions" && standardTabs.includes("actions") && (
            <ActionsPanel
              entityType={effectiveEntityType}
              entityId={numericEntityId as number}
              data={recordData?.actions?.items}
              actionIds={recordData?.actions?.ids}
              isEditing={isEditing}
              onChange={(actions: any) =>
                onRecordChange?.({
                  ...recordData,
                  actions: { ...recordData?.actions, items: actions },
                })
              }
            />
          )}

          {activeTab === "comments" && standardTabs.includes("comments") && (
            <CommentsPanel
              comments={recordData?.comments}
              isEditing={isEditing}
              entityType={effectiveEntityType}
              entityId={numericEntityId as number}
              onChange={(comments: any) =>
                onRecordChange?.({ ...recordData, comments })
              }
            />
          )}

          {activeTab === "documents" && standardTabs.includes("documents") && (
            <DocumentsPanel
              parent_model={effectiveEntityType}
              parentId={numericEntityId}
              data={recordData?.refs?.links?.document}
              isEditing={isEditing}
              onChange={(docs: any) =>
                onRecordChange?.({
                  ...recordData,
                  refs: {
                    ...recordData?.refs,
                    links: { ...recordData?.refs?.links, document: docs },
                  },
                })
              }
            />
          )}

          {activeTab === "financials" &&
            standardTabs.includes("financials") && (
              <FinancialsPanel
                totals={recordData?.financial?.totals}
                cost={recordData?.financial?.cost}
                sell={recordData?.financial?.sell}
                currency={recordData?.financial?.currency}
              />
            )}

          {activeTab === "raw" && standardTabs.includes("raw") && (
            <JsonFieldEditor
              label={rawLabel}
              value={recordData}
              readonly
              defaultExpanded
              maxHeight="600px"
            />
          )}

          {/* Custom tab content from additionalTabs */}
          {additionalTabs.map((tab) =>
            activeTab === tab.id && tab.content ? (
              <React.Fragment key={tab.id}>{tab.content}</React.Fragment>
            ) : null,
          )}
        </div>
      )}
    </>
  );
};

// ---------------------------------------------------------------------------
// Hook for managing tab state with localStorage
// ---------------------------------------------------------------------------

export function useDetailTabs(
  entityType: string,
  defaultTab: string = "overview",
  validTabs?: string[],
) {
  const storageKey = `${entityType}Detail_activeTab`;

  const [activeTab, setActiveTab] = useState(() => {
    const stored = localStorage.getItem(storageKey);
    if (stored && (!validTabs || validTabs.includes(stored))) {
      return stored;
    }
    return defaultTab;
  });

  const handleTabChange = useCallback(
    (tabId: string) => {
      setActiveTab(tabId);
      localStorage.setItem(storageKey, tabId);
    },
    [storageKey],
  );

  return { activeTab, setActiveTab: handleTabChange };
}

// ---------------------------------------------------------------------------
// Hook for managing column count with localStorage
// ---------------------------------------------------------------------------

export function useColumnCount(entityType: string, defaultCount: 2 | 3 = 3) {
  const storageKey = `${entityType}Detail_columnCount`;

  const [columnCount, setColumnCount] = useState<2 | 3>(() => {
    const stored = localStorage.getItem(storageKey);
    return stored === "2" ? 2 : stored === "3" ? 3 : defaultCount;
  });

  const handleColumnChange = useCallback(
    (count: 2 | 3) => {
      setColumnCount(count);
      localStorage.setItem(storageKey, String(count));
    },
    [storageKey],
  );

  return { columnCount, setColumnCount: handleColumnChange };
}

export default DetailTabs;
