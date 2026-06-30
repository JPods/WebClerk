import React, {
  RefObject,
  useMemo,
  useRef,
  useState,
  useEffect,
  useCallback,
} from "react";
import { Link } from "react-router-dom";
import { TableColumn } from "react-data-table-component";
import { useDrag, useDrop, DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
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
  FaEye,
  FaEyeSlash,
} from "react-icons/fa";

export interface ColumnFilter {
  key: string;
  label: string;
  type?: string;
  options?: Array<{ value: string; label: string }>;
}

// Draggable column item for column manager
interface DraggableColumnItemProps {
  column: string;
  index: number;
  visible: boolean;
  isSelected: boolean;
  moveColumn: (dragIndex: number, hoverIndex: number) => void;
  toggleVisibility: (index: number) => void;
  onSelect: (index: number) => void;
}

const COLUMN_DRAG_TYPE = "COLUMN_ITEM";

function getSerializableColumnProps(col: TableColumn<any>): Record<string, any> {
  const result: Record<string, any> = {};
  for (const [key, val] of Object.entries(col as object)) {
    if (typeof val !== "function") {
      try {
        JSON.stringify(val);
        result[key] = val;
      } catch {
        // skip non-serializable values
      }
    }
  }
  return result;
}

const DraggableColumnItem: React.FC<DraggableColumnItemProps> = ({
  column,
  index,
  visible,
  isSelected,
  moveColumn,
  toggleVisibility,
  onSelect,
}) => {
  const ref = useRef<HTMLDivElement>(null);

  const [{ isDragging }, drag] = useDrag({
    type: COLUMN_DRAG_TYPE,
    item: { index },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  });

  const [, drop] = useDrop({
    accept: COLUMN_DRAG_TYPE,
    hover: (item: { index: number }, monitor) => {
      if (!ref.current) return;
      const dragIndex = item.index;
      const hoverIndex = index;
      if (dragIndex === hoverIndex) return;

      const hoverBoundingRect = ref.current.getBoundingClientRect();
      const hoverMiddleY =
        (hoverBoundingRect.bottom - hoverBoundingRect.top) / 2;
      const clientOffset = monitor.getClientOffset();
      if (!clientOffset) return;
      const hoverClientY = clientOffset.y - hoverBoundingRect.top;

      if (dragIndex < hoverIndex && hoverClientY < hoverMiddleY) return;
      if (dragIndex > hoverIndex && hoverClientY > hoverMiddleY) return;

      moveColumn(dragIndex, hoverIndex);
      item.index = hoverIndex;
    },
  });

  drag(drop(ref));

  return (
    <div
      ref={ref}
      onClick={() => onSelect(index)}
      className={`flex items-center justify-between p-2 rounded cursor-move ${
        isDragging ? "opacity-50" : ""
      } ${
        isSelected
          ? "ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-900/30"
          : visible
          ? "bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600"
          : "bg-gray-100 dark:bg-gray-800 opacity-60 hover:bg-gray-200 dark:hover:bg-gray-700"
      }`}
    >
      <div className="flex items-center gap-2">
        <FaGripVertical className="w-3 h-3 text-gray-400" />
        <span
          className={`text-xs ${
            visible
              ? "text-gray-900 dark:text-gray-100"
              : "text-gray-500 dark:text-gray-400 line-through"
          }`}
        >
          {column}
        </span>
      </div>
      <button
        onClick={(e) => {
          e.stopPropagation();
          toggleVisibility(index);
        }}
        className={`p-1 rounded ${
          visible
            ? "text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20"
            : "text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
        }`}
        title={visible ? "Hide column" : "Show column"}
      >
        {visible ? (
          <FaEye className="w-3 h-3" />
        ) : (
          <FaEyeSlash className="w-3 h-3" />
        )}
      </button>
    </div>
  );
};

