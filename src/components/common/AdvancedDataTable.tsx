import React, { useState, useMemo, useCallback } from "react";
import DataTable, { TableColumn } from "react-data-table-component";
import {
  FaFileExcel,
  FaFilePdf,
  FaSearch,
  FaTimes,
  FaFilter,
  FaDownload,
  FaSortAmountDown,
  FaSortAmountUp,
} from "react-icons/fa";
import { useTheme } from "../../context/ThemeContext";
import * as XLSX from "xlsx";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

export interface ColumnFilter {
  key: string;
  label: string;
  options?: Array<{ value: string; label: string }>;
  type?: "select" | "text" | "date";
}

interface AdvancedDataTableProps<T> {
  data: T[];
  columns: TableColumn<T>[];
  title?: string;
  loading?: boolean;
  filters?: ColumnFilter[];
  enableExport?: boolean;
  enableSelection?: boolean;
  onSelectionChange?: (selectedRows: T[]) => void;
  customActions?: React.ReactNode;
  exportFileName?: string;
  onRowClicked?: (row: T) => void;
  searchPlaceholder?: string;
  noDataMessage?: string;
}

export default function AdvancedDataTable<T extends Record<string, any>>({
  data,
  columns,
  title = "Data Table",
  loading = false,
  filters = [],
  enableExport = true,
  enableSelection = false,
  onSelectionChange,
  customActions,
  exportFileName = "export",
  onRowClicked,
  searchPlaceholder = "Search...",
  noDataMessage = "No data available",
}: AdvancedDataTableProps<T>) {
  const { theme } = useTheme();
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedRows, setSelectedRows] = useState<T[]>([]);
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [showFilters, setShowFilters] = useState(false);

  // Filter and search logic
  const filteredData = useMemo(() => {
    let result = [...data];

    // Apply search
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase();
      result = result.filter((row) =>
        Object.values(row).some((value) =>
          String(value).toLowerCase().includes(searchLower)
        )
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
  }, [data, searchTerm, filterValues]);

  // Handle selection
  const handleSelectedRowsChange = useCallback(
    (state: { selectedRows: T[] }) => {
      setSelectedRows(state.selectedRows);
      onSelectionChange?.(state.selectedRows);
    },
    [onSelectionChange]
  );

  // Export to Excel
  const exportToExcel = useCallback(
    (selectedOnly = false) => {
      const dataToExport = selectedOnly && selectedRows.length > 0 ? selectedRows : filteredData;
      
      // Extract only the visible columns
      const exportData = dataToExport.map((row) => {
        const exportRow: Record<string, any> = {};
        columns.forEach((col) => {
          if (col.name && col.selector) {
            const key = String(col.name);
            const value = typeof col.selector === "function" ? col.selector(row) : row[col.selector as keyof T];
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
      const wscols = columns.map((col) => ({ wch: Math.min(maxWidth, String(col.name).length + 5) }));
      worksheet["!cols"] = wscols;
      
      XLSX.writeFile(workbook, `${exportFileName}_${new Date().toISOString().split("T")[0]}.xlsx`);
    },
    [columns, filteredData, selectedRows, exportFileName]
  );

  // Export to PDF
  const exportToPDF = useCallback(
    (selectedOnly = false) => {
      const dataToExport = selectedOnly && selectedRows.length > 0 ? selectedRows : filteredData;
      const doc = new jsPDF();

      // Add title
      doc.setFontSize(16);
      doc.text(title, 14, 15);
      
      // Add export date
      doc.setFontSize(10);
      doc.text(`Exported: ${new Date().toLocaleDateString()}`, 14, 22);

      // Prepare table data
      const tableColumns = columns
        .filter((col) => col.name)
        .map((col) => String(col.name));

      const tableData = dataToExport.map((row) =>
        columns
          .filter((col) => col.name)
          .map((col) => {
            if (col.selector) {
              const value = typeof col.selector === "function" 
                ? col.selector(row) 
                : row[col.selector as keyof T];
              return String(value || "");
            }
            return "";
          })
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

      doc.save(`${exportFileName}_${new Date().toISOString().split("T")[0]}.pdf`);
    },
    [columns, filteredData, selectedRows, title, exportFileName]
  );

  // Clear filters
  const clearFilters = useCallback(() => {
    setSearchTerm("");
    setFilterValues({});
  }, []);

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
      },
    },
  };

  return (
    <div className="w-full space-y-4">
      {/* Header Section */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        {/* Search Bar */}
        <div className="relative flex-1 max-w-md">
          <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
            <FaSearch className="w-4 h-4 text-gray-400" />
          </div>
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder={searchPlaceholder}
            className="w-full pl-10 pr-10 py-2.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white dark:placeholder-gray-400"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm("")}
              className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <FaTimes className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Filter Toggle */}
          {filters.length > 0 && (
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                showFilters
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
          {(searchTerm || Object.values(filterValues).some(Boolean)) && (
            <button
              onClick={clearFilters}
              className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
            >
              <FaTimes className="w-4 h-4" />
              Clear
            </button>
          )}

          {/* Export Dropdown */}
          {enableExport && (
            <div className="relative group">
              <button className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 transition-colors">
                <FaDownload className="w-4 h-4" />
                Export
                {selectedRows.length > 0 && (
                  <span className="px-2 py-0.5 text-xs rounded-full bg-white text-green-600">
                    {selectedRows.length}
                  </span>
                )}
              </button>

              {/* Dropdown Menu */}
              <div className="absolute right-0 z-10 hidden mt-2 w-56 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 group-hover:block">
                <div className="py-1">
                  <div className="px-4 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                    Export All Data
                  </div>
                  <button
                    onClick={() => exportToExcel(false)}
                    className="flex items-center gap-3 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                  >
                    <FaFileExcel className="w-4 h-4 text-green-600" />
                    Excel ({filteredData.length} rows)
                  </button>
                  <button
                    onClick={() => exportToPDF(false)}
                    className="flex items-center gap-3 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                  >
                    <FaFilePdf className="w-4 h-4 text-red-600" />
                    PDF ({filteredData.length} rows)
                  </button>

                  {enableSelection && selectedRows.length > 0 && (
                    <>
                      <div className="my-1 border-t border-gray-200 dark:border-gray-700"></div>
                      <div className="px-4 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                        Export Selected
                      </div>
                      <button
                        onClick={() => exportToExcel(true)}
                        className="flex items-center gap-3 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                      >
                        <FaFileExcel className="w-4 h-4 text-green-600" />
                        Excel ({selectedRows.length} selected)
                      </button>
                      <button
                        onClick={() => exportToPDF(true)}
                        className="flex items-center gap-3 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                      >
                        <FaFilePdf className="w-4 h-4 text-red-600" />
                        PDF ({selectedRows.length} selected)
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Custom Actions */}
          {customActions}
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && filters.length > 0 && (
        <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filters.map((filter) => (
              <div key={filter.key}>
                <label className="block mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                  {filter.label}
                </label>
                {filter.type === "select" && filter.options ? (
                  <select
                    value={filterValues[filter.key] || ""}
                    onChange={(e) =>
                      setFilterValues((prev) => ({ ...prev, [filter.key]: e.target.value }))
                    }
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
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
                      setFilterValues((prev) => ({ ...prev, [filter.key]: e.target.value }))
                    }
                    placeholder={`Filter by ${filter.label.toLowerCase()}`}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400"
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Stats Bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
          <span className="font-medium">
            Total: <span className="text-gray-900 dark:text-gray-100">{data.length}</span>
          </span>
          {filteredData.length !== data.length && (
            <span className="font-medium">
              Filtered: <span className="text-blue-600 dark:text-blue-400">{filteredData.length}</span>
            </span>
          )}
          {enableSelection && selectedRows.length > 0 && (
            <span className="font-medium">
              Selected: <span className="text-green-600 dark:text-green-400">{selectedRows.length}</span>
            </span>
          )}
        </div>
      </div>

      {/* Data Table */}
      <div className="overflow-hidden bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
        <DataTable
          columns={columns}
          data={filteredData}
          pagination
          paginationPerPage={10}
          paginationRowsPerPageOptions={[10, 25, 50, 100]}
          selectableRows={enableSelection}
          onSelectedRowsChange={handleSelectedRowsChange}
          progressPending={loading}
          progressComponent={
            <div className="flex items-center justify-center p-12">
              <div className="flex flex-col items-center gap-3">
                <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Loading data...</p>
              </div>
            </div>
          }
          noDataComponent={
            <div className="flex items-center justify-center p-12">
              <div className="text-center">
                <p className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-1">
                  {noDataMessage}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {searchTerm || Object.values(filterValues).some(Boolean)
                    ? "Try adjusting your search or filters"
                    : "Start by adding some data"}
                </p>
              </div>
            </div>
          }
          theme={theme === "dark" ? "dark" : "default"}
          customStyles={customStyles}
          highlightOnHover
          pointerOnHover
          onRowClicked={onRowClicked}
          responsive
          dense={false}
        />
      </div>
    </div>
  );
}
