import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, { type AdvancedDataTableHandle } from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useRef} from "react";
import { fetchGLAccounts, deleteGLAccount } from "../services/glAccountApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import GLAccountDetail from "./GLAccountDetail";
import ButtonToolbar from "@/components/common/ButtonToolbar";

export default function GLAccountList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedGLAccount, setSelectedGLAccount] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState<boolean[]>([]);
  const tableRef = useRef<AdvancedDataTableHandle<any>>(null);
  const columnBtnRef = useRef<HTMLButtonElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  const dispatch = useDispatch();

  const getGLAccountData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchGLAccounts();
      if (res.status === 200) {
        // Extract array from various response structures
        // WCAPI standard: data.results, legacy: data.items, or direct array
        const responseData = res.data;
        let items: any[] = [];
        if (Array.isArray(responseData)) {
          items = responseData;
        } else if (responseData?.data?.results && Array.isArray(responseData.data.results)) {
          items = responseData.data.results;
        } else if (responseData?.results && Array.isArray(responseData.results)) {
          items = responseData.results;
        } else if (responseData?.items && Array.isArray(responseData.items)) {
          items = responseData.items;
        } else if (responseData?.data && Array.isArray(responseData.data)) {
          items = responseData.data;
        }
        console.log('[GLAccountList] Loaded', items.length, 'accounts');
        setData(items);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch gl accounts", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch gl accounts", error);
      dispatch(showToast({ message: "Failed to fetch gl accounts", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getGLAccountData();
  }, [getGLAccountData]);

  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    try {
      setLoading(true);
      const searchQuery = terms.join(",");
      const res = await fetchGLAccounts({ search: searchQuery });
      if (res.status === 200) {
        const responseData = res.data;
        let items: any[] = [];
        if (Array.isArray(responseData)) {
          items = responseData;
        } else if (responseData?.data?.results && Array.isArray(responseData.data.results)) {
          items = responseData.data.results;
        } else if (responseData?.results && Array.isArray(responseData.results)) {
          items = responseData.results;
        } else if (responseData?.items && Array.isArray(responseData.items)) {
          items = responseData.items;
        } else if (responseData?.data && Array.isArray(responseData.data)) {
          items = responseData.data;
        }
        setData(items);
      }
    } catch (error) {
      console.error("Database search failed:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleView = (row: any) => {
    setSelectedGLAccount(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedGLAccount(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedGLAccount(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getGLAccountData();
    setFormMode(null);
    setSelectedGLAccount(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedGLAccount(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete gl account ${row.code}?`)) {
      try {
        await deleteGLAccount(row.id);
        dispatch(showToast({ message: "GL Account deleted successfully", type: "success" }));
        getGLAccountData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete gl account", type: "error" }));
      }
    }
  };

  // Columns for GL Account table
  const userColumns: TableColumn<any>[] = [
    { name: "Account #", selector: (row) => row.account_number || row.code || "--", sortable: true, width: "15%" },
    { name: "Name", selector: (row) => row.name || "--", sortable: true, width: "25%" },
    { name: "Type", selector: (row) => row.type || "--", sortable: true, width: "12%" },
    { name: "Category", selector: (row) => row.category || "--", sortable: true, width: "12%" },
    { name: "Division", selector: (row) => row.division || "--", sortable: true, width: "10%" },
    { name: "Used For", selector: (row) => row.used_for || "--", sortable: true, width: "13%" },
    { 
      name: "Balance", 
      selector: (row) => row.balance ?? 0, 
      sortable: true, 
      width: "13%",
      right: true,
      format: (row) => (row.balance != null ? Number(row.balance).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "0.00"),
    },
  ];

  userColumns.push({
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
  });

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
    if (columnVisibility.length === 0) return columns;
    return columns.filter((_: any, index: number) => columnVisibility[index] !== false);
  }, [columns, columnVisibility]);
  return (
    <>
      <ButtonToolbar
        pageTitle="GL Account List"
        title="GL Account"
        modelKey="gl_account"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={getData}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={columns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="gl_account-list"
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
                Add GL Account
              </button>
            </div>
            <div className="overflow-x-auto bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-400 rounded-md">
              <AdvancedDataTable
              ref={tableRef}
                columns={userColumns.map((col) => ({
                  ...col,
                  name: typeof col.name === "string" ? col.name.toUpperCase() : col.name,
                }))}
                data={filteredData}
                storageKey="gl_account_list"
                loading={loading}
                onRowActivate={handleEdit}
                rowKeyField="id"
                enableDatabaseSearch={true}
                searchDatabase={searchDatabase}
                onSearchModeChange={setSearchDatabase}
                onDatabaseSearch={handleDatabaseSearch}
              
              externalSearchTerm={searchTerm}
              onExternalSearchTermChange={setSearchTerm}
              hideHeader={true}/>
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <GLAccountDetail
              inline
              modeProp={formMode}
              dataProp={selectedGLAccount}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}