interface BreadcrumbProps<T = any> {
  pageTitle: string;
  title?: string;
  modelKey?: string;
  searchTerm?: string;
  onSearchTermChange?: (value: string) => void;
  handleAddInline?: () => void;
  handleBulkDelete?: () => void;
  tableRef?: RefObject<any>;
  columnBtnRef?: RefObject<HTMLButtonElement>;
  importInputRef?: RefObject<HTMLInputElement>;
  selectedRows?: any[];
  selectedCount?: number;
  totalCount?: number;
  filteredCount?: number;
  onPrint?: () => void;
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
}

const PageBreadcrumb = <T extends Record<string, any> = any>({
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
}: BreadcrumbProps<T>) => {
  // exportFileName available for future use if needed
  void _exportFileName;
  const count = selectedCount ?? selectedRows?.length ?? 0;
  const canExport = Boolean(tableRef?.current?.exportToExcel);
  const canSelect = Boolean(tableRef?.current?.selectAll);

  const columnManagerRef = useRef<HTMLDivElement>(null);
  const columnManagerDropdownRef = useRef<HTMLDivElement>(null);
  const exportDropdownRef = useRef<HTMLDivElement>(null);
  const localImportInputRef = useRef<HTMLInputElement>(null);
  const localColumnBtnRef = useRef<HTMLButtonElement>(null);

  const [showExportDropdown, setShowExportDropdown] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [showColumnManager, setShowColumnManager] = useState(false);
  const [columnManagerPosition, setColumnManagerPosition] = useState<{
    top: number;
    left: number;
  } | null>(null);
  const [exportDropdownPosition, setExportDropdownPosition] = useState<{
    top: number;
    left: number;
  } | null>(null);

  const [selectedColIndex, setSelectedColIndex] = useState<number | null>(null);
  const [editJson, setEditJson] = useState<string>("");
  const [jsonError, setJsonError] = useState<string>("");

  // Internal column visibility state (used when not controlled externally)
  const [internalColumnVisibility, setInternalColumnVisibility] = useState<
    boolean[]
  >(() => columns.map(() => true));
  const [internalColumns, setInternalColumns] =
    useState<TableColumn<T>[]>(columns);
  const initialColumnsRef = useRef<TableColumn<T>[]>(columns);

  // Use external or internal visibility
  const columnVisibility = externalColumnVisibility ?? internalColumnVisibility;

  // Use external or internal columns
  const currentColumns = onColumnsChange ? columns : internalColumns;

  const effectiveShowFilters = filtersOpen ?? showFilters;
  const setEffectiveShowFilters = onFiltersOpenChange ?? setShowFilters;
  const effectiveImportInputRef = importInputRef ?? localImportInputRef;
  const effectiveColumnBtnRef = columnBtnRef ?? localColumnBtnRef;

  // Stable key for persisted layouts and column reconciliation.
  const getColumnPersistKey = useCallback(
    (col: TableColumn<T>, index: number): string => {
      if (col.id != null) return `id:${String(col.id)}`;
      if (typeof col.name === "string") {
        return `name:${col.name.trim().toLowerCase()}`;
      }
      if (typeof col.selector === "string") {
        return `selector:${col.selector.trim().toLowerCase()}`;
      }
      if (typeof col.sortField === "string") {
        return `sortField:${col.sortField.trim().toLowerCase()}`;
      }
      return `index:${index}`;
    },
    [],
  );

  const columnsSignature = useMemo(
    () => columns.map((col, i) => getColumnPersistKey(col, i)).join("|"),
    [columns, getColumnPersistKey],
  );

  const isColumnsControlled = Boolean(onColumnsChange);

  // Keep an immutable reset baseline from the first non-empty columns set.
  useEffect(() => {
    if (initialColumnsRef.current.length === 0 && columns.length > 0) {
      initialColumnsRef.current = columns;
    }
  }, [columns]);

  // Sync internal state for uncontrolled mode without clobbering user reordering.
  useEffect(() => {
    if (isColumnsControlled || columns.length === 0) return;

    setInternalColumns((prevColumns) => {
      if (prevColumns.length === 0) {
        if (!externalColumnVisibility) {
          setInternalColumnVisibility(columns.map(() => true));
        }
        return columns;
      }

      const prevByKey = new Map<string, TableColumn<T>>();
      prevColumns.forEach((col, index) => {
        prevByKey.set(getColumnPersistKey(col, index), col);
      });

      const incomingKeys = columns.map((col, index) =>
        getColumnPersistKey(col, index),
      );
      const incomingKeySet = new Set(incomingKeys);

      const mergedColumns: TableColumn<T>[] = [];

      // Preserve user order for columns that still exist.
      prevColumns.forEach((col, index) => {
        const key = getColumnPersistKey(col, index);
        if (incomingKeySet.has(key)) {
          mergedColumns.push(prevByKey.get(key) ?? col);
        }
      });

      // Append new columns introduced from props.
      columns.forEach((col, index) => {
        const key = getColumnPersistKey(col, index);
        if (!prevColumns.some((pCol, pIndex) => getColumnPersistKey(pCol, pIndex) === key)) {
          mergedColumns.push(col);
        }
      });

      if (!externalColumnVisibility) {
        setInternalColumnVisibility((prevVisibility) => {
          const prevVisibilityByKey = new Map<string, boolean>();
          prevColumns.forEach((col, index) => {
            prevVisibilityByKey.set(
              getColumnPersistKey(col, index),
              prevVisibility[index] ?? true,
            );
          });

          return mergedColumns.map((col, index) => {
            const key = getColumnPersistKey(col, index);
            return prevVisibilityByKey.get(key) ?? true;
          });
        });
      }

      return mergedColumns;
    });
  }, [
    columns,
    columnsSignature,
    externalColumnVisibility,
    getColumnPersistKey,
    isColumnsControlled,
  ]);

  // Load persisted column layout (supports legacy array and keyed layouts).
  useEffect(() => {
    if (!storageKey || columns.length === 0) return;

    try {
      const saved = localStorage.getItem(
        `PageBreadcrumb:${storageKey}:columns`,
      );
      if (saved) {
        const parsed = JSON.parse(saved) as {
          order?: string[];
          visibility?: boolean[] | Record<string, boolean>;
        };

        let nextColumns = [...columns];
        let nextVisibility: boolean[] | null = null;

        const keyedVisibility =
          parsed.visibility && !Array.isArray(parsed.visibility)
            ? parsed.visibility
            : null;
        const hasKeyedOrder = Array.isArray(parsed.order) && parsed.order.length > 0;

        if (hasKeyedOrder || keyedVisibility) {
          const byKey = new Map<string, TableColumn<T>>();
          columns.forEach((col, index) => {
            byKey.set(getColumnPersistKey(col, index), col);
          });

          const reordered: TableColumn<T>[] = [];
          const usedKeys = new Set<string>();

          if (hasKeyedOrder) {
            parsed.order?.forEach((key) => {
              const col = byKey.get(key);
              if (col) {
                reordered.push(col);
                usedKeys.add(key);
              }
            });
          }

          columns.forEach((col, index) => {
            const key = getColumnPersistKey(col, index);
            if (!usedKeys.has(key)) {
              reordered.push(col);
            }
          });

          nextColumns = reordered;
          nextVisibility = nextColumns.map((col, index) => {
            const key = getColumnPersistKey(col, index);
            return keyedVisibility?.[key] !== false;
          });
        } else if (
          Array.isArray(parsed.visibility) &&
          parsed.visibility.length === columns.length
        ) {
          nextVisibility = parsed.visibility;
        }

        if (nextColumns.length > 0) {
          if (onColumnsChange) {
            onColumnsChange(nextColumns);
          } else {
            setInternalColumns(nextColumns);
          }
        }

        if (nextVisibility) {
          if (onColumnVisibilityChange) {
            onColumnVisibilityChange(nextVisibility);
          } else {
            setInternalColumnVisibility(nextVisibility);
          }
        }
      }
    } catch {
      // Ignore errors
    }
  }, [
    columns,
    columnsSignature,
    getColumnPersistKey,
    onColumnsChange,
    onColumnVisibilityChange,
    storageKey,
  ]);

  // Save column layout
  const saveColumnLayout = useCallback(
    (layoutColumns: TableColumn<T>[], visibility: boolean[]) => {
      if (!storageKey) return;

      const order = layoutColumns.map((col, index) =>
        getColumnPersistKey(col, index),
      );
      const keyedVisibility = order.reduce<Record<string, boolean>>(
        (acc, key, index) => {
          acc[key] = visibility[index] ?? true;
          return acc;
        },
        {},
      );

      try {
        localStorage.setItem(
          `PageBreadcrumb:${storageKey}:columns`,
          JSON.stringify({ order, visibility: keyedVisibility }),
        );
      } catch {
        // Ignore errors
      }
    },
    [getColumnPersistKey, storageKey],
  );

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        exportDropdownRef.current &&
        !exportDropdownRef.current.contains(event.target as Node)
      ) {
        setShowExportDropdown(false);
      }
      if (
        columnManagerRef.current &&
        !columnManagerRef.current.contains(event.target as Node) &&
        columnManagerDropdownRef.current &&
        !columnManagerDropdownRef.current.contains(event.target as Node)
      ) {
        setShowColumnManager(false);
      }
    };

    if (showExportDropdown || showColumnManager) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showExportDropdown, showColumnManager]);

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
  };

  const activeFilterCount = Object.values(filterValues).filter(Boolean).length;

  // Column management functions
  const moveColumn = useCallback(
    (dragIndex: number, hoverIndex: number) => {
      // Update columns
      const newColumns = [...currentColumns];
      const [draggedColumn] = newColumns.splice(dragIndex, 1);
      newColumns.splice(hoverIndex, 0, draggedColumn);

      if (onColumnsChange) {
        onColumnsChange(newColumns);
      } else {
        setInternalColumns(newColumns);
      }

      // Update visibility
      const newVisibility = [...columnVisibility];
      const [draggedVisibility] = newVisibility.splice(dragIndex, 1);
      newVisibility.splice(hoverIndex, 0, draggedVisibility);

      if (onColumnVisibilityChange) {
        onColumnVisibilityChange(newVisibility);
      } else {
        setInternalColumnVisibility(newVisibility);
      }
      saveColumnLayout(newColumns, newVisibility);
    },
    [
      currentColumns,
      columnVisibility,
      onColumnsChange,
      onColumnVisibilityChange,
      saveColumnLayout,
    ],
  );

  const toggleColumnVisibility = useCallback(
    (index: number) => {
      const newVisibility = [...columnVisibility];
      newVisibility[index] = !newVisibility[index];

      if (onColumnVisibilityChange) {
        onColumnVisibilityChange(newVisibility);
      } else {
        setInternalColumnVisibility(newVisibility);
      }
      saveColumnLayout(currentColumns, newVisibility);
    },
    [columnVisibility, currentColumns, onColumnVisibilityChange, saveColumnLayout],
  );

  const showAllColumns = useCallback(() => {
    const newVisibility = currentColumns.map(() => true);
    if (onColumnVisibilityChange) {
      onColumnVisibilityChange(newVisibility);
    } else {
      setInternalColumnVisibility(newVisibility);
    }
    saveColumnLayout(currentColumns, newVisibility);
  }, [currentColumns, onColumnVisibilityChange, saveColumnLayout]);

  const hideAllColumns = useCallback(() => {
    const newVisibility = currentColumns.map(() => false);
    if (onColumnVisibilityChange) {
      onColumnVisibilityChange(newVisibility);
    } else {
      setInternalColumnVisibility(newVisibility);
    }
    saveColumnLayout(currentColumns, newVisibility);
  }, [currentColumns, onColumnVisibilityChange, saveColumnLayout]);

  const resetColumns = useCallback(() => {
    const baselineColumns =
      initialColumnsRef.current.length > 0 ? initialColumnsRef.current : columns;

    if (onColumnsChange) {
      onColumnsChange(baselineColumns);
    } else {
      setInternalColumns(baselineColumns);
    }

    const newVisibility = baselineColumns.map(() => true);
    if (onColumnVisibilityChange) {
      onColumnVisibilityChange(newVisibility);
    } else {
      setInternalColumnVisibility(newVisibility);
    }

    if (storageKey) {
      try {
        localStorage.removeItem(`PageBreadcrumb:${storageKey}:columns`);
      } catch {
        // Ignore
      }
    }
  }, [columns, onColumnsChange, onColumnVisibilityChange, storageKey]);

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

          {/* Print */}
          <button
            onClick={onPrint}
            disabled={!onPrint}
            title="Print"
            className="w-9 h-9 flex items-center justify-center rounded-md bg-yellow-500 text-white hover:bg-yellow-600 disabled:opacity-50"
          >
            <FaPrint className="w-4 h-4" />
          </button>

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
              onClick={() => {
                if (!showColumnManager && effectiveColumnBtnRef.current) {
                  const rect =
                    effectiveColumnBtnRef.current.getBoundingClientRect();
                  const panelWidth = 320;
                  let left = rect.left;
                  // Keep panel within viewport
                  if (left + panelWidth > window.innerWidth - 16) {
                    left = window.innerWidth - panelWidth - 16;
                  }
                  setColumnManagerPosition({
                    top: rect.bottom + 8,
                    left: Math.max(16, left),
                  });
                }
                setShowColumnManager(!showColumnManager);
              }}
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
            className="w-9 h-9 flex items-center justify-center rounded-md bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
          >
            <FaTrash className="w-4 h-4" />
          </button>
          {/* </div> */}
        </div>
        <h2 className="text-xl font-semibold text-gray-800 dark:text-white/90">
          {pageTitle}
        </h2>
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
      </div>

      {/* Export Dropdown - Fixed position to avoid overflow clipping */}
      {showExportDropdown && exportDropdownPosition && (
        <div
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

      {/* Column Manager Dropdown - Fixed position to avoid overflow clipping */}
      {showColumnManager &&
        currentColumns.length > 0 &&
        columnManagerPosition && (
          <div
            ref={columnManagerDropdownRef}
            className="fixed z-[9999] w-80 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700"
            style={{
              top: columnManagerPosition.top,
              left: columnManagerPosition.left,
            }}
          >
            <div className="p-4">
              {/* Header */}
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                  Manage Columns
                </h3>
                <button
                  onClick={resetColumns}
                  className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 font-medium"
                >
                  Reset
                </button>
              </div>

              {/* Quick Actions */}
              <div className="flex items-center gap-2 mb-3">
                <button
                  onClick={showAllColumns}
                  className="flex-1 px-3 py-1.5 text-xs font-medium text-green-700 bg-green-50 rounded hover:bg-green-100 dark:bg-green-900/20 dark:text-green-400"
                >
                  Show All
                </button>
                <button
                  onClick={hideAllColumns}
                  className="flex-1 px-3 py-1.5 text-xs font-medium text-red-700 bg-red-50 rounded hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400"
                >
                  Hide All
                </button>
              </div>

              {/* Instructions */}
              <div className="mb-3 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <p className="text-xs text-blue-700 dark:text-blue-300">
                  <strong>👁</strong> Click eye to show/hide &nbsp;
                  <strong>↕</strong> Drag to reorder
                </p>
              </div>

              {/* Column List */}
              <DndProvider backend={HTML5Backend}>
                <div className="space-y-1 max-h-64 overflow-y-auto">
                  {currentColumns.map((col, index) => (
                    <DraggableColumnItem
                      key={`col-${index}-${String(
                        col.name || col.id || index,
                      )}`}
                      column={String(
                        col.name || col.id || `Column ${index + 1}`,
                      )}
                      index={index}
                      visible={columnVisibility[index] ?? true}
                      moveColumn={moveColumn}
                      toggleVisibility={toggleColumnVisibility}
                    />
                  ))}
                </div>
              </DndProvider>

              {/* Footer */}
              <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Visible:{" "}
                  <span className="font-medium text-blue-600">
                    {visibleColumnCount}
                  </span>{" "}
                  / {totalColumnCount}
                </p>
                <button
                  onClick={() => setShowColumnManager(false)}
                  className="px-3 py-1 text-xs font-medium text-gray-700 bg-gray-100 rounded hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
    </div>
  );
};

export default PageBreadcrumb;
