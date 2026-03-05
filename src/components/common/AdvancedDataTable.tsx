import React, {
  useState,
  useMemo,
  useCallback,
  useRef,
  useEffect,
} from "react";
import DataTable, { TableColumn } from "react-data-table-component";
import { useDrag, useDrop } from "react-dnd";
import { useTheme } from "@/context/ThemeContext";
import { FaGripVertical } from "react-icons/fa";
import * as XLSX from "xlsx";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

/**
 * Parse comma-separated search terms into an array of trimmed lowercase terms.
 * Supports both "," and ", " as separators.
 * Exported for use in List components that need to perform database searches.
 */
export const parseSearchTerms = (input: string): string[] => {
  if (!input || !input.trim()) return [];
  return input
    .split(/,\s*/)
    .map((t) => t.trim().toLowerCase())
    .filter((t) => t.length > 0);
};

export type ColumnFilter = {
  key: string; // unique key for the filter (used as object key)
  label: string; // label to display in the UI
  type?: string; // e.g. "text", "select", etc.
  options?: Array<{ value: string; label: string }>; // for select filters
  // Optionally keep name/field for backward compatibility
  name?: string;
  field?: string;
};

export interface AdvancedDataTableProps<T> {
  data: T[];
  columns: TableColumn<T>[];
  title?: string;
  loading?: boolean;
  filters?: ColumnFilter[];
  hideHeader?: boolean;
  externalSearchTerm?: string;
  onExternalSearchTermChange?: (s: string) => void;
  filtersOpen?: boolean;
  onFiltersOpenChange?: (open: boolean) => void;
  onAdd?: () => void;
  onEditSelected?: (row: T) => void;
  onDeleteSelected?: (rows: T[]) => void;
  onImportFile?: (f: File) => void;
  importAccept?: string;
  onPrint?: () => void;
  storageKey?: string;
  enableExport?: boolean;
  enableSelection?: boolean;
  onSelectionChange?: (rows: T[]) => void;
  onVisibleRowsChange?: (rows: T[]) => void;
  customActions?: React.ReactNode;
  exportFileName?: string;
  onRowClicked?: (row: T) => void;
  onRowActivate?: (row: T) => void;
  onRowDoubleClicked?: (row: T) => void;
  rowKeyField?: string;
  selectionMode?: "rowClick" | "checkbox";
  enableSelectedOnlyFilter?: boolean;
  rowClickMode?: "onlyIdAndActions" | "anywhere";
  rowClickAllowedColumnNames?: string[];
  rowClickAllowedColumnIds?: Array<string | number>;
  searchPlaceholder?: string;
  noDataMessage?: string;
  /** Enable toggle between searching in current selection vs querying database */
  enableDatabaseSearch?: boolean;
  /** Current search mode: true = query database, false = search in selection */
  searchDatabase?: boolean;
  /** Callback when search mode changes */
  onSearchModeChange?: (searchDatabase: boolean) => void;
  /** Callback to perform database search with parsed terms. Parent component handles updating data. */
  onDatabaseSearch?: (terms: string[]) => Promise<void> | void;
}

// Draggable Column Header Component
interface DraggableColumnHeaderProps {
  column: string;
  index: number;
  visible: boolean;
  moveColumn: (dragIndex: number, hoverIndex: number) => void;
  toggleVisibility: (index: number) => void;
}

const DraggableColumnHeader: React.FC<DraggableColumnHeaderProps> = ({
  column,
  index,
  visible,
  moveColumn,
  toggleVisibility,
}) => {
  const ref = useRef<HTMLDivElement>(null);

  const [{ isDragging }, drag] = useDrag({
    type: "column",
    item: { index },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  });

  const [, drop] = useDrop({
    accept: "column",
    hover: (item: { index: number }) => {
      if (!ref.current) return;
      const dragIndex = item.index;
      const hoverIndex = index;
      if (dragIndex === hoverIndex) return;
      moveColumn(dragIndex, hoverIndex);
      item.index = hoverIndex;
    },
  });

  drag(drop(ref));

  return (
    <div
      ref={ref}
      className="flex items-center gap-2"
      style={{
        opacity: isDragging ? 0.5 : 1,
      }}
    >
      <input
        type="checkbox"
        checked={visible}
        onChange={() => toggleVisibility(index)}
        className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 cursor-pointer"
        onClick={(e) => e.stopPropagation()}
      />
      <div
        className="flex items-center gap-1 flex-1"
        style={{ cursor: "move" }}
      >
        <FaGripVertical className="text-gray-400" size={12} />
        <span className={`${!visible ? "text-gray-400 line-through" : ""}`}>
          {column}
        </span>
      </div>
    </div>
  );
};

