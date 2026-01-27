import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import ComponentCard from "@/components/common/ComponentCard";
import ErrorBoundary from "@/components/common/ErrorBoundary";
import AdvancedDataTable, { ColumnFilter } from "@/components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useRef } from "react";
import { FaSearch, FaPlus, FaTrash, FaDownload, FaEdit, FaFileImport, FaPrint, FaTimes, FaFilter, FaCheckSquare, FaGripVertical } from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useWindowManager } from "@/context/WindowManagerContext";

interface OrgEntityListProps<T = any> {
  modelKey: string;
  title?: string;
  fetchFn?: () => Promise<any[]>;
  deleteFn?: (id: number) => Promise<any>;
  onImportFile?: (file: File) => void;
  onPrint?: () => void;
  columns: TableColumn<T>[];
  filters?: ColumnFilter[];
  storageKey?: string;
  exportFileName?: string;
  displayComponent?: React.ComponentType<any>;
  routes?: {
    add?: string;
    edit?: (id: any) => string;
    detail?: (id: any) => string;
  };
}

export default function OrgEntityList<T = any>({
  modelKey,
  title,
  fetchFn,
  deleteFn,
  columns,
  filters,
  storageKey,
  exportFileName,
  displayComponent: DisplayComponent,
  routes,
  onImportFile,
  onPrint,
}: OrgEntityListProps<T>) {
  const dispatch = useDispatch();
  const { ensureWindow, activateWindow } = useWindowManager();
  const [data, setData] = useState<T[]>([]);
  const [selectedRows, setSelectedRows] = useState<T[]>([]);
  const [selectedRow, setSelectedRow] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const tableRef = useRef<any>(null);
  const columnBtnRef = useRef<HTMLButtonElement | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const importInputRef = useRef<HTMLInputElement | null>(null);

  const getData = useCallback(async () => {
    setLoading(true);
    try {
      if (fetchFn) {
        const res = await fetchFn();
        // Try to unwrap common API shapes
        const results = Array.isArray(res) ? res : res?.data?.data?.results || res?.results || [];
        setData(results);
      }
    } catch (error) {
      console.error(`Failed to fetch ${modelKey}`, error);
      dispatch(showToast({ message: `Failed to fetch ${title || modelKey}`, type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [fetchFn, modelKey, dispatch, title]);

  useEffect(() => {
    getData();
  }, [getData]);


  const handleRowDoubleClick = useCallback((row: any) => {
    if (!routes?.detail) return;
    const id = row.id;
    const path = routes.detail(id);
    const display = row.display_name || row.name || `${title || modelKey} ${id}`;
    ensureWindow(path, display, { maximized: false });
    activateWindow(path);
  }, [ensureWindow, activateWindow, routes, modelKey, title]);

  const handleEdit = useCallback((row: any) => {
    if (!routes?.edit) return;
    const id = row.id;
    const path = routes.edit(id);
    const display = `Edit ${row.display_name || row.name || `${title || modelKey} ${id}`}`;
    ensureWindow(path, display, { maximized: false });
    activateWindow(path);
  }, [ensureWindow, activateWindow, routes, modelKey, title]);

  const handleAdd = useCallback(() => {
    if (!routes?.add) return;
    const path = routes.add;
    ensureWindow(path, `Add ${title || modelKey}`, { maximized: false });
    activateWindow(path);
  }, [ensureWindow, activateWindow, routes, modelKey, title]);

  const handleBulkDelete = useCallback(async (rows?: any[]) => {
    const targetRows = rows && rows.length ? rows : selectedRows;
    if (!targetRows.length || !deleteFn) return;
    if (!window.confirm(`Delete ${targetRows.length} ${title || modelKey}(s)?`)) return;

    try {
      await Promise.all(targetRows.map((r) => deleteFn((r as any).id)));
      dispatch(showToast({ message: `${targetRows.length} ${title || modelKey}(s) deleted`, type: "success" }));
      getData();
      setSelectedRows([]);
    } catch (e) {
      dispatch(showToast({ message: "Failed to delete some records", type: "error" }));
    }
  }, [selectedRows, deleteFn, dispatch, getData, modelKey, title]);

  return (
    <>
      <PageBreadcrumb pageTitle={title || modelKey} />
      <div className="flex items-center justify-between gap-4 mb-4">
        <div className="flex items-center gap-2 flex-nowrap overflow-x-auto">
          <button
            onClick={handleAdd}
            title="Add"
            className="w-9 h-9 flex items-center justify-center rounded-md bg-blue-600 text-white hover:bg-blue-700"
          >
            <FaPlus className="w-4 h-4" />
          </button>

          <button
            onClick={() => tableRef.current?.selectAll?.()}
            title="Select All"
            className="w-9 h-9 flex items-center justify-center rounded-md bg-sky-600 text-white hover:bg-sky-700"
          >
            <FaCheckSquare className="w-4 h-4" />
          </button>

          <button
            onClick={() => tableRef.current?.clearSelection?.()}
            title="Clear Selection"
            className="w-9 h-9 flex items-center justify-center rounded-md bg-gray-100 text-gray-700 hover:bg-gray-200"
          >
            <FaTimes className="w-4 h-4" />
          </button>

          <button
            onClick={() => importInputRef.current?.click()}
            title="Import"
            className="w-9 h-9 flex items-center justify-center rounded-md bg-slate-600 text-white hover:bg-slate-700 disabled:opacity-50"
            disabled={!((window as any).File) && !Boolean(undefined)}
          >
            <FaFileImport className="w-4 h-4" />
          </button>
          <input
            ref={importInputRef}
            type="file"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) {
                if ((tableRef.current as any)?.props?.onImportFile) {
                  (tableRef.current as any).props.onImportFile(f);
                }
              }
              e.currentTarget.value = "";
            }}
          />

          <button
            onClick={() => onPrint?.()}
            disabled={!onPrint}
            title="Print"
            className="w-9 h-9 flex items-center justify-center rounded-md bg-yellow-500 text-white hover:bg-yellow-600 disabled:opacity-50"
          >
            <FaPrint className="w-4 h-4" />
          </button>

          <button
            onClick={() => tableRef.current?.exportToExcel(false)}
            title="Export"
            className="w-9 h-9 flex items-center justify-center rounded-md bg-green-600 text-white hover:bg-green-700"
          >
            <FaDownload className="w-4 h-4" />
          </button>

          <button
            onClick={() => tableRef.current?.exportToExcel(true)}
            disabled={selectedRows.length === 0}
            title="Export Selected"
            className="w-9 h-9 flex items-center justify-center rounded-md bg-green-500 text-white hover:bg-green-600 disabled:opacity-50"
          >
            <FaDownload className="w-4 h-4" />
          </button>

          <button
            ref={columnBtnRef}
            onClick={() => tableRef.current?.openColumnManager?.(columnBtnRef.current)}
            title="Columns"
            className="w-9 h-9 flex items-center justify-center rounded-md bg-gray-100 text-gray-700 hover:bg-gray-200"
          >
            <FaGripVertical className="w-4 h-4" />
          </button>
        </div>

          <div className="w-72">
          <div className="relative flex items-center">
            <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
              <FaSearch className="w-4 h-4 text-gray-400" />
            </div>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder={`Search ${title || modelKey}`}
              className="w-full pl-10 pr-3 py-2.5 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white"
            />
            <button
              onClick={() => handleBulkDelete()}
              disabled={selectedRows.length === 0}
              title="Delete"
              className="ml-2 w-9 h-9 flex items-center justify-center rounded-md bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
            >
              <FaTrash className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div>
            <ComponentCard>
              <ErrorBoundary>
                <AdvancedDataTable
                data={data}
                columns={columns}
                title={title || modelKey}
                loading={loading}
                filters={filters}
                storageKey={storageKey}
                ref={tableRef}
                hideHeader={true}
                externalSearchTerm={searchTerm}
                onExternalSearchTermChange={setSearchTerm}
                filtersOpen={filtersOpen}
                onFiltersOpenChange={setFiltersOpen}
                onImportFile={onImportFile}
                onPrint={onPrint}
                enableExport={!!exportFileName}
                enableSelection={!!deleteFn}
                onSelectionChange={setSelectedRows}
                exportFileName={exportFileName}
                onRowActivate={handleEdit}
                onRowDoubleClicked={handleRowDoubleClick}
                onRowClicked={(row: any) => setSelectedRow(row)}
                onAdd={handleAdd}
                onDeleteSelected={() => handleBulkDelete()}
                noDataMessage={`No ${title || modelKey} found`}
                />
              </ErrorBoundary>
            </ComponentCard>
          </div>

          <div>
            <ComponentCard>
              {selectedRow ? (
                DisplayComponent ? (
                  <DisplayComponent
                    inline={true}
                    dataProp={selectedRow}
                    onSaved={getData}
                    onCancelInline={() => setSelectedRow(null)}
                    onClose={() => setSelectedRow(null)}
                  />
                ) : (
                  <pre className="p-4">{JSON.stringify(selectedRow, null, 2)}</pre>
                )
              ) : (
                <div className="p-6 text-sm text-gray-500">Click a row on the left to see details here.</div>
              )}
            </ComponentCard>
          </div>
        </div>
      </div>
    </>
  );
}
