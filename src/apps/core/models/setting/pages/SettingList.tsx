/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import DataGrid from "@/components/common/DataGrid";
import ComponentCard from "../../../../../components/common/ComponentCard";
import { useEffect, useState, useCallback, useMemo, useRef} from "react";
import { fetchSettings, deleteSetting } from "../services/settingApi";
import { FaEye, FaEdit, FaPlus, FaTrashAlt } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import SettingDetail from "./SettingDetail";
import Badge from "../../../../../components/ui/badge/Badge";
import ButtonToolbar from "@/components/common/ButtonToolbar";
import { useColumnContextMenu } from "@/hooks/useColumnContextMenu";

export default function SettingList() {
  const location = useLocation();
  const routeState = (location.state as any) || {};
  const [data, setData] = useState<any[]>([]);
  const [selectedSetting, setSelectedSetting] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);
  const [searchTerm, setSearchTerm] = useState(routeState.searchTerm || "");
  const [filterValues, setFilterValues] = useState<Record<string, string>>(routeState.filterValues || {});
  const [filtersOpen, setFiltersOpen] = useState(Boolean(routeState.filtersOpen));
  const [columnVisibility, setColumnVisibility] = useState<boolean[]>([]);
  const tableRef = useRef<any>(null);
  const columnBtnRef = useRef<HTMLButtonElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  const dispatch = useDispatch();

  const getSettingData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchSettings();
      if (res.status === 200) {
        setData(res.data.items);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch settings", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch settings", error);
      dispatch(showToast({ message: "Failed to fetch settings", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getSettingData();
  }, [getSettingData]);

  useEffect(() => {
    if (routeState.searchTerm !== undefined) {
      setSearchTerm(routeState.searchTerm || "");
    }
    if (routeState.filterValues) {
      setFilterValues(routeState.filterValues);
    }
    if (routeState.filtersOpen !== undefined) {
      setFiltersOpen(Boolean(routeState.filtersOpen));
    }
  }, [routeState.filtersOpen, routeState.filterValues, routeState.searchTerm]);

  // Handle database search
  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    const query = terms.join(' ');
    setLoading(true);
    try {
      const res = await fetchSettings({ search: query });
      if (res.status === 200) {
        setData(res.data.items);
      }
    } catch (error) {
      console.error("Database search error:", error);
      dispatch(showToast({ message: "Search failed", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  const handleView = (row: any) => {
    setSelectedSetting(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedSetting(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedSetting(routeState.addDefaults || null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getSettingData();
    setFormMode(null);
    setSelectedSetting(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedSetting(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete setting ${row.name}?`)) {
      try {
        await deleteSetting(row.id);
        dispatch(showToast({ message: "Setting deleted successfully", type: "success" }));
        getSettingData(); // Refresh data
      } catch {
        dispatch(showToast({ message: "Failed to delete setting", type: "error" }));
      }
    }
  };

  const userColumns: any[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "5%" },
    {
      name: "Name",
      selector: (row) => row.name || "--",
      sortable: true,
      width: "20%",
    },
    {
      name: "Purpose",
      selector: (row) => row.purpose || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Role",
      selector: (row) => row.role || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Model Target",
      selector: (row) => row.parent_model || "--",
      sortable: true,
      width: "15%",
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
            <FaTrashAlt className="text-red-600 hover:scale-110 transition" />
          </button>
        </div>
      ),
      ignoreRowClick: true,
      allowOverflow: true,
      button: true,
    },
  ];

  const filters = useMemo(
    () => [
      { key: "name", label: "Name", type: "text" },
      { key: "purpose", label: "Purpose", type: "text" },
      { key: "parent_model", label: "Parent Model", type: "text" },
      { key: "role", label: "Role", type: "text" },
    ],
    [],
  );

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

  const columnCtx = useColumnContextMenu("setting_list", userColumns);
  return (
    <>
      <ButtonToolbar
        pageTitle="Setting List"
        title="Setting"
        modelKey="setting"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={getSettingData}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={userColumns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="setting-list"
        filters={filters}
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
                {filterValues.purpose === "search" ? "Add Search" : "Add Setting"}
              </button>
            </div>
            <DataGrid
              ref={tableRef}
              columns={userColumns}
              data={filteredData}
              storageKey="setting_list"
              loading={loading}
              filters={filters}
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
            <SettingDetail
              inline
              modeProp={formMode}
              dataProp={selectedSetting}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}