export type AdvancedDataTableHandle<T> = {
  exportToExcel: (selectedOnly?: boolean) => void;
  exportToPDF: (selectedOnly?: boolean) => void;
  exportToJSON: (selectedOnly?: boolean) => void;
  getSelectedRows: () => T[];
  clearSelection: () => void;
  selectAll: () => void;
  openColumnManager: (anchor?: HTMLElement | DOMRect | null) => void;
};

const AdvancedDataTable = React.forwardRef(function AdvancedDataTable<
  T extends Record<string, any>,
>(
  {
    data,
    columns: initialColumns,
    title = "Data Table",
    loading = false,
    externalSearchTerm,
    onExternalSearchTermChange,
    filtersOpen,
    onFiltersOpenChange,
    onImportFile,
    storageKey,
    enableSelection = false,
    onSelectionChange,
    onVisibleRowsChange,
    exportFileName = "export",
    onRowClicked,
    onRowActivate,
    onRowDoubleClicked,
    rowKeyField = "id",
    selectionMode = "rowClick",
    enableSelectedOnlyFilter = true,
    rowClickMode = "onlyIdAndActions",
    rowClickAllowedColumnNames,
    rowClickAllowedColumnIds,
    noDataMessage = "No data available",
    searchDatabase: searchDatabaseProp,
    onSearchModeChange,
    onDatabaseSearch,
  }: AdvancedDataTableProps<T>,
  ref: React.Ref<AdvancedDataTableHandle<T>>,
) {
  type RowWithKey = T & { __wcRowKey: string };
  const internalRowKeyField = "__wcRowKey" as const;

  const { theme } = useTheme();
  const [searchTerm, setSearchTerm] = useState("");
  const [searchDatabaseInternal, setSearchDatabaseInternal] = useState(false);

  // Controlled or uncontrolled search mode
  const searchDatabase = searchDatabaseProp ?? searchDatabaseInternal;
  const [selectedRows, setSelectedRows] = useState<T[]>([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [selectionAnchorKey, setSelectionAnchorKey] = useState<string | null>(
    null,
  );
  const [showSelectedOnly, setShowSelectedOnly] = useState(false);
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [showFilters, setShowFiltersState] = useState(false);
  const [showExportDropdown, setShowExportDropdown] = useState(false);
  const exportDropdownRef = useRef<HTMLDivElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);
  const [columns, setColumns] = useState<TableColumn<T>[]>(initialColumns);
  const [columnVisibility, setColumnVisibility] = useState<boolean[]>(
    initialColumns.map(() => true),
  );
  const [showColumnManager, setShowColumnManager] = useState(false);
  const [columnManagerAnchorRect, setColumnManagerAnchorRect] =
    useState<DOMRect | null>(null);
  const columnManagerRef = useRef<HTMLDivElement>(null);

  const didHydrateLayoutRef = useRef(false);

  const effectiveSearchTerm = externalSearchTerm ?? searchTerm;
  const setEffectiveSearchTerm = onExternalSearchTermChange ?? setSearchTerm;

  const getColumnPersistKey = useCallback(
    (col: TableColumn<T>, index: number) => {
      if (col.id != null) return `id:${String(col.id)}`;
      if (typeof col.name === "string")
        return `name:${col.name.trim().toLowerCase()}`;
      if (typeof col.selector === "string")
        return `selector:${col.selector.trim().toLowerCase()}`;
      if (typeof col.sortField === "string")
        return `sortField:${col.sortField.trim().toLowerCase()}`;
      return `index:${index}`;
    },
    [],
  );

  const columnStorageKey = useMemo(() => {
    if (!storageKey) return null;
    return `AdvancedDataTable:v1:${storageKey}:columns`;
  }, [storageKey]);

  const readPersistedLayout = useCallback(() => {
    if (!columnStorageKey) return null;
    try {
      const raw = localStorage.getItem(columnStorageKey);
      if (!raw) return null;
      return JSON.parse(raw) as {
        v: 1;
        order?: string[];
        visibility?: Record<string, boolean>;
      };
    } catch {
      return null;
    }
  }, [columnStorageKey]);

  const writePersistedLayout = useCallback(
    (nextColumns: TableColumn<T>[], nextVisibility: boolean[]) => {
      if (!columnStorageKey) return;
      try {
        const keys = nextColumns.map((c, i) => getColumnPersistKey(c, i));
        const visibility: Record<string, boolean> = {};
        keys.forEach((k, i) => {
          visibility[k] = nextVisibility[i] ?? true;
        });
        localStorage.setItem(
          columnStorageKey,
          JSON.stringify({ v: 1 as const, order: keys, visibility }),
        );
      } catch {
        // ignore storage errors
      }
    },
    [columnStorageKey, getColumnPersistKey],
  );

  // Update columns when initialColumns change (hydrate persisted order/visibility per storageKey)
  useEffect(() => {
    const persisted = readPersistedLayout();
    const base = initialColumns.map((col, index) => ({
      col,
      key: getColumnPersistKey(col, index),
    }));

    if (!persisted?.order?.length) {
      setColumns(initialColumns);
      setColumnVisibility(initialColumns.map(() => true));
      didHydrateLayoutRef.current = true;
      return;
    }

    const byKey = new Map(base.map((x) => [x.key, x.col] as const));
    const used = new Set<string>();
    const ordered: TableColumn<T>[] = [];

    for (const key of persisted.order) {
      const col = byKey.get(key);
      if (col) {
        ordered.push(col);
        used.add(key);
      }
    }

    for (const item of base) {
      if (!used.has(item.key)) ordered.push(item.col);
    }

    const visibilityArr = ordered.map((col, i) => {
      const key = getColumnPersistKey(col, i);
      return persisted.visibility?.[key] ?? true;
    });

    setColumns(ordered);
    setColumnVisibility(visibilityArr);
    didHydrateLayoutRef.current = true;
  }, [initialColumns, readPersistedLayout, getColumnPersistKey]);

  // Persist layout whenever user changes it
  useEffect(() => {
    if (!columnStorageKey) return;
    if (!didHydrateLayoutRef.current) return;
    writePersistedLayout(columns, columnVisibility);
  }, [columns, columnVisibility, columnStorageKey, writePersistedLayout]);

  // Handle click outside to close export dropdown and column manager
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
        !columnManagerRef.current.contains(event.target as Node)
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

  // Get visible columns
  const visibleColumns = useMemo(() => {
    return columns.filter((_, index) => columnVisibility[index]);
  }, [columns, columnVisibility]);

  const onActivate = onRowActivate ?? onRowClicked;

  const normalize = useCallback(
    (value: string) => value.trim().toLowerCase(),
    [],
  );

  const getRowKey = useCallback(
    (row: T, rowIndex?: number) => {
      const internalKey = (row as any)?.[internalRowKeyField];
      if (internalKey != null) return String(internalKey);

      const fromKeyField = rowKeyField
        ? (row as any)?.[rowKeyField]
        : undefined;
      const fromId = (row as any)?.id;
      const fromAltId = (row as any)?._id ?? (row as any)?.uuid;
      const value = fromKeyField ?? fromId ?? fromAltId ?? rowIndex;
      return String(value);
    },
    [rowKeyField],
  );

  const selectedRowKeySet = useMemo(
    () => new Set(selectedRowKeys),
    [selectedRowKeys],
  );

  const rowByKey = useMemo(() => {
    const map = new Map<string, T>();
    const safeData = Array.isArray(data) ? data : [];
    safeData.forEach((row, index) => {
      map.set(getRowKey(row, index), row);
    });
    return map;
  }, [data, getRowKey]);

  // Keep selectedRows in sync if upstream data objects change.
  useEffect(() => {
    if (selectedRowKeys.length === 0) {
      if (selectedRows.length !== 0) setSelectedRows([]);
      return;
    }
    const nextSelected = selectedRowKeys
      .map((key) => rowByKey.get(key))
      .filter(Boolean) as T[];
    setSelectedRows(nextSelected);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rowByKey]);

  useEffect(() => {
    if (showSelectedOnly && selectedRowKeys.length === 0) {
      setShowSelectedOnly(false);
    }
  }, [showSelectedOnly, selectedRowKeys.length]);

  const dataTableColumns = useMemo(() => {
    const allowedNameSet = new Set(
      (rowClickAllowedColumnNames ?? []).map(normalize),
    );
    const allowedIdSet = new Set(
      (rowClickAllowedColumnIds ?? []).map((v) => String(v)),
    );

    const isActivationColumn = (col: TableColumn<T>) => {
      if (allowedIdSet.size > 0 && col.id != null) {
        if (allowedIdSet.has(String(col.id))) return true;
      }
      if (allowedNameSet.size > 0 && typeof col.name === "string") {
        if (allowedNameSet.has(normalize(col.name))) return true;
      }
      if (allowedIdSet.size === 0 && allowedNameSet.size === 0) {
        if (typeof col.name === "string") {
          const name = normalize(col.name);
          if (name === "id" || name.endsWith(" id") || name.startsWith("id ")) {
            return true;
          }
          if (name.includes("action")) return true;
        }
        if (typeof col.id === "string") {
          const id = normalize(col.id);
          if (id === "id" || id.includes("action")) return true;
        }
      }
      return false;
    };

    const isIdColumn = (col: TableColumn<T>) => {
      if (typeof col.id === "string" && normalize(col.id) === "id") return true;
      if (typeof col.name === "string" && normalize(col.name) === "id")
        return true;
      return false;
    };

    const mapped = visibleColumns.map((col) => {
      const activationCol =
        rowClickMode === "onlyIdAndActions" &&
        !!onActivate &&
        isActivationColumn(col);
      const ignoreForSelection =
        enableSelection && selectionMode === "rowClick" && activationCol;

      // Make the ID column clickable for activate (edit/view) and prevent it from toggling selection.
      if (activationCol && isIdColumn(col) && onActivate) {
        const originalCell = col.cell;
        const originalFormat = col.format;
        const originalSelector = col.selector;

        return {
          ...col,
          ignoreRowClick: true,
          cell: (
            row: T,
            rowIndex: number,
            column: TableColumn<T>,
            id: string | number,
          ) => {
            const content = originalCell
              ? originalCell(row, rowIndex, column, id)
              : originalFormat
              ? originalFormat(row, rowIndex)
              : typeof originalSelector === "function"
              ? (originalSelector(row, rowIndex) as any)
              : originalSelector
              ? (row as any)[originalSelector as any]
              : (row as any)?.[rowKeyField];

            return (
              <span
                className="text-blue-600 hover:text-blue-700 hover:underline font-medium cursor-pointer"
                onClick={(e) => {
                  e.stopPropagation();
                  onActivate(row);
                }}
              >
                {content as any}
              </span>
            );
          },
        };
      }

      if (ignoreForSelection) {
        return {
          ...col,
          ignoreRowClick: true,
        };
      }

      return col;
    });

    // If the sum of column widths is less than the available table width,
    // react-data-table-component can leave a trailing blank area to the right.
    // Make one "filler" column expand to consume remaining space.
    // Prefer a non-actions column so action buttons remain a consistent size.
    if (mapped.length > 0) {
      const isActionLike = (c: TableColumn<T>) => {
        const name = typeof c.name === "string" ? normalize(c.name) : "";
        const id = typeof c.id === "string" ? normalize(c.id) : "";
        return (
          name === "actions" ||
          name === "action" ||
          id === "actions" ||
          id === "action"
        );
      };

      let fillerIndex = -1;
      for (let i = mapped.length - 1; i >= 0; i--) {
        if (!isActionLike(mapped[i])) {
          fillerIndex = i;
          break;
        }
      }
      if (fillerIndex === -1) fillerIndex = mapped.length - 1;

      const filler = mapped[fillerIndex];
      mapped[fillerIndex] = {
        ...filler,
        // Remove any explicit width so flex-grow can actually fill.
        width: undefined,
        // Ensure the column can expand.
        grow:
          typeof (filler as any).grow === "number" ? (filler as any).grow : 1,
      } as TableColumn<T>;
    }

    return mapped;
  }, [
    visibleColumns,
    rowClickMode,
    onActivate,
    rowClickAllowedColumnNames,
    rowClickAllowedColumnIds,
    enableSelection,
    selectionMode,
    normalize,
    rowKeyField,
  ]);

  /**
   * Parse comma-separated search terms into an array of trimmed lowercase terms.
   * Supports both "," and ", " as separators.
   */
  const parseSearchTerms = useCallback((input: string): string[] => {
    if (!input || !input.trim()) return [];
    return input
      .split(/,\s*/)
      .map((t) => t.trim().toLowerCase())
      .filter((t) => t.length > 0);
  }, []);

  /**
   * Check if a row matches ALL search terms (AND logic).
   * Searches all scalar fields and refs.keywords.
   */
  const rowMatchesAllTerms = useCallback(
    (row: Record<string, any>, terms: string[]): boolean => {
      if (!terms.length) return true;

      // Collect all searchable text from the row
      const searchableValues: string[] = [];

      // Add all scalar field values
      Object.entries(row).forEach(([key, value]) => {
        if (value === null || value === undefined) return;
        if (
          typeof value === "string" ||
          typeof value === "number" ||
          typeof value === "boolean"
        ) {
          searchableValues.push(String(value).toLowerCase());
        }
      });

      // Add refs.keywords if present
      const refs = row.refs;
      if (refs && typeof refs === "object") {
        const keywords = refs.keywords;
        if (typeof keywords === "string") {
          searchableValues.push(keywords.toLowerCase());
        } else if (Array.isArray(keywords)) {
          keywords.forEach((kw) => {
            if (typeof kw === "string") {
              searchableValues.push(kw.toLowerCase());
            }
          });
        }
      }

      // Check that ALL terms match somewhere in the searchable values
      const searchableText = searchableValues.join(" ");
      return terms.every((term) => searchableText.includes(term));
    },
    [],
  );

  // Filter and search logic
  const filteredData = useMemo(() => {
    // If database search mode is active and we have a search term,
    // filtering is handled externally via onDatabaseSearch callback
    if (searchDatabase && effectiveSearchTerm && onDatabaseSearch) {
      // Return all data - parent component handles database query results
      return [...(Array.isArray(data) ? data : [])];
    }

    let result = [...(Array.isArray(data) ? data : [])];

    // Apply search with AND logic for comma-separated terms
    if (effectiveSearchTerm) {
      const terms = parseSearchTerms(effectiveSearchTerm);
      if (terms.length > 0) {
        result = result.filter((row) => rowMatchesAllTerms(row, terms));
      }
    }

    // Apply column filters
    Object.entries(filterValues).forEach(([key, value]) => {
      if (value) {
        result = result.filter((row) => {
          const rowValue = String(row[key] || "").toLowerCase();
          return rowValue.includes(value.toLowerCase());
        });
      }
    });

    return result;
  }, [
    data,
    effectiveSearchTerm,
    filterValues,
    searchDatabase,
    onDatabaseSearch,
    parseSearchTerms,
    rowMatchesAllTerms,
  ]);

  // Trigger database search callback when in database mode
  useEffect(() => {
    if (searchDatabase && onDatabaseSearch && effectiveSearchTerm) {
      const terms = parseSearchTerms(effectiveSearchTerm);
      if (terms.length > 0) {
        onDatabaseSearch(terms);
      }
    }
  }, [searchDatabase, onDatabaseSearch, effectiveSearchTerm, parseSearchTerms]);

  useEffect(() => {
    if (onVisibleRowsChange) {
      onVisibleRowsChange(filteredData);
    }
  }, [filteredData, onVisibleRowsChange]);

  const tableData = useMemo(() => {
    if (!enableSelection || !enableSelectedOnlyFilter || !showSelectedOnly) {
      return filteredData;
    }

    return filteredData.filter((row, index) =>
      selectedRowKeySet.has(getRowKey(row, index)),
    );
  }, [
    enableSelection,
    enableSelectedOnlyFilter,
    showSelectedOnly,
    filteredData,
    selectedRowKeySet,
    getRowKey,
  ]);

  const tableRows: RowWithKey[] = useMemo(() => {
    return tableData.map((row, index) => ({
      ...(row as any),
      [internalRowKeyField]: getRowKey(row, index),
    })) as RowWithKey[];
  }, [tableData, getRowKey]);

  // Handle selection
  const handleSelectedRowsChange = useCallback(
    (state: { selectedRows: T[] }) => {
      setSelectedRows(state.selectedRows);
      onSelectionChange?.(state.selectedRows);
    },
    [onSelectionChange],
  );

  const clearSelection = useCallback(() => {
    setSelectedRowKeys([]);
    setSelectedRows([]);
    setSelectionAnchorKey(null);
    setShowSelectedOnly(false);
    onSelectionChange?.([]);
  }, [onSelectionChange]);

  const setSelectionKeys = useCallback(
    (keys: string[]) => {
      const unique = Array.from(new Set(keys));
      setSelectedRowKeys(unique);

      const nextSelected = unique
        .map((key) => rowByKey.get(key))
        .filter(Boolean) as T[];
      setSelectedRows(nextSelected);
      onSelectionChange?.(nextSelected);
    },
    [rowByKey, onSelectionChange],
  );

  const handleRowClickSelect = useCallback(
    (row: T, e: React.MouseEvent) => {
      if (!enableSelection || selectionMode !== "rowClick") return;

      const target = e.target as HTMLElement | null;
      if (
        target?.closest(
          "button,a,input,select,textarea,label,[role='button'],[data-ignore-row-select='true']",
        )
      ) {
        return;
      }

      const displayIndex = tableData.findIndex(
        (r, i) => getRowKey(r, i) === getRowKey(row),
      );
      const clickedIndex = displayIndex >= 0 ? displayIndex : 0;
      const clickedKey = getRowKey(row, clickedIndex);

      const isToggle = e.ctrlKey || e.metaKey;
      const isRange = e.shiftKey;

      if (isRange) {
        const anchorKey = selectionAnchorKey ?? clickedKey;
        const anchorIndex = tableData.findIndex(
          (r, i) => getRowKey(r, i) === anchorKey,
        );

        const from = anchorIndex >= 0 ? anchorIndex : clickedIndex;
        const start = Math.min(from, clickedIndex);
        const end = Math.max(from, clickedIndex);
        const rangeKeys = tableData
          .slice(start, end + 1)
          .map((r, i) => getRowKey(r, start + i));

        const next = isToggle ? [...selectedRowKeys, ...rangeKeys] : rangeKeys;
        setSelectionKeys(next);
        return;
      }

      setSelectionAnchorKey(clickedKey);

      if (isToggle) {
        if (selectedRowKeySet.has(clickedKey)) {
          setSelectionKeys(selectedRowKeys.filter((k) => k !== clickedKey));
        } else {
          setSelectionKeys([...selectedRowKeys, clickedKey]);
        }
        return;
      }

      setSelectionKeys([clickedKey]);
    },
    [
      enableSelection,
      selectionMode,
      tableData,
      getRowKey,
      selectionAnchorKey,
      selectedRowKeys,
      selectedRowKeySet,
      setSelectionKeys,
    ],
  );

  const conditionalRowStyles = useMemo(() => {
    if (!enableSelection || selectionMode !== "rowClick") return undefined;

    const selectedBg = theme === "dark" ? "#0b2a4a" : "#dbeafe";
    const selectedHoverBg = theme === "dark" ? "#0a223b" : "#cfe3ff";
    return [
      {
        when: (row: T) => selectedRowKeySet.has(getRowKey(row)),
        style: {
          backgroundColor: selectedBg,
          "&:hover": {
            backgroundColor: selectedHoverBg,
          },
        },
      },
    ];
  }, [enableSelection, selectionMode, selectedRowKeySet, getRowKey, theme]);

  // Export to Excel
  const exportToExcel = useCallback(
    (selectedOnly = false) => {
      const dataToExport =
        selectedOnly && selectedRows.length > 0 ? selectedRows : filteredData;

      // Extract only the visible columns
      const exportData = dataToExport.map((row) => {
        const exportRow: Record<string, any> = {};
        visibleColumns.forEach((col) => {
          if (col.name && col.selector) {
            const key = String(col.name);
            const value =
              typeof col.selector === "function"
                ? col.selector(row)
                : row[col.selector as keyof T];
            exportRow[key] = value;
          }
        });
        return exportRow;
      });

      const worksheet = XLSX.utils.json_to_sheet(exportData);
      const workbook = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(workbook, worksheet, "Data");

      // Auto-size columns
      const maxWidth = 50;
      const wscols = visibleColumns.map((col) => ({
        wch: Math.min(maxWidth, String(col.name).length + 5),
      }));
      worksheet["!cols"] = wscols;

      XLSX.writeFile(
        workbook,
        `${exportFileName}_${new Date().toISOString().split("T")[0]}.xlsx`,
      );
    },
    [visibleColumns, filteredData, selectedRows, exportFileName],
  );

  // Export to PDF
  const exportToPDF = useCallback(
    (selectedOnly = false) => {
      const dataToExport =
        selectedOnly && selectedRows.length > 0 ? selectedRows : filteredData;
      const doc = new jsPDF();

      // Add title
      doc.setFontSize(16);
      doc.text(title, 14, 15);

      // Add export date
      doc.setFontSize(10);
      doc.text(`Exported: ${new Date().toLocaleDateString()}`, 14, 22);

      // Prepare table data with only visible columns
      const tableColumns = visibleColumns
        .filter((col) => col.name)
        .map((col) => String(col.name));

      const tableData = dataToExport.map((row) =>
        visibleColumns
          .filter((col) => col.name)
          .map((col) => {
            if (col.selector) {
              const value =
                typeof col.selector === "function"
                  ? col.selector(row)
                  : row[col.selector as keyof T];
              return String(value || "");
            }
            return "";
          }),
      );

      autoTable(doc, {
        head: [tableColumns],
        body: tableData,
        startY: 28,
        theme: "grid",
        styles: { fontSize: 8, cellPadding: 2 },
        headStyles: { fillColor: [59, 130, 246], textColor: 255 },
        alternateRowStyles: { fillColor: [245, 247, 250] },
      });

      doc.save(
        `${exportFileName}_${new Date().toISOString().split("T")[0]}.pdf`,
      );
    },
    [visibleColumns, filteredData, selectedRows, title, exportFileName],
  );

  // Export to JSON
  const exportToJSON = useCallback(
    (selectedOnly = false) => {
      const dataToExport =
        selectedOnly && selectedRows.length > 0 ? selectedRows : filteredData;

      // Extract only the visible columns
      const exportData = dataToExport.map((row) => {
        const exportRow: Record<string, any> = {};
        visibleColumns.forEach((col) => {
          if (col.name && col.selector) {
            const key = String(col.name);
            const value =
              typeof col.selector === "function"
                ? col.selector(row)
                : row[col.selector as keyof T];
            exportRow[key] = value;
          }
        });
        return exportRow;
      });

      // Create JSON string with proper formatting
      const jsonString = JSON.stringify(exportData, null, 2);

      // Create blob and download
      const blob = new Blob([jsonString], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${exportFileName}_${
        new Date().toISOString().split("T")[0]
      }.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    },
    [visibleColumns, filteredData, selectedRows, exportFileName],
  );

  const openColumnManagerImpl = useCallback(
    (anchor?: HTMLElement | DOMRect | null) => {
      if (!anchor) {
        setColumnManagerAnchorRect(null);
      } else if (anchor instanceof HTMLElement) {
        setColumnManagerAnchorRect(anchor.getBoundingClientRect());
      } else {
        setColumnManagerAnchorRect(anchor as DOMRect);
      }
      setShowColumnManager(true);
    },
    [],
  );

  React.useImperativeHandle(
    ref,
    () => ({
      exportToExcel: (selectedOnly = false) => exportToExcel(selectedOnly),
      exportToPDF: (selectedOnly = false) => exportToPDF(selectedOnly),
      exportToJSON: (selectedOnly = false) => exportToJSON(selectedOnly),
      getSelectedRows: () => selectedRows,
      clearSelection: () => clearSelection(),
      selectAll: () => {
        const keys = tableRows.map((r) =>
          String((r as any)[internalRowKeyField]),
        );
        setSelectionKeys(keys);
      },
      openColumnManager: (anchor?: HTMLElement | DOMRect | null) =>
        openColumnManagerImpl(anchor),
    }),
    [
      exportToExcel,
      exportToPDF,
      exportToJSON,
      selectedRows,
      clearSelection,
      tableRows,
      setSelectionKeys,
      openColumnManagerImpl,
    ],
  );

  // Custom styles for react-data-table-component
  const customStyles = {
    tableWrapper: {
      style: {
        width: "100%",
      },
    },
    table: {
      style: {
        width: "100%",
        minWidth: "100%",
      },
    },
    head: {
      style: {
        width: "100%",
        minWidth: "100%",
      },
    },
    headRow: {
      style: {
        width: "100%",
        minWidth: "100%",
        backgroundColor: theme === "dark" ? "#1f2937" : "#f9fafb",
      },
    },
    rows: {
      style: {
        minHeight: "48px",
        width: "100%",
        minWidth: "100%",
        "&:hover": {
          backgroundColor: theme === "dark" ? "#1f2937" : "#f3f4f6",
        },
      },
    },
    headCells: {
      style: {
        paddingLeft: "16px",
        paddingRight: "16px",
        fontWeight: "600",
        fontSize: "14px",
        backgroundColor: theme === "dark" ? "#1f2937" : "#f9fafb",
        color: theme === "dark" ? "#f3f4f6" : "#111827",
      },
    },
    cells: {
      style: {
        paddingLeft: "16px",
        paddingRight: "16px",
        fontSize: "14px",
        color: theme === "dark" ? "#e5e7eb" : "#374151",
        backgroundColor: "inherit",
      },
    },
  };

  return (
    <div className="w-full space-y-4">
      {/* Header Section */}

      {/* Stats Bar */}
      {/* <div className="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-4 text-xs text-gray-600 dark:text-gray-400">
          <span className="font-medium">
            Total:{" "}
            <span className="text-gray-900 dark:text-gray-100">
              {data.length}
            </span>
          </span>
          {filteredData.length !== data.length && (
            <span className="font-medium">
              Filtered:{" "}
              <span className="text-blue-600 dark:text-blue-400">
                {filteredData.length}
              </span>
            </span>
          )}
          {enableSelection && enableSelectedOnlyFilter && showSelectedOnly && (
            <span className="font-medium">
              Showing:{" "}
              <span className="text-blue-600 dark:text-blue-400">
                Selected Only ({tableData.length})
              </span>
            </span>
          )}
          {enableSelection && selectedRows.length > 0 && (
            <span className="font-medium">
              Selected:{" "}
              <span className="text-green-600 dark:text-green-400">
                {selectedRows.length}
              </span>
            </span>
          )}
          <span className="font-medium">
            Columns:{" "}
            <span className="text-purple-600 dark:text-purple-400">
              {visibleColumns.length}/{columns.length}
            </span>
          </span>
        </div>
      </div> */}

      {/* Data Table */}
      <div className="w-full overflow-x-auto bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
        <DataTable
          columns={dataTableColumns as unknown as TableColumn<RowWithKey>[]}
          data={tableRows}
          pagination
          paginationPerPage={500}
          paginationRowsPerPageOptions={[25, 50, 100, 250, 500]}
          keyField={internalRowKeyField}
          selectableRows={enableSelection && selectionMode === "checkbox"}
          selectableRowsHighlight={
            enableSelection && selectionMode === "checkbox"
          }
          onSelectedRowsChange={
            enableSelection && selectionMode === "checkbox"
              ? handleSelectedRowsChange
              : undefined
          }
          progressPending={loading}
          progressComponent={
            <div className="flex items-center justify-center p-20">
              {/* Replace with your actual loader or a simple spinner */}
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          }
          noDataComponent={
            <div className="flex items-center justify-center p-12">
              <div className="text-center">
                <p className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-1">
                  {noDataMessage}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {effectiveSearchTerm ||
                  Object.values(filterValues).some(Boolean)
                    ? "Try adjusting your search or filters"
                    : "Start by adding some data"}
                </p>
              </div>
            </div>
          }
          theme={theme === "dark" ? "dark" : "default"}
          customStyles={customStyles}
          conditionalRowStyles={conditionalRowStyles}
          highlightOnHover
          pointerOnHover
          onRowClicked={(row: RowWithKey, e: React.MouseEvent) => {
            const target = e.target as HTMLElement | null;
            if (enableSelection && selectionMode === "rowClick") {
              handleRowClickSelect(row, e);
            }

            // Avoid activating when clicking interactive controls inside the row
            if (
              target?.closest(
                "button,a,input,select,textarea,label,[role='button'],[data-ignore-row-select='true']",
              )
            ) {
              return;
            }

            onRowClicked?.(row);
          }}
          onRowDoubleClicked={(row: RowWithKey) => {
            onRowDoubleClicked?.(row);
          }}
          responsive
          dense={false}
        />
      </div>
    </div>
  );
});

export default AdvancedDataTable as <T extends Record<string, any>>(
  props: AdvancedDataTableProps<T> & {
    ref?: React.Ref<AdvancedDataTableHandle<T>>;
  },
) => React.ReactElement;
