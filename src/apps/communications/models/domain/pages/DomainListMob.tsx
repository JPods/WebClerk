import {
  useState,
  useEffect,
  useMemo,
  useCallback,
  type ReactNode,
} from "react";
import { dynamicData } from "../../../../../model/dynamicData";
import AccordionItem from "@/components/accordion/AccordionItem";
import {
  ColumnFilter,
  parseSearchTerms,
} from "../../../../../components/common/AdvancedDataTable";
import {
  FaSearch,
  FaTimes,
  FaDownload,
  FaFilter,
  FaFileExcel,
  FaFilePdf,
  FaFileCode,
} from "react-icons/fa";
import * as XLSX from "xlsx";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

type ExportColumn = {
  name?: string;
  selector?: string | ((row: dynamicData) => any);
};

interface DomainListMobProps {
  dataProp: dynamicData[];
  selectedDomain?: dynamicData | null;
  handleView: (row: dynamicData) => void;
  handleEdit: (row: dynamicData) => void;
  emptyMessage?: string;
  filters?: ColumnFilter[];
  searchPlaceholder?: string;
  enableDatabaseSearch?: boolean;
  searchDatabase?: boolean;
  onSearchModeChange?: (searchDatabase: boolean) => void;
  onDatabaseSearch?: (terms: string[]) => Promise<void> | void;
  enableExport?: boolean;
  exportFileName?: string;
  customActions?: ReactNode;
  loading?: boolean;
  columnsForExport?: ExportColumn[];
}

