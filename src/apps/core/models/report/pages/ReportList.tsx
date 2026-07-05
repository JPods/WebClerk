/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import DataGrid from "@/components/common/DataGrid";
import ComponentCard from "../../../../../components/common/ComponentCard";
import { useEffect, useState, useCallback, useMemo, useRef} from "react";
import { fetchReports, deleteReport } from "../services/reportApi";
import { FaEye, FaEdit, FaTrash, FaPlus } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import ReportDetail from "./ReportDetail";
import Badge from "../../../../../components/ui/badge/Badge";
import ButtonToolbar from "@/components/common/ButtonToolbar";
import { useColumnContextMenu } from "@/hooks/useColumnContextMenu";

export default function ReportList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedReport, setSelectedReport] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [searchDatabase, setSearchDatabase] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState<boolean[]>([]);
  const tableRef = useRef<any>(null);
  const columnBtnRef = useRef<HTMLButtonElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  const dispatch = useDispatch();

  const getReportData = useCallback(async () => {
    try {
      const res = await fetchReports();
      if (res.status === 200) {
        setData(res.data.items);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch reports", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch reports", error);
    }
  }, [dispatch]);

  useEffect(() => {
    getReportData();
  }, [getReportData]);

  // Handle database search
  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    const query = terms.join(' ');
    try {
      const res = await fetchReports(undefined, { search: query });
      if (res.status === 200) {
        setData(res.data.items);
      }
    } catch (error) {
      console.error("Database search error:", error);
      dispatch(showToast({ message: "Search failed", type: "error" }));
    }
  }, [dispatch]);

  const handleView = (row: any) => {
    setSelectedReport(row);
    setFormMode("view");
  };

  const handleEdit = async (row: any) => {
    const res = await fetchReports(row.id);
    if (res.status === 200) setSelectedReport(res.data.item);
    else setSelectedReport(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedReport(null);
    setFormMode("add");
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete report ${row.title}?`)) {
      try {
        await deleteReport(row.id);
        dispatch(
          showToast({
            message: "Report deleted successfully",
            type: "success",
          })
        );
        getReportData(); // Refresh data
        if (selectedReport && selectedReport.id === row.id) {
          setFormMode(null);
          setSelectedReport(null);
        }
      } catch {
        dispatch(
          showToast({
            message: "Failed to delete report",
            type: "error",
          })
        );
      }
    }
  };

  const handleFormSaved = () => {
    getReportData();
    setFormMode(null);
    setSelectedReport(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedReport(null);
  };

  const userColumns: any[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "5%" },
    {
      name: "Title",
      selector: (row) => row.title || "--",
      sortable: true,
      width: "20%",
    },
    {
      name: "Type",
      selector: (row) => row.type || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Description",
      selector: (row) => row.description || "--",
      sortable: true,
      width: "30%",
    },
    {
      name: "Is Active",
      selector: (row) => (row.is_active ? "Active" : "Inactive"),
      cell: (row) => (
        <>
          <Badge size="sm" color={row.is_active ? "success" : "warning"}>
            {row.is_active ? "Active" : "Inactive"}
          </Badge>
        </>
      ),
      sortable: true,
      width: "10%",
    },
    {
      name: "Action",
      cell: (row) => (
        <div className="flex gap-2">
          <button onClick={() => handleView(row)} title="View">
            <FaEye className="text-blue-600 hover:scale-110 transition" />
          </button>
          <button onClick={() => handleEdit(row)} title="Edit">
            <FaEdit className="text-green-600 hover:scale-110 transition" />
          </button>
          <button onClick={() => handleDelete(row)} title="Delete">
            <FaTrash className="text-red-600 hover:scale-110 transition" />
          </button>
        </div>
      ),
      ignoreRowClick: true,
      allowOverflow: true,
      button: true,
    },
  ];

  // Filter data based on filterValues from ButtonToolbar
  const filteredData = useMemo(() => {
    if (Object.keys(filterValues).length === 0) return data;
    return data.filter((row: any) => {
      return Object.entries(filterValues).every(([key, value]) => {
        if (!value) return true;
        const rowValue = String(row[key] || "").toLowerCase();
        return rowValue.includes(value.toLowerCase());
      });
    });
  }, [data, filterValues]);

  // Filter columns based on visibility from ButtonToolbar
  const visibleColumns = useMemo(() => {
    if (columnVisibility.length === 0) return userColumns;
    return userColumns.filter((_: any, index: number) => columnVisibility[index] !== false);
  }, [userColumns, columnVisibility]);

  const columnCtx = useColumnContextMenu("report_list", userColumns);
  return (
    <>
      <ButtonToolbar
        pageTitle="Report List"
        title="Report"
        modelKey="report"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={getReportData}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={userColumns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="report-list"
        filterValues={filterValues}
        onFilterValuesChange={setFilterValues}
        filtersOpen={filtersOpen}
        onFiltersOpenChange={setFiltersOpen}
      />
<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Report
              </button>
            </div>
            <DataGrid
              ref={tableRef}
              columns={userColumns}
              data={filteredData}
              storageKey="report_list"
              onRowActivate={handleEdit}
              enableDatabaseSearch={true}
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
            
              externalSearchTerm={searchTerm}
              onExternalSearchTermChange={setSearchTerm}
              allFields={columnCtx.allFields}
              namedViews={columnCtx.namedViews}
              onDeleteColumn={columnCtx.onDeleteColumn}
              onAddColumn={columnCtx.onAddColumn}
              onSaveLayout={columnCtx.onSaveLayout}
              onSaveLayoutAs={columnCtx.onSaveLayoutAs}
              onLoadView={columnCtx.onLoadView}
              hideHeader={true}/>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <ReportDetail
              inline
              modeProp={formMode}
              dataProp={selectedReport}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}