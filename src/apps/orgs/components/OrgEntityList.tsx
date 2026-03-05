import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import ComponentCard from "@/components/common/ComponentCard";
import ErrorBoundary from "@/components/common/ErrorBoundary";
import AdvancedDataTable, {
  ColumnFilter,
} from "@/components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useRef } from "react";
import {
  FaSearch,
  FaPlus,
  FaTrash,
  FaDownload,
  FaEdit,
  FaFileImport,
  FaPrint,
  FaTimes,
  FaFilter,
  FaCheckSquare,
  FaGripVertical,
} from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useWindowManager } from "@/context/WindowManagerContext";

type OrgEntityRowActions<T = any> = {
  onView: (row: T) => void;
  onEdit: (row: T) => void;
  onDelete: (row: T) => void;
};

interface OrgEntityListProps<T = any> {
  modelKey: string;
  title?: string;
  fetchFn?: () => Promise<any[]>;
  deleteFn?: (id: number) => Promise<any>;
  onImportFile?: (file: File) => void;
  onPrint?: () => void;
  columns:
    | TableColumn<T>[]
    | ((actions: OrgEntityRowActions<T>) => TableColumn<T>[]);
  filters?: ColumnFilter[];
  storageKey?: string;
  exportFileName?: string;
  displayComponent?: React.ComponentType<any>;
  routes?: {
    add?: string;
    edit?: (id: any) => string;
    detail?: (id: any) => string;
  };
  /** Enable toggle between searching in current selection vs querying database */
  enableDatabaseSearch?: boolean;
  /** Current search mode: true = query database, false = search in selection */
  searchDatabase?: boolean;
  /** Callback when search mode changes */
  onSearchModeChange?: (searchDatabase: boolean) => void;
  /** Callback to perform database search with parsed terms */
  onDatabaseSearch?: (terms: string[]) => Promise<void> | void;
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
  enableDatabaseSearch,
  searchDatabase,
  onSearchModeChange,
  onDatabaseSearch,
}: OrgEntityListProps<T>) {
  const dispatch = useDispatch();
  const { ensureWindow, activateWindow } = useWindowManager();
  const [data, setData] = useState<T[]>([]);
  const [selectedRows, setSelectedRows] = useState<T[]>([]);
  const [selectedRow, setSelectedRow] = useState<any | null>(null);
  const [detailMode, setDetailMode] = useState<"view" | "edit" | "add">("view");
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const tableRef = useRef<any>(null);
  const columnBtnRef = useRef<HTMLButtonElement>(null!);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const importInputRef = useRef<HTMLInputElement>(null!);

  const getData = useCallback(async () => {
    setLoading(true);
    try {
      if (fetchFn) {
        const res = await fetchFn();
        // Try to unwrap common API shapes
        const results = Array.isArray(res)
          ? res
          : res?.data?.data?.results ||
            res?.data?.items ||
            res?.data?.results ||
            res?.results ||
            res?.items ||
            [];
        setData(results);
      }
    } catch (error) {
      console.error(`Failed to fetch ${modelKey}`, error);
      dispatch(
        showToast({
          message: `Failed to fetch ${title || modelKey}`,
          type: "error",
        }),
      );
    } finally {
      setLoading(false);
    }
  }, [fetchFn, modelKey, dispatch, title]);

  useEffect(() => {
    getData();
  }, [getData]);

  const handleRowDoubleClick = useCallback((row: any) => {
    // Double-click opens inline edit mode (not floating window)
    setSelectedRow(row);
    setDetailMode("edit");
  }, []);

  const handleEdit = useCallback(
    (row: any) => {
      if (!routes?.edit) return;
      const id = row.id;
      const path = routes.edit(id);
      const display = `Edit ${
        row.display_name || row.name || `${title || modelKey} ${id}`
      }`;
      ensureWindow(path, display, { maximized: false });
      activateWindow(path);
    },
    [ensureWindow, activateWindow, routes, modelKey, title],
  );

  const handleViewInline = useCallback((row: any) => {
    setSelectedRow(row);
    setDetailMode("view");
  }, []);

  const handleEditInline = useCallback((row: any) => {
    setSelectedRow(row);
    setDetailMode("edit");
  }, []);

  const handleAddInline = useCallback(() => {
    setSelectedRow({});
    setDetailMode("add");
  }, []);

  const handleDeleteInline = useCallback(
    async (row: any) => {
      if (!deleteFn) return;
      const display =
        row.display_name || row.name || `${title || modelKey} ${row.id}`;
      if (!window.confirm(`Delete ${display}?`)) return;
      try {
        await deleteFn(row.id);
        dispatch(
          showToast({
            message: `${title || modelKey} deleted`,
            type: "success",
          }),
        );
        getData();
        setSelectedRow(null);
      } catch (e) {
        dispatch(
          showToast({ message: "Failed to delete record", type: "error" }),
        );
      }
    },
    [deleteFn, dispatch, getData, modelKey, title],
  );

  const resolvedColumns =
    typeof columns === "function"
      ? columns({
          onView: handleViewInline,
          onEdit: handleEditInline,
          onDelete: handleDeleteInline,
        })
      : columns;

  const handleAdd = useCallback(() => {
    if (!routes?.add) return;
    const path = routes.add;
    ensureWindow(path, `Add ${title || modelKey}`, { maximized: false });
    activateWindow(path);
  }, [ensureWindow, activateWindow, routes, modelKey, title]);

  const handleBulkDelete = useCallback(
    async (rows?: any[]) => {
      const targetRows = rows && rows.length ? rows : selectedRows;
      if (!targetRows.length || !deleteFn) return;
      if (
        !window.confirm(`Delete ${targetRows.length} ${title || modelKey}(s)?`)
      )
        return;

      try {
        await Promise.all(targetRows.map((r) => deleteFn((r as any).id)));
        dispatch(
          showToast({
            message: `${targetRows.length} ${title || modelKey}(s) deleted`,
            type: "success",
          }),
        );
        getData();
        setSelectedRows([]);
      } catch (e) {
        dispatch(
          showToast({
            message: "Failed to delete some records",
            type: "error",
          }),
        );
      }
    },
    [selectedRows, deleteFn, dispatch, getData, modelKey, title],
  );

  return (
    <>
      {/* <PageBreadcrumb
        pageTitle={title || modelKey}
        handleAddInline={handleAddInline}
      /> */}
      <PageBreadcrumb
        pageTitle={title || modelKey}
        title={title}
        modelKey={modelKey}
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAddInline}
        handleBulkDelete={() => handleBulkDelete()}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        selectedRows={selectedRows}
        onPrint={onPrint}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={selectedRow ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <ErrorBoundary>
              <AdvancedDataTable
                data={data}
                columns={resolvedColumns}
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
                onRowActivate={handleViewInline}
                onRowDoubleClicked={handleRowDoubleClick}
                onRowClicked={(row: any) => {
                  setSelectedRow(row);
                  setDetailMode("view");
                }}
                onAdd={handleAddInline}
                onDeleteSelected={() => handleBulkDelete()}
                noDataMessage={`No ${title || modelKey} found`}
                enableDatabaseSearch={enableDatabaseSearch}
                searchDatabase={searchDatabase}
                onSearchModeChange={onSearchModeChange}
                onDatabaseSearch={onDatabaseSearch}
              />
            </ErrorBoundary>
          </ComponentCard>
        </div>

        {selectedRow && (
          <div className="lg:col-span-2">
            <ComponentCard>
              {DisplayComponent ? (
                <DisplayComponent
                  inline={true}
                  dataProp={selectedRow}
                  modeProp={detailMode}
                  onSaved={getData}
                  onCancelInline={() => setSelectedRow(null)}
                  onClose={() => setSelectedRow(null)}
                />
              ) : (
                <pre className="p-4">
                  {JSON.stringify(selectedRow, null, 2)}
                </pre>
              )}
            </ComponentCard>
          </div>
        )}
      </div>
    </>
  );
}
