/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import React, {
  RefObject,
  useMemo,
  useRef,
  useState,
  useEffect,
  useCallback,
} from "react";
import { Link } from "react-router-dom";
/** Column shape compatible with legacy TableColumn (no react-data-table-component dep) */
type TableColumn<T = any> = {
  id?: string | number;
  name?: string | React.ReactNode;
  selector?: ((row: T, index?: number) => any) | string;
  cell?: (row: T, index: number, column: any, id: any) => React.ReactNode;
  sortable?: boolean;
  width?: string;
  [key: string]: any;
};
import {
  FaSearch,
  FaPlus,
  FaTrash,
  FaDownload,
  FaFileImport,
  FaPrint,
  FaTimes,
  FaCheckSquare,
  FaGripVertical,
  FaSync,
  FaFilter,
  FaFileExcel,
  FaFilePdf,
  FaFileCode,
} from "react-icons/fa";
import PrintReportDropdown, {
  type QuickFilterItem,
} from "./PrintReportDropdown";
import SearchPresetDropdown from "./SearchPresetDropdown";
import { getReportsForModel, type ReportDef } from "@/config/reportLists";
import {
  useColumnSetups,
  type ColumnSetupEntry,
} from "@/hooks/useColumnSetups";
import { ColumnSetupDialog } from "./ColumnSetupDialog";
import Badge from "../ui/badge/Badge";
import {
  type SearchPresetInputValue,
  type SearchPresetRecord,
} from "@/api/wcapi";

type ActivePresetState = {
  id?: number;
  name: string;
};

export interface ColumnFilter {
  key: string;
  label: string;
  type?: string;
  options?: Array<{ value: string; label: string }>;
}

interface BreadcrumbProps<T = any> {
  pageTitle: string;
  title?: string;
  modelKey?: string;
  searchTerm?: string;
  onSearchTermChange?: (value: string) => void;
  handleAddInline?: () => void;
  handleBulkDelete?: () => void;
  tableRef?: RefObject<any>;
  columnBtnRef?: RefObject<HTMLButtonElement | null>;
  importInputRef?: RefObject<HTMLInputElement | null>;
  selectedRows?: any[];
  selectedCount?: number;
  totalCount?: number;
  filteredCount?: number;
  onPrint?: () => void;
  /** Called when user picks a report from the print dropdown (requires modelKey to have reports in reportLists) */
  onSelectReport?: (report: ReportDef) => void;
  /** Quick-filter items shown in the print/report dropdown above reports */
  quickFilters?: QuickFilterItem[];
  /** Called when a quick-filter item is clicked */
  onQuickFilter?: (key: string) => void;
  onRefresh?: () => void;
  loading?: boolean;
  enableDatabaseSearch?: boolean;
  searchDatabase?: boolean;
  onSearchModeChange?: (v: boolean) => void;
  filtersOpen?: boolean;
  onFiltersOpenChange?: (open: boolean) => void;
  filters?: ColumnFilter[];
  filterValues?: Record<string, string>;
  onFilterValuesChange?: (values: Record<string, string>) => void;
  enableExport?: boolean;
  exportFileName?: string;
  onImportFile?: (file: File) => void;
  // Column management props
  columns?: TableColumn<T>[];
  columnVisibility?: boolean[];
  onColumnVisibilityChange?: (visibility: boolean[]) => void;
  onColumnsChange?: (columns: TableColumn<T>[]) => void;
  storageKey?: string;
  // Custom content slots
  customActions?: React.ReactNode;
  summaryContent?: React.ReactNode;
  children?: React.ReactNode;
  onApplySearchPreset?: (
    preset: SearchPresetRecord,
    values?: Record<string, SearchPresetInputValue>,
  ) => Promise<void> | void;
}

