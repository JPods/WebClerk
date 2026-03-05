import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, { type AdvancedDataTableHandle } from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useRef} from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchPurchaseLines } from "../services/purchaseLineApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import PurchaseLineDetail from "./PurchaseLineDetail";
import ButtonToolbar from "@/components/common/ButtonToolbar";

export default function PurchaseLineList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedPurchaseLine, setSelectedPurchaseLine] = useState<any | null>(null);
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

  const getPurchaseLineData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchPurchaseLines();
      if (res.status === 200) {
        setData(res.data.items);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch purchase lines", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch purchase lines", error);
      dispatch(showToast({ message: "Failed to fetch purchase lines", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getPurchaseLineData();
  }, [getPurchaseLineData]);

  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    try {
      setLoading(true);
      const searchQuery = terms.join(",");
      const res = await fetchPurchaseLines({ search: searchQuery });
      if (res.status === 200) {
        setData(res.data.items);
      }
    } catch (error) {
      console.error("Database search failed:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleView = (row: any) => {
    setSelectedPurchaseLine(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedPurchaseLine(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedPurchaseLine(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getPurchaseLineData();
    setFormMode(null);
    setSelectedPurchaseLine(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedPurchaseLine(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete purchase line ${row.id}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(showToast({ message: "Purchase line deleted successfully", type: "success" }));
        getPurchaseLineData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete purchase line", type: "error" }));
      }
    }
  };

  const userColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "5%" },
    {
      name: "Purchase ID",
      selector: (row) => row.purchase_id || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Item ID",
      selector: (row) => row.item_id || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Quantity",
      selector: (row) => row.quantity || "--",
      sortable: true,
      width: "10%",
    },
    {
      name: "Unit Price",
      selector: (row) => row.unit_price || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Line Total",
      selector: (row) => row.line_total || "--",
      sortable: true,
      width: "15%",
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
    if (columnVisibility.length === 0) return columns;
    return columns.filter((_: any, index: number) => columnVisibility[index] !== false);
  }, [columns, columnVisibility]);
  return (
    <>
      <ButtonToolbar
        pageTitle="Purchase Line List"
        title="Purchase Line"
        modelKey="purchase_line"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={getPurchaseLineData}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={columns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="purchase_line-list"
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
                Add Purchase Line
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
                storageKey="purchase_line_list"
                onRowActivate={handleEdit}
                loading={loading}
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
            <PurchaseLineDetail
              inline
              modeProp={formMode}
              dataProp={selectedPurchaseLine}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}