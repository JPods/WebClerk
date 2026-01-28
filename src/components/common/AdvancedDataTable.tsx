import React, {
  useState,
  useMemo,
  useCallback,
  useRef,
  useEffect,
} from "react";
import DataTable, { TableColumn } from "react-data-table-component";
import { useDrag, useDrop, DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { useTheme } from "@/context/ThemeContext";
import {
  FaGripVertical,
  FaPlus,
  FaEdit,
  FaFileImport,
  FaTimes,
  FaFilter,
  FaDownload,
  FaPrint,
  FaCheckSquare,
  FaSearch,
  FaTrash,
  FaFileExcel,
  FaFilePdf,
  FaFileCode,
} from "react-icons/fa";
import * as XLSX from "xlsx";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

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
  showGlobalMenu?: boolean;
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

type AdvancedDataTableHandle<T> = {
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
    filters = [],
    hideHeader = false,
    externalSearchTerm,
    onExternalSearchTermChange,
    filtersOpen,
    onFiltersOpenChange,
    showGlobalMenu = true,
    onAdd,
    onEditSelected,
    onDeleteSelected,
    onImportFile,
    importAccept = ".json,.csv",
    onPrint,
    storageKey,
    enableExport = true,
    enableSelection = false,
    onSelectionChange,
    onVisibleRowsChange,
    customActions,
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
    searchPlaceholder = "Search...",
    noDataMessage = "No data available",
  }: AdvancedDataTableProps<T>,
  ref: React.Ref<AdvancedDataTableHandle<T>>,
) {
  type RowWithKey = T & { __wcRowKey: string };
  const internalRowKeyField = "__wcRowKey" as const;

  const { theme } = useTheme();
  const [searchTerm, setSearchTerm] = useState("");
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

  const effectiveShowFilters = filtersOpen ?? showFilters;
  const setEffectiveShowFilters = useCallback(
    (open: boolean) => {
      if (onFiltersOpenChange) {
        onFiltersOpenChange(open);
      } else {
        setShowFiltersState(open);
      }
    },
    [onFiltersOpenChange],
  );

  const handleImportClick = useCallback(() => {
    importInputRef.current?.click();
  }, []);

  const handleImportChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;
      onImportFile?.(file);
      event.target.value = "";
    },
    [onImportFile],
  );

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

  // Move column position
  const moveColumn = useCallback((dragIndex: number, hoverIndex: number) => {
    setColumns((prevColumns) => {
      const newColumns = [...prevColumns];
      const [draggedColumn] = newColumns.splice(dragIndex, 1);
      newColumns.splice(hoverIndex, 0, draggedColumn);
      return newColumns;
    });
    setColumnVisibility((prevVisibility) => {
      const newVisibility = [...prevVisibility];
      const [draggedVisibility] = newVisibility.splice(dragIndex, 1);
      newVisibility.splice(hoverIndex, 0, draggedVisibility);
      return newVisibility;
    });
  }, []);

  // Toggle column visibility
  const toggleColumnVisibility = useCallback((index: number) => {
    setColumnVisibility((prev) => {
      const newVisibility = [...prev];
      newVisibility[index] = !newVisibility[index];
      return newVisibility;
    });
  }, []);

  // Show/Hide all columns
  const toggleAllColumns = useCallback(
    (visible: boolean) => {
      setColumnVisibility(columns.map(() => visible));
    },
    [columns],
  );

  // Reset columns to original order and visibility
  const resetColumnOrder = useCallback(() => {
    setColumns(initialColumns);
    setColumnVisibility(initialColumns.map(() => true));
    if (columnStorageKey) {
      try {
        localStorage.removeItem(columnStorageKey);
      } catch {
        // ignore
      }
    }
  }, [initialColumns, columnStorageKey]);

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
    data.forEach((row, index) => {
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

    return visibleColumns.map((col) => {
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

  // Filter and search logic
  const filteredData = useMemo(() => {
    let result = [...data];

    // Apply search
    if (effectiveSearchTerm) {
      const searchLower = effectiveSearchTerm.toLowerCase();
      result = result.filter((row) =>
        Object.values(row).some((value) =>
          String(value).toLowerCase().includes(searchLower),
        ),
      );
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
  }, [data, effectiveSearchTerm, filterValues]);

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

  // Clear filters
  const clearFilters = useCallback(() => {
    setEffectiveSearchTerm("");
    setFilterValues({});
  }, [setEffectiveSearchTerm]);

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
    rows: {
      style: {
        minHeight: "48px",
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
      {!hideHeader && (
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            {showGlobalMenu && (
              <>
                <button
                  onClick={onAdd}
                  disabled={!onAdd}
                  className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                  title="Add"
                >
                  <FaPlus className="w-4 h-4" />
                  Add
                </button>
                <button
                  onClick={() =>
                    selectedRows.length === 1 &&
                    onEditSelected?.(selectedRows[0])
                  }
                  disabled={!onEditSelected || selectedRows.length !== 1}
                  className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 transition-colors disabled:opacity-50"
                  title="Edit"
                >
                  <FaEdit className="w-4 h-4" />
                  Edit
                </button>
                {/* Delete moved after search bar for right-aligned placement */}
                <button
                  onClick={handleImportClick}
                  disabled={!onImportFile}
                  className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-white bg-slate-600 rounded-lg hover:bg-slate-700 transition-colors disabled:opacity-50"
                  title="Import"
                >
                  <FaFileImport className="w-4 h-4" />
                  Import
                </button>
                <input
                  ref={importInputRef}
                  type="file"
                  accept={importAccept}
                  className="hidden"
                  onChange={handleImportChange}
                />
              </>
            )}

            {/* Filter Toggle */}
            {filters.length > 0 && (
              <button
                onClick={() => setEffectiveShowFilters(!effectiveShowFilters)}
                className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium rounded-lg transition-colors ${
                  effectiveShowFilters
                    ? "bg-blue-600 text-white hover:bg-blue-700"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                }`}
              >
                <FaFilter className="w-4 h-4" />
                Filters
                {Object.values(filterValues).filter(Boolean).length > 0 && (
                  <span className="px-2 py-0.5 text-xs rounded-full bg-white text-blue-600 dark:bg-gray-800 dark:text-blue-400">
                    {Object.values(filterValues).filter(Boolean).length}
                  </span>
                )}
              </button>
            )}

            {/* Clear Filters */}
            {(effectiveSearchTerm ||
              Object.values(filterValues).some(Boolean)) && (
              <button
                onClick={clearFilters}
                className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
              >
                <FaTimes className="w-4 h-4" />
                Clear
              </button>
            )}

            {showGlobalMenu && (
              <button
                onClick={onPrint}
                disabled={!onPrint}
                className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-white bg-yellow-600 rounded-lg hover:bg-yellow-700 transition-colors disabled:opacity-50"
                title="Print"
              >
                <FaPrint className="w-4 h-4" />
                Print
              </button>
            )}

            {/* Selected-only filter */}
            {enableSelection &&
              enableSelectedOnlyFilter &&
              selectionMode === "rowClick" &&
              selectedRowKeys.length > 0 && (
                <button
                  onClick={() => setShowSelectedOnly((v) => !v)}
                  className={`flex items-center gap-2 px-4 py-2 text-xs font-medium rounded-lg transition-colors ${
                    showSelectedOnly
                      ? "bg-blue-600 text-white hover:bg-blue-700"
                      : "bg-blue-50 text-blue-700 hover:bg-blue-100 dark:bg-blue-900/20 dark:text-blue-300 dark:hover:bg-blue-900/30"
                  }`}
                >
                  {showSelectedOnly ? "Show All" : "Show Selected"}
                  <span
                    className={`px-2 py-0.5 text-xs rounded-full ${
                      showSelectedOnly
                        ? "bg-white text-blue-600"
                        : "bg-blue-600 text-white"
                    }`}
                  >
                    {selectedRowKeys.length}
                  </span>
                </button>
              )}

            {/* Clear selection */}
            {enableSelection &&
              selectionMode === "rowClick" &&
              selectedRowKeys.length > 0 && (
                <button
                  onClick={clearSelection}
                  className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                >
                  <FaTimes className="w-4 h-4" />
                  Clear Selection
                </button>
              )}
            {/* Export Dropdown */}
            {enableExport && (
              <div className="relative" ref={exportDropdownRef}>
                <button
                  onClick={() => setShowExportDropdown(!showExportDropdown)}
                  className="flex items-center gap-2 px-3 py-2 text-xs font-medium transition-colors disabled:opacity-50 text-white bg-green-600 rounded-lg hover:bg-green-700 "
                >
                  <FaDownload className="w-4 h-4" />
                  Export
                  {selectedRows.length > 0 && (
                    <span className="px-2  text-xs rounded-full bg-white text-green-600">
                      {selectedRows.length}
                    </span>
                  )}
                </button>

                {/* Dropdown Menu */}
                {showExportDropdown && (
                  <div className="absolute right-0 z-10 mt-2 w-56 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
                    <div className="py-1">
                      <div className="px-4 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                        Export All Data
                      </div>
                      <button
                        onClick={() => exportToExcel(false)}
                        className="flex items-center gap-3 w-full px-4 py-2 text-xs text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                      >
                        <FaFileExcel className="w-4 h-4 text-green-600" />
                        Excel ({filteredData.length} rows)
                      </button>
                      <button
                        onClick={() => exportToPDF(false)}
                        className="flex items-center gap-3 w-full px-4 py-2 text-xs text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                      >
                        <FaFilePdf className="w-4 h-4 text-red-600" />
                        PDF ({tableData.length} rows)
                      </button>
                      <button
                        onClick={() => exportToJSON(false)}
                        className="flex items-center gap-3 w-full px-4 py-2 text-xs text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                      >
                        <FaFileCode className="w-4 h-4 text-blue-600" />
                        JSON ({filteredData.length} rows)
                      </button>

                      {enableSelection && selectedRows.length > 0 && (
                        <>
                          <div className="my-1 border-t border-gray-200 dark:border-gray-700"></div>
                          <div className="px-4 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                            Export Selected
                          </div>
                          <button
                            onClick={() => exportToExcel(true)}
                            className="flex items-center gap-3 w-full px-4 py-2 text-xs text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                          >
                            <FaFileExcel className="w-4 h-4 text-green-600" />
                            Excel ({selectedRows.length} selected)
                          </button>
                          <button
                            onClick={() => exportToPDF(true)}
                            className="flex items-center gap-3 w-full px-4 py-2 text-xs text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                          >
                            <FaFilePdf className="w-4 h-4 text-red-600" />
                            PDF ({selectedRows.length} selected)
                          </button>
                          <button
                            onClick={() => exportToJSON(true)}
                            className="flex items-center gap-3 w-full px-4 py-2 text-xs text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                          >
                            <FaFileCode className="w-4 h-4 text-blue-600" />
                            JSON ({selectedRows.length} selected)
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Column Manager */}
            <div className="relative" ref={columnManagerRef}>
              <button
                onClick={() => setShowColumnManager(!showColumnManager)}
                className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 transition-colors"
              >
                <FaGripVertical className="w-4 h-4" />
                Columns
                <span className="px-2 py-0.5 text-xs rounded-full bg-blue-600 text-white">
                  {columnVisibility.filter(Boolean).length}/{columns.length}
                </span>
              </button>

              {/* Column Manager Dropdown */}
              {showColumnManager && (
                <div className="absolute right-0 z-10 mt-2 w-96 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
                  <div className="p-4">
                    {/* Header */}
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-xs font-semibold text-gray-900 dark:text-gray-100">
                        Manage Columns
                      </h3>
                      <button
                        onClick={resetColumnOrder}
                        className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-medium"
                      >
                        Reset All
                      </button>
                    </div>

                    {/* Quick Actions */}
                    <div className="flex items-center gap-2 mb-3">
                      <button
                        onClick={() => toggleAllColumns(true)}
                        className="flex-1 px-3 py-1.5 text-xs font-medium text-green-700 bg-green-50 rounded hover:bg-green-100 dark:bg-green-900/20 dark:text-green-400 dark:hover:bg-green-900/30"
                      >
                        Show All
                      </button>
                      <button
                        onClick={() => toggleAllColumns(false)}
                        className="flex-1 px-3 py-1.5 text-xs font-medium text-red-700 bg-red-50 rounded hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400 dark:hover:bg-red-900/30"
                      >
                        Hide All
                      </button>
                    </div>

                    {/* Instructions */}
                    <div className="mb-3 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                      <p className="text-xs text-blue-700 dark:text-blue-300">
                        <strong>✓</strong> Check/uncheck to show/hide columns
                        <br />
                        <strong>↕</strong> Drag to reorder columns
                      </p>
                    </div>

                    {/* Column List */}
                    <DndProvider backend={HTML5Backend}>
                      <div className="space-y-1 max-h-96 overflow-y-auto">
                        {columns.map((col, index) => (
                          <div
                            key={getColumnPersistKey(col, index)}
                            className={`flex items-center gap-2 p-3 rounded transition-colors ${
                              columnVisibility[index]
                                ? "bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600"
                                : "bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700"
                            }`}
                          >
                            <DraggableColumnHeader
                              column={String(col.name)}
                              index={index}
                              visible={columnVisibility[index]}
                              moveColumn={moveColumn}
                              toggleVisibility={toggleColumnVisibility}
                            />
                          </div>
                        ))}
                      </div>
                    </DndProvider>

                    {/* Footer Info */}
                    <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                      <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
                        Visible:{" "}
                        <span className="font-medium text-blue-600 dark:text-blue-400">
                          {columnVisibility.filter(Boolean).length}
                        </span>{" "}
                        / Total:{" "}
                        <span className="font-medium">{columns.length}</span>
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Custom Actions */}
            {customActions}

            {/* Search Bar + Delete (right-aligned) */}
            <div className="flex items-center gap-2 w-full lg:w-auto">
              <div className="relative flex-1">
                <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                  <FaSearch className="w-4 h-4 text-gray-400" />
                </div>
                <input
                  type="text"
                  value={effectiveSearchTerm}
                  onChange={(e) => setEffectiveSearchTerm(e.target.value)}
                  placeholder={searchPlaceholder}
                  className="w-full pl-10 pr-10 py-2.5 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white dark:placeholder-gray-400"
                />
                {effectiveSearchTerm && (
                  <button
                    onClick={() => setEffectiveSearchTerm("")}
                    className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  >
                    <FaTimes className="w-4 h-4" />
                  </button>
                )}
              </div>

              {showGlobalMenu && (
                <button
                  onClick={() => onDeleteSelected?.(selectedRows)}
                  disabled={!onDeleteSelected || selectedRows.length === 0}
                  className="ml-2 flex items-center gap-2 px-3 py-2 text-xs font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                  title="Delete"
                >
                  <FaTrash className="w-4 h-4" />
                  Delete
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {hideHeader && customActions && (
        <div className="flex flex-wrap items-center gap-2">{customActions}</div>
      )}

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
                      setFilterValues((prev) => ({
                        ...prev,
                        [filter.key]: e.target.value,
                      }))
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
                      setFilterValues((prev) => ({
                        ...prev,
                        [filter.key]: e.target.value,
                      }))
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

      {/* Stats Bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
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
      </div>

      {/* Column Manager (rendered when header is hidden) */}
      {/* {showColumnManager && (
        <div
          style={
            columnManagerAnchorRect
              ? (() => {
                  const rect = columnManagerAnchorRect;
                  const panelWidth = 384; // w-96
                  const top = Math.min(
                    window.innerHeight - 48,
                    rect.bottom + 8,
                  );
                  // center under button, but keep within viewport with 8px padding
                  let left = Math.round(
                    rect.left + rect.width / 2 - panelWidth / 2,
                  );
                  left = Math.max(
                    8,
                    Math.min(window.innerWidth - panelWidth - 8, left),
                  );
                  return {
                    position: "fixed",
                    top,
                    left,
                    zIndex: 50,
                  } as React.CSSProperties;
                })()
              : { position: "fixed", right: 24, top: 96, zIndex: 50 }
          }
          ref={columnManagerRef}
        >
          <div className="w-96 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-semibold text-gray-900 dark:text-gray-100">
                  Manage Columns
                </h3>
                <button
                  onClick={resetColumnOrder}
                  className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-medium"
                >
                  Reset All
                </button>
              </div>

              <div className="flex items-center gap-2 mb-3">
                <button
                  onClick={() => toggleAllColumns(true)}
                  className="flex-1 px-3 py-1.5 text-xs font-medium text-green-700 bg-green-50 rounded hover:bg-green-100 dark:bg-green-900/20 dark:text-green-400 dark:hover:bg-green-900/30"
                >
                  Show All
                </button>
                <button
                  onClick={() => toggleAllColumns(false)}
                  className="flex-1 px-3 py-1.5 text-xs font-medium text-red-700 bg-red-50 rounded hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400 dark:hover:bg-red-900/30"
                >
                  Hide All
                </button>
              </div>

              <div className="mb-3 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <p className="text-xs text-blue-700 dark:text-blue-300">
                  <strong>✓</strong> Check/uncheck to show/hide columns
                </p>
              </div>

              <div className="max-h-64 overflow-y-auto">
                {columns.map((c, i) => (
                  <div
                    key={String(c.name || i)}
                    className="flex items-center justify-between p-2 rounded hover:bg-gray-50 dark:hover:bg-gray-900"
                  >
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={!!columnVisibility[i]}
                        onChange={() => toggleColumnVisibility(i)}
                        className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                      />
                      <span className="text-xs">
                        {String(c.name || c.selector || `col-${i}`)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => moveColumn(i, i - 1)}
                        className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400"
                        title="Move up"
                        disabled={i === 0}
                      >
                        ▲
                      </button>
                      <button
                        onClick={() => moveColumn(i, i + 1)}
                        className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400"
                        title="Move down"
                        disabled={i === columns.length - 1}
                      >
                        ▼
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-3 text-right">
                <button
                  onClick={() => setShowColumnManager(false)}
                  className="px-3 py-1.5 text-xs font-medium text-gray-700 bg-gray-100 rounded hover:bg-gray-200"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )} */}

      {/* Data Table */}
      <div className="overflow-hidden bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
        <DataTable
          columns={dataTableColumns as unknown as TableColumn<RowWithKey>[]}
          data={tableRows}
          pagination
          paginationPerPage={10}
          paginationRowsPerPageOptions={[10, 25, 50, 100]}
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
            <div className="flex items-center justify-center p-12">
              <div className="flex flex-col items-center gap-3">
                <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  Loading data...
                </p>
              </div>
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