const ButtonToolbar = <T extends Record<string, any> = any>({
  pageTitle,
  title,
  modelKey,
  searchTerm = "",
  onSearchTermChange,
  handleAddInline,
  handleBulkDelete,
  tableRef,
  columnBtnRef,
  importInputRef,
  selectedRows = [],
  selectedCount,
  totalCount,
  filteredCount,
  onPrint,
  onSelectReport,
  quickFilters,
  onQuickFilter,
  onRefresh,
  loading,
  enableDatabaseSearch,
  searchDatabase,
  onSearchModeChange,
  filtersOpen,
  onFiltersOpenChange,
  filters = [],
  filterValues = {},
  onFilterValuesChange,
  enableExport = true,
  exportFileName: _exportFileName = "export",
  onImportFile,
  // Column management
  columns = [],
  columnVisibility: externalColumnVisibility,
  onColumnVisibilityChange,
  onColumnsChange,
  storageKey,
  // Custom content slots
  customActions,
  summaryContent,
  children,
  onApplySearchPreset,
}: BreadcrumbProps<T>) => {
  // exportFileName available for future use if needed
  void _exportFileName;
  const count = selectedCount ?? selectedRows?.length ?? 0;
  // canExport is true when tableRef is provided - the ref methods handle gracefully if not ready
  const canExport = Boolean(tableRef);
  const canSelect = Boolean(tableRef?.current?.selectAll);

  const columnManagerRef = useRef<HTMLDivElement>(null);
  const exportDropdownRef = useRef<HTMLDivElement>(null);
  const exportDropdownPanelRef = useRef<HTMLDivElement>(null);
  const localImportInputRef = useRef<HTMLInputElement>(null);
  const localColumnBtnRef = useRef<HTMLButtonElement>(null);

  const [showExportDropdown, setShowExportDropdown] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [activePreset, setActivePreset] =
    useState<ActivePresetState | null>(null);
  const [exportDropdownPosition, setExportDropdownPosition] = useState<{
    top: number;
    left: number;
  } | null>(null);

  // Internal column visibility state (used when not controlled externally)
  const [internalColumnVisibility, setInternalColumnVisibility] = useState<
    boolean[]
  >(() => columns.map(() => true));
  const [internalColumns, setInternalColumns] =
    useState<TableColumn<T>[]>(columns);

  const getColumnIdentity = useCallback(
    (col: TableColumn<T>, index: number) => {
      if (col.id != null) return `id:${String(col.id)}`;
      if (typeof col.name === "string")
        return `name:${col.name.trim().toLowerCase()}`;
      if (typeof col.selector === "string")
        return `selector:${(col.selector as string).trim().toLowerCase()}`;
      if (typeof col.sortField === "string")
        return `sortField:${col.sortField.trim().toLowerCase()}`;
      return `index:${index}`;
    },
    [],
  );

  const incomingSchemaSignature = useMemo(
    () =>
      columns
        .map((col, index) => getColumnIdentity(col, index))
        .sort()
        .join("|"),
    [columns, getColumnIdentity],
  );

  const internalSchemaSignature = useMemo(
    () =>
      internalColumns
        .map((col, index) => getColumnIdentity(col, index))
        .sort()
        .join("|"),
    [internalColumns, getColumnIdentity],
  );

  // Column setups (named presets via hook)
  const columnSetupsApi = useColumnSetups(storageKey, modelKey);
  const [editingSetupName, setEditingSetupName] = useState<string | null>(null);

  // Use external or internal visibility
  const columnVisibility = externalColumnVisibility ?? internalColumnVisibility;

  // Use external or internal columns
  const currentColumns = onColumnsChange ? columns : internalColumns;

  const effectiveShowFilters = filtersOpen ?? showFilters;
  const setEffectiveShowFilters = onFiltersOpenChange ?? setShowFilters;
  const effectiveImportInputRef = importInputRef ?? localImportInputRef;
  const effectiveColumnBtnRef = columnBtnRef ?? localColumnBtnRef;

  // Sync internal state when columns prop changes
  useEffect(() => {
    if (columns.length === 0) return;

    // Controlled mode: mirror parent columns exactly.
    if (onColumnsChange) {
      setInternalColumns(columns);
      return;
    }

    // Uncontrolled mode: initialize once, then preserve local drag order unless schema changes.
    if (internalColumns.length === 0) {
      setInternalColumns(columns);
      if (!externalColumnVisibility) {
        setInternalColumnVisibility(columns.map(() => true));
      }
      return;
    }

    if (incomingSchemaSignature !== internalSchemaSignature) {
      setInternalColumns(columns);
      if (!externalColumnVisibility) {
        setInternalColumnVisibility(columns.map(() => true));
      }
    }
  }, [
    columns,
    externalColumnVisibility,
    onColumnsChange,
    internalColumns.length,
    incomingSchemaSignature,
    internalSchemaSignature,
  ]);

  // Load persisted column layout + setups
  useEffect(() => {
    if (!storageKey || columns.length === 0) return;

    try {
      const saved = localStorage.getItem(
        `PageBreadcrumb:${storageKey}:columns`,
      );
      if (saved) {
        const { visibility } = JSON.parse(saved);
        if (Array.isArray(visibility) && visibility.length === columns.length) {
          if (onColumnVisibilityChange) {
            onColumnVisibilityChange(visibility);
          } else {
            setInternalColumnVisibility(visibility);
          }
        }
      }
    } catch {
      // Ignore errors
    }
  }, [storageKey, columns.length, onColumnVisibilityChange]);

  // Save column layout
  // Column persist-key helper (matches AdvancedDataTable logic)
  const getColumnPersistKey = useCallback(
    (col: TableColumn<T>, index: number): string => {
      if (col.id != null) return `id:${String(col.id)}`;
      if (typeof col.name === "string")
        return `name:${col.name.trim().toLowerCase()}`;
      if (typeof col.selector === "string")
        return `selector:${(col.selector as string).trim().toLowerCase()}`;
      if (typeof col.sortField === "string")
        return `sortField:${col.sortField.trim().toLowerCase()}`;
      return `index:${index}`;
    },
    [],
  );

  const saveColumnLayout = useCallback(
    (visibility: boolean[]) => {
      if (!storageKey) return;
      try {
        localStorage.setItem(
          `PageBreadcrumb:${storageKey}:columns`,
          JSON.stringify({ visibility }),
        );
      } catch {
        // Ignore errors
      }
    },
    [storageKey],
  );

  const syncTableLayout = useCallback(
    (nextColumns: TableColumn<T>[], nextVisibility: boolean[]) => {
      const order = nextColumns.map((c, i) => getColumnPersistKey(c, i));
      const visibility: Record<string, boolean> = {};
      order.forEach((key, i) => {
        visibility[key] = nextVisibility[i] ?? true;
      });

      tableRef?.current?.applyColumnLayout?.({ order, visibility });

      if (storageKey) {
        try {
          localStorage.setItem(
            `AdvancedDataTable:v1:${storageKey}:columns`,
            JSON.stringify({ v: 1 as const, order, visibility }),
          );
        } catch {
          // Ignore storage errors
        }
      }
    },
    [tableRef, storageKey, getColumnPersistKey],
  );

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      // Close export dropdown if click is outside both button and panel
      const isInsideExportButton = exportDropdownRef.current?.contains(target);
      const isInsideExportPanel =
        exportDropdownPanelRef.current?.contains(target);
      if (!isInsideExportButton && !isInsideExportPanel) {
        setShowExportDropdown(false);
      }
    };

    if (showExportDropdown) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showExportDropdown]);

  const handleImportChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && onImportFile) {
      onImportFile(file);
    }
    e.currentTarget.value = "";
  };

  const clearFilters = () => {
    onSearchTermChange?.("");
    onFilterValuesChange?.({});
    setActivePreset(null);
  };

  const handleApplySearchPreset = useCallback(
    async (
      preset: SearchPresetRecord,
      values?: Record<string, SearchPresetInputValue>,
    ) => {
      await onApplySearchPreset?.(preset, values);
      setActivePreset({ id: preset.id, name: preset.name || "Saved Search" });
    },
    [onApplySearchPreset],
  );

  const activeFilterCount = Object.values(filterValues).filter(Boolean).length;

  // Build current snapshot for saving as a setup
  const buildCurrentConfig = useCallback((): ColumnSetupEntry => {
    const order = currentColumns.map((c, i) => getColumnPersistKey(c, i));
    const visibility: Record<string, boolean> = {};
    const widths: Record<string, string> = {};
    currentColumns.forEach((col, i) => {
      const key = getColumnPersistKey(col, i);
      visibility[key] = columnVisibility[i] ?? true;
      if (col.width) widths[key] = col.width;
    });
    return { order, visibility, widths, sort: null };
  }, [currentColumns, columnVisibility, getColumnPersistKey]);

  // Apply a ColumnSetupEntry to current columns
  const applyConfig = useCallback(
    (config: ColumnSetupEntry) => {
      const byKey = new Map<string, { col: TableColumn<T>; origIdx: number }>();
      currentColumns.forEach((col, i) => {
        byKey.set(getColumnPersistKey(col, i), { col, origIdx: i });
      });

      const reordered: TableColumn<T>[] = [];
      const newVis: boolean[] = [];
      const used = new Set<string>();

      // Apply saved order first
      for (const key of config.order) {
        const entry = byKey.get(key);
        if (entry) {
          const c = { ...entry.col };
          if (config.widths[key]) c.width = config.widths[key];
          reordered.push(c);
          newVis.push(config.visibility[key] !== false);
          used.add(key);
        }
      }
      // Append any columns not in the saved order
      currentColumns.forEach((col, i) => {
        const key = getColumnPersistKey(col, i);
        if (!used.has(key)) {
          reordered.push(col);
          newVis.push(config.visibility[key] !== false);
        }
      });

      if (onColumnsChange) {
        onColumnsChange(reordered as TableColumn<T>[]);
      } else {
        setInternalColumns(reordered as TableColumn<T>[]);
      }
      if (onColumnVisibilityChange) {
        onColumnVisibilityChange(newVis);
      } else {
        setInternalColumnVisibility(newVis);
      }
      saveColumnLayout(newVis);
      void columnSetupsApi.uploadToServer(config);
      syncTableLayout(reordered as TableColumn<T>[], newVis);
    },
    [
      currentColumns,
      getColumnPersistKey,
      onColumnsChange,
      onColumnVisibilityChange,
      saveColumnLayout,
      columnSetupsApi,
      syncTableLayout,
    ],
  );

  // Column meta for the dialog
  const columnMetas = useMemo(
    () =>
      currentColumns.map((col, i) => ({
        key: getColumnPersistKey(col, i),
        label: String(col.name || col.id || `Column ${i + 1}`),
      })),
    [currentColumns, getColumnPersistKey],
  );

  const visibleColumnCount = columnVisibility.filter(Boolean).length;
  const totalColumnCount = currentColumns.length;

  return (
    <div className="flex flex-col gap-3 mb-4">
      {/* Top row: title and breadcrumbs */}
      <div className="flex items-center justify-between">
        {/* Actions & search row */}
        <div className="flex items-center w-full max-w-2xl md:gap-2 lg:max-w-3xl lg:gap-2">
          {/* Add Button */}
          <button
            onClick={handleAddInline}
            title="Add"
            className="w-9 h-9 flex items-center justify-center rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            disabled={!handleAddInline}
          >
            <FaPlus className="w-4 h-4" />
          </button>
          {/* Select All */}
          <button
            onClick={() => tableRef?.current?.selectAll?.()}
            title="Select All"
            className="w-9 h-9 flex items-center justify-center rounded-md bg-sky-600 text-white hover:bg-sky-700 disabled:opacity-50"
            disabled={!canSelect}
          >
            <FaCheckSquare className="w-4 h-4" />
          </button>
          {/* Clear Selection */}
          <button
            onClick={() => tableRef?.current?.clearSelection?.()}
            title="Clear Selection"
            className="w-9 h-9 py-4 flex items-center justify-center rounded-md bg-red-100 text-gray-700 hover:bg-gray-200 disabled:opacity-50"
            disabled={!canSelect || count === 0}
          >
            <FaTimes className="w-4 h-4" />
          </button>
          {/* Import */}
          <button
            onClick={() => effectiveImportInputRef?.current?.click()}
            title="Import"
            className="w-9 h-9 flex items-center justify-center rounded-md bg-slate-600 text-white hover:bg-slate-700 disabled:opacity-50"
            disabled={!onImportFile}
          >
            <FaFileImport className="w-4 h-4" />
          </button>
          <input
            ref={effectiveImportInputRef}
            type="file"
            accept=".json,.csv,.xlsx"
            className="hidden"
            onChange={handleImportChange}
          />
          {/* Print / Report dropdown */}
          {modelKey &&
          (getReportsForModel(modelKey).length > 0 ||
            (quickFilters && quickFilters.length > 0)) ? (
            <PrintReportDropdown
              modelKey={modelKey}
              onSelect={onSelectReport}
              quickFilters={quickFilters}
              onQuickFilter={onQuickFilter}
              compact
            />
          ) : (
            <button
              onClick={onPrint}
              disabled={!onPrint}
              title="Print"
              className="w-9 h-9 flex items-center justify-center rounded-md bg-yellow-500 text-white hover:bg-yellow-600 disabled:opacity-50"
            >
              <FaPrint className="w-4 h-4" />
            </button>
          )}
          {/* Export Dropdown */}
          {enableExport && (
            <div className="relative" ref={exportDropdownRef}>
              <button
                onClick={(e) => {
                  if (!showExportDropdown) {
                    const rect = e.currentTarget.getBoundingClientRect();
                    setExportDropdownPosition({
                      top: rect.bottom + 8,
                      left: rect.left,
                    });
                  }
                  setShowExportDropdown(!showExportDropdown);
                }}
                title="Export"
                className="w-9 h-9 flex items-center justify-center rounded-md bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
                disabled={!canExport}
              >
                <FaDownload className="w-4 h-4" />
              </button>
            </div>
          )}
          {/* Column Manager */}
          <div className="relative" ref={columnManagerRef}>
            <button
              ref={effectiveColumnBtnRef}
              onClick={() => setEditingSetupName("__current__")}
              title="Manage Columns"
              className="flex items-center gap-1 px-3 py-4 h-9 rounded-md bg-success-100 text-gray-700 hover:bg-gray-200 disabled:opacity-50"
              disabled={currentColumns.length === 0}
            >
              <FaGripVertical className="w-4 h-4" />
              {totalColumnCount > 0 && (
                <span className="text-xs font-medium">
                  {visibleColumnCount}/{totalColumnCount}
                </span>
              )}
            </button>
          </div>
          {/* Refresh */}
          <button
            onClick={onRefresh}
            disabled={!onRefresh || loading}
            title="Refresh"
            className="w-9 h-9 flex items-center justify-center rounded-md bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50"
          >
            <FaSync className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
          {/* Filters Toggle */}
          {filters.length > 0 && (
            <button
              onClick={() => setEffectiveShowFilters(!effectiveShowFilters)}
              className={`px-3 py-3 text-md font-medium rounded-md flex items-center gap-2 ${
                effectiveShowFilters
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
              title="Toggle Filters"
            >
              <FaFilter className="w-4 h-4" />

              {activeFilterCount > 0 && (
                <span className="px-1.5 py-0.5 text-xs rounded-full bg-white text-blue-600">
                  {activeFilterCount}
                </span>
              )}
            </button>
          )}
          {/* Clear Filters */}
          {(searchTerm || activeFilterCount > 0) && (
            <button
              onClick={clearFilters}
              className="px-3 py-2 text-xs font-medium rounded-md bg-gray-100 text-gray-700 hover:bg-gray-200 flex items-center gap-2"
              title="Clear Filters"
            >
              <FaTimes className="w-3 h-3" />
              Clear
            </button>
          )}
          {/* <div className="flex items-center justify-between"> */}
          <div className="relative">
            {enableDatabaseSearch && (
              <label className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400 whitespace-nowrap cursor-pointer select-none px-2">
                <input
                  type="checkbox"
                  checked={!!searchDatabase}
                  onChange={(e) => onSearchModeChange?.(e.target.checked)}
                  className="w-3.5 h-3.5 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 cursor-pointer"
                />
                <span>Query DB</span>
              </label>
            )}
          </div>
          {modelKey && onApplySearchPreset ? (
            <SearchPresetDropdown
              modelKey={modelKey}
              onApplyPreset={handleApplySearchPreset}
              disabled={loading}
              activePresetId={activePreset?.id}
            />
          ) : null}
          {activePreset ? (
            <span className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-md bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-200">
              {activePreset.name}
              <button
                type="button"
                onClick={() => setActivePreset(null)}
                className="text-indigo-500 hover:text-indigo-700 dark:text-indigo-300 dark:hover:text-indigo-100"
                title="Clear active saved search indicator"
              >
                <FaTimes className="w-3 h-3" />
              </button>
            </span>
          ) : null}
          <div className="relative">
            <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
              <FaSearch className="w-4 h-4 text-gray-400" />
            </div>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => onSearchTermChange?.(e.target.value)}
              placeholder={`Search ${title || modelKey || ""}`.trim()}
              className="w-full pl-10 pr-10 py-2.5 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white"
            />
            {searchTerm && (
              <button
                onClick={() => onSearchTermChange?.("")}
                className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
              >
                <FaTimes className="w-4 h-4" />
              </button>
            )}
          </div>
          <button
            onClick={handleBulkDelete}
            disabled={count === 0 || !handleBulkDelete}
            title="Delete Selected"
            className="w-9 h-9 flex text-xs items-center justify-center rounded-md bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
          >
            <FaTrash className="w-4 h-4" />
          </button>
          {selectedCount ? (
            <Badge color="warning">{selectedCount}</Badge>
          ) : null}
          {/* Custom Actions Slot */}
          {customActions}
          {/* </div> */}
        </div>
        <nav>
          <ol className="flex items-center gap-1.5">
            <li>
              <Link
                className="inline-flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400"
                to="/"
              >
                Home
                <svg
                  className="stroke-current"
                  width="17"
                  height="16"
                  viewBox="0 0 17 16"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M6.0765 12.667L10.2432 8.50033L6.0765 4.33366"
                    stroke=""
                    strokeWidth="1.2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </Link>
            </li>
            <li className="text-sm text-gray-800 dark:text-white/90">
              {pageTitle}
            </li>
          </ol>
        </nav>
      </div>

      {/* Filters Panel */}
      {effectiveShowFilters && filters.length > 0 && (
        <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filters.map((filter) => (
              <div key={filter.key}>
                <label className="block mb-2 text-xs font-medium text-gray-700 dark:text-gray-300">
                  {filter.label}
                </label>
                {filter.type === "select" && filter.options ? (
                  <select
                    value={filterValues[filter.key] || ""}
                    onChange={(e) =>
                      onFilterValuesChange?.({
                        ...filterValues,
                        [filter.key]: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                  >
                    <option value="">All</option>
                    {filter.options.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type={filter.type || "text"}
                    value={filterValues[filter.key] || ""}
                    onChange={(e) =>
                      onFilterValuesChange?.({
                        ...filterValues,
                        [filter.key]: e.target.value,
                      })
                    }
                    placeholder={`Filter by ${filter.label.toLowerCase()}`}
                    className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400"
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Stats row */}
      <div className="flex flex-wrap items-center gap-3 text-xs text-gray-600 dark:text-gray-400">
        {typeof totalCount === "number" && (
          <span>
            Total:{" "}
            <span className="text-gray-900 dark:text-gray-100">
              {totalCount}
            </span>
          </span>
        )}
        {typeof filteredCount === "number" && filteredCount !== totalCount && (
          <span>
            Filtered:{" "}
            <span className="text-blue-600 dark:text-blue-400">
              {filteredCount}
            </span>
          </span>
        )}
        <span>
          Selected:{" "}
          <span className="text-green-600 dark:text-green-400">{count}</span>
        </span>
        {totalColumnCount > 0 && (
          <span>
            Columns:{" "}
            <span className="text-purple-600 dark:text-purple-400">
              {visibleColumnCount}/{totalColumnCount}
            </span>
          </span>
        )}

        {/* Custom Summary Content Slot */}
        {summaryContent}
      </div>

      {/* Children Slot */}
      {children}

      {/* Export Dropdown - Fixed position to avoid overflow clipping */}
      {showExportDropdown && exportDropdownPosition && (
        <div
          ref={exportDropdownPanelRef}
          className="fixed z-9999 w-56 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700"
          style={{
            top: exportDropdownPosition.top,
            left: exportDropdownPosition.left,
          }}
        >
          <div className="py-1">
            <div className="px-4 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
              Export All Data
            </div>
            <button
              onClick={() => {
                tableRef?.current?.exportToExcel?.(false);
                setShowExportDropdown(false);
              }}
              className="flex items-center gap-3 w-full px-4 py-2 text-xs text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              <FaFileExcel className="w-4 h-4 text-green-600" />
              Excel
            </button>
            <button
              onClick={() => {
                tableRef?.current?.exportToPDF?.(false);
                setShowExportDropdown(false);
              }}
              className="flex items-center gap-3 w-full px-4 py-2 text-xs text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              <FaFilePdf className="w-4 h-4 text-red-600" />
              PDF
            </button>
            <button
              onClick={() => {
                tableRef?.current?.exportToJSON?.(false);
                setShowExportDropdown(false);
              }}
              className="flex items-center gap-3 w-full px-4 py-2 text-xs text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              <FaFileCode className="w-4 h-4 text-blue-600" />
              JSON
            </button>

            {count > 0 && (
              <>
                <div className="my-1 border-t border-gray-200 dark:border-gray-700"></div>
                <div className="px-4 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                  Export Selected ({count})
                </div>
                <button
                  onClick={() => {
                    tableRef?.current?.exportToExcel?.(true);
                    setShowExportDropdown(false);
                  }}
                  className="flex items-center gap-3 w-full px-4 py-2 text-xs text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                >
                  <FaFileExcel className="w-4 h-4 text-green-600" />
                  Excel ({count} selected)
                </button>
                <button
                  onClick={() => {
                    tableRef?.current?.exportToPDF?.(true);
                    setShowExportDropdown(false);
                  }}
                  className="flex items-center gap-3 w-full px-4 py-2 text-xs text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                >
                  <FaFilePdf className="w-4 h-4 text-red-600" />
                  PDF ({count} selected)
                </button>
                <button
                  onClick={() => {
                    tableRef?.current?.exportToJSON?.(true);
                    setShowExportDropdown(false);
                  }}
                  className="flex items-center gap-3 w-full px-4 py-2 text-xs text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                >
                  <FaFileCode className="w-4 h-4 text-blue-600" />
                  JSON ({count} selected)
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* Column Setup Edit Dialog */}
      {editingSetupName &&
        (() => {
          const setup = columnSetupsApi.setups.find(
            (s) => s.name === editingSetupName,
          );
          const isCurrent = editingSetupName === "__current__";
          const dialogConfig = setup?.config ?? buildCurrentConfig();
          const dialogTitle = isCurrent ? "Current Columns" : editingSetupName;
          return (
            <ColumnSetupDialog
              open={true}
              title={dialogTitle}
              columnMetas={columnMetas}
              config={dialogConfig}
              existingSetupNames={columnSetupsApi.setups.map((s) => s.name)}
              namedSetups={columnSetupsApi.setups}
              initialSetupName={isCurrent ? null : editingSetupName}
              onSaveNamed={(name, cfg) => {
                const exists = columnSetupsApi.setups.some(
                  (s) => s.name === name,
                );
                if (exists) {
                  columnSetupsApi.updateSetup(name, cfg);
                } else {
                  columnSetupsApi.saveSetup(name, cfg);
                }
              }}
              onClose={() => setEditingSetupName(null)}
              onPreview={(config) => {
                tableRef?.current?.applyColumnLayout?.({
                  order: config.order,
                  visibility: config.visibility,
                  widths: config.widths,
                });
              }}
              onSave={(config) => {
                if (!isCurrent) {
                  columnSetupsApi.updateSetup(editingSetupName, config);
                }
                applyConfig(config);
                tableRef?.current?.applyColumnLayout?.({
                  order: config.order,
                  visibility: config.visibility,
                  widths: config.widths,
                });
                setEditingSetupName(null);
              }}
              columnSetupsApi={columnSetupsApi}
            />
          );
        })()}
    </div>
  );
};

export default ButtonToolbar;