export default function DomainListMob({
  dataProp,
  selectedDomain,
  handleView,
  handleEdit: _handleEdit,
  emptyMessage,
  filters = [],
  searchPlaceholder = "Search...",
  enableDatabaseSearch = false,
  searchDatabase,
  onSearchModeChange,
  onDatabaseSearch,
  enableExport = true,
  exportFileName = "domain_export",
  customActions,
  loading = false,
  columnsForExport = [],
}: DomainListMobProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [showFilters, setShowFilters] = useState(false);
  const [showExportDropdown, setShowExportDropdown] = useState(false);
  const [searchDatabaseInternal, setSearchDatabaseInternal] = useState(false);

  const effectiveSearchDatabase = searchDatabase ?? searchDatabaseInternal;
  const setEffectiveSearchDatabase =
    onSearchModeChange ?? setSearchDatabaseInternal;

  const rowMatchesAllTerms = useCallback(
    (row: Record<string, any>, terms: string[]) => {
      if (!terms.length) return true;

      const searchableValues: string[] = [];

      Object.entries(row).forEach(([_, value]) => {
        if (value === null || value === undefined) return;
        if (
          typeof value === "string" ||
          typeof value === "number" ||
          typeof value === "boolean"
        ) {
          searchableValues.push(String(value).toLowerCase());
        }
      });

      const refs = row.refs;
      if (refs && typeof refs === "object") {
        const keywords = (refs as any).keywords;
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

      const searchableText = searchableValues.join(" ");
      return terms.every((term) => searchableText.includes(term));
    },
    [],
  );

  const filteredData = useMemo(() => {
    const base = Array.isArray(dataProp) ? dataProp : [];

    if (effectiveSearchDatabase && searchTerm && onDatabaseSearch) {
      return [...base];
    }

    let next = [...base];

    if (searchTerm) {
      const terms = parseSearchTerms(searchTerm);
      if (terms.length > 0) {
        next = next.filter((row) => rowMatchesAllTerms(row, terms));
      }
    }

    Object.entries(filterValues).forEach(([key, value]) => {
      if (value) {
        next = next.filter((row) => {
          const rowValue = String((row as any)[key] || "").toLowerCase();
          return rowValue.includes(value.toLowerCase());
        });
      }
    });

    return next;
  }, [
    dataProp,
    effectiveSearchDatabase,
    searchTerm,
    onDatabaseSearch,
    filterValues,
    rowMatchesAllTerms,
  ]);

  useEffect(() => {
    if (
      effectiveSearchDatabase &&
      onDatabaseSearch &&
      searchTerm &&
      searchTerm.trim()
    ) {
      const terms = parseSearchTerms(searchTerm);
      if (terms.length > 0) {
        onDatabaseSearch(terms);
      }
    }
  }, [effectiveSearchDatabase, onDatabaseSearch, searchTerm]);

  useEffect(() => {
    if (selectedDomain?.id && filteredData?.length) {
      const idx = filteredData.findIndex(
        (item) => String(item.id) === String(selectedDomain.id),
      );
      setOpenIndex(idx >= 0 ? idx : null);
    } else {
      setOpenIndex(null);
    }
  }, [selectedDomain, filteredData]);

  const dataToRender = filteredData;

  const exportColumns =
    columnsForExport.length > 0 ? columnsForExport : undefined;

  const exportRows = useCallback(
    () =>
      dataToRender.map((row) => {
        const exportRow: Record<string, any> = {};

        if (exportColumns) {
          exportColumns.forEach((col, idx) => {
            const key = col.name || `col_${idx + 1}`;
            if (typeof col.selector === "function") {
              exportRow[key] = col.selector(row);
            } else if (typeof col.selector === "string") {
              exportRow[key] = (row as any)[col.selector];
            } else if ((row as any)[key] !== undefined) {
              exportRow[key] = (row as any)[key];
            }
          });
        } else {
          Object.entries(row).forEach(([k, v]) => {
            if (typeof v !== "object" && typeof v !== "function") {
              exportRow[k] = v;
            }
          });
        }

        return exportRow;
      }),
    [dataToRender, exportColumns],
  );

  const exportToExcel = useCallback(() => {
    const worksheet = XLSX.utils.json_to_sheet(exportRows());
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Data");
    XLSX.writeFile(
      workbook,
      `${exportFileName}_${new Date().toISOString().split("T")[0]}.xlsx`,
    );
  }, [exportRows, exportFileName]);

  const exportToPDF = useCallback(() => {
    const rows = exportRows();
    const doc = new jsPDF();

    const headers = exportColumns
      ? exportColumns.map((c, idx) => c.name || `Col ${idx + 1}`)
      : Object.keys(rows[0] || {});

    const body = rows.map((row) =>
      headers.map((h) => String((row as any)[h] ?? "")),
    );

    doc.setFontSize(14);
    doc.text("Domain", 14, 15);
    doc.setFontSize(10);
    doc.text(`Exported: ${new Date().toLocaleDateString()}`, 14, 22);

    autoTable(doc, {
      head: [headers],
      body,
      startY: 28,
      theme: "grid",
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { fillColor: [59, 130, 246], textColor: 255 },
      alternateRowStyles: { fillColor: [245, 247, 250] },
    });

    doc.save(`${exportFileName}_${new Date().toISOString().split("T")[0]}.pdf`);
  }, [exportColumns, exportRows, exportFileName]);

  const exportToJSON = useCallback(() => {
    const jsonString = JSON.stringify(exportRows(), null, 2);
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
  }, [exportRows, exportFileName]);

  const filtersApplied =
    Boolean(searchTerm) || Object.values(filterValues).some(Boolean);

  return (
    <div className="flex-1 overflow-y-auto px-2 space-y-4">
      <div className="space-y-3">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap items-center gap-2 w-full">
            <div className="flex items-center gap-2 w-full lg:w-auto">
              <div className="relative flex-1">
                <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                  <FaSearch className="w-4 h-4 text-gray-400" />
                </div>
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder={searchPlaceholder}
                  className="w-full pl-10 pr-10 py-2.5 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white dark:placeholder-gray-400"
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
              {enableDatabaseSearch && (
                <label className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400 whitespace-nowrap cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={effectiveSearchDatabase}
                    onChange={(e) =>
                      setEffectiveSearchDatabase(e.target.checked)
                    }
                    className="w-3.5 h-3.5 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 cursor-pointer"
                  />
                  <span>Query DB</span>
                </label>
              )}
            </div>

            {customActions}

            {enableExport && (
              <div className="relative">
                <button
                  onClick={() => setShowExportDropdown((v) => !v)}
                  className="flex items-center gap-2 px-3 py-2 text-xs font-medium transition-colors text-white bg-green-600 rounded-lg hover:bg-green-700"
                >
                  <FaDownload className="w-4 h-4" />
                  Export
                </button>
                {showExportDropdown && (
                  <div className="absolute z-20 mt-2 w-56 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
                    <div className="py-1">
                      <div className="px-4 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                        Export Data
                      </div>
                      <button
                        onClick={() => {
                          exportToExcel();
                          setShowExportDropdown(false);
                        }}
                        className="flex items-center gap-3 w-full px-4 py-2 text-xs text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                      >
                        <FaFileExcel className="w-4 h-4 text-green-600" />
                        Excel ({dataToRender.length} rows)
                      </button>
                      <button
                        onClick={() => {
                          exportToPDF();
                          setShowExportDropdown(false);
                        }}
                        className="flex items-center gap-3 w-full px-4 py-2 text-xs text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                      >
                        <FaFilePdf className="w-4 h-4 text-red-600" />
                        PDF ({dataToRender.length} rows)
                      </button>
                      <button
                        onClick={() => {
                          exportToJSON();
                          setShowExportDropdown(false);
                        }}
                        className="flex items-center gap-3 w-full px-4 py-2 text-xs text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                      >
                        <FaFileCode className="w-4 h-4 text-blue-600" />
                        JSON ({dataToRender.length} rows)
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {filters.length > 0 && (
              <button
                onClick={() => setShowFilters((v) => !v)}
                className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium rounded-lg transition-colors ${
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

            {filtersApplied && (
              <button
                onClick={() => {
                  setSearchTerm("");
                  setFilterValues({});
                }}
                className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
              >
                <FaTimes className="w-4 h-4" />
                Clear
              </button>
            )}
          </div>
        </div>

        {showFilters && filters.length > 0 && (
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

        <div className="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 text-xs text-gray-600 dark:text-gray-400">
          <div className="flex items-center gap-4">
            <span className="font-medium">
              Total:{" "}
              <span className="text-gray-900 dark:text-gray-100">
                {dataProp.length}
              </span>
            </span>
            {dataToRender.length !== dataProp.length && (
              <span className="font-medium">
                Filtered:{" "}
                <span className="text-blue-600 dark:text-blue-400">
                  {dataToRender.length}
                </span>
              </span>
            )}
            {loading && <span className="text-amber-600">Loading...</span>}
          </div>
        </div>
      </div>

      {dataToRender && dataToRender.length > 0 ? (
        dataToRender.map((contact, index) => (
          <AccordionItem
            key={contact.id}
            title={`[id: ${contact.id}]  ${
              (contact.path ?? "--").length > 40
                ? `${(contact.path ?? "--").slice(0, 40)}...`
                : contact.path ?? "--"
            }`}
            isOpen={openIndex === index}
            onToggle={() => {
              const willOpen = openIndex !== index;
              setOpenIndex(willOpen ? index : null);

              if (willOpen) {
                handleView(contact);
              }
            }}
          >
            <div className="flex flex-col min-h-auto">
              <div className="space-y-1 text-sm border-t">
                <p>
                  <strong>contact:</strong>{" "}
                  {contact?.refs?.links?.contact?.[0]?.contact?.display_name
                    ? `[id: ${contact?.refs?.links?.contact?.[0]?.contact?.id}] ${contact?.refs?.links?.contact?.[0]?.contact?.display_name}`
                    : "--"}
                </p>
                <p>
                  <strong>path:</strong> {contact.path || "--"}
                </p>
                <p>
                  <strong>type:</strong> {contact.type || "--"}
                </p>
              </div>
            </div>
          </AccordionItem>
        ))
      ) : (
        <p className="text-center text-gray-500">
          {emptyMessage ?? "No domain found."}
        </p>
      )}
    </div>
  );
}
