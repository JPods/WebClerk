import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, { type AdvancedDataTableHandle } from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo, useRef} from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchExchangeTransactions } from "../services/exchangeTransactionApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import ExchangeTransactionDetail from "./ExchangeTransactionDetail";
import ButtonToolbar from "@/components/common/ButtonToolbar";

export default function ExchangeTransactionList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedExchangeTransaction, setSelectedExchangeTransaction] = useState<any | null>(null);
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

  const getExchangeTransactionData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchExchangeTransactions();
      if (res.status === 200) {
        setData(res.data.items);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch exchange transactions", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch exchange transactions", error);
      dispatch(showToast({ message: "Failed to fetch exchange transactions", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getExchangeTransactionData();
  }, [getExchangeTransactionData]);

  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    try {
      setLoading(true);
      const searchQuery = terms.join(",");
      const res = await fetchExchangeTransactions({ search: searchQuery });
      if (res.status === 200) {
        setData(res.data.items || res.data || []);
      }
    } catch (error) {
      console.error("Database search failed:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleView = (row: any) => {
    setSelectedExchangeTransaction(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedExchangeTransaction(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedExchangeTransaction(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getExchangeTransactionData();
    setFormMode(null);
    setSelectedExchangeTransaction(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedExchangeTransaction(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete exchange transaction ${row.id}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(showToast({ message: "Exchange Transaction deleted successfully", type: "success" }));
        getExchangeTransactionData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete exchange transaction", type: "error" }));
      }
    }
  };

  const userColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "5%" },
    {
      name: "From Currency",
      selector: (row) => row.from_currency || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "To Currency",
      selector: (row) => row.to_currency || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Amount",
      selector: (row) => row.amount || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Rate",
      selector: (row) => row.rate || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Date",
      selector: (row) => row.date || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Status",
      selector: (row) => row.status || "--",
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
  return (
    <>
      <ButtonToolbar
        pageTitle="Exchange Transaction List"
        title="Exchange Transaction"
        modelKey="exchange_transaction"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={getExchangeTransactionData}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={userColumns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="exchange_transaction-list"
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
                Add Exchange Transaction
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
                storageKey="exchange_transaction_list"
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
            <ExchangeTransactionDetail
              inline
              modeProp={formMode}
              dataProp={selectedExchangeTransaction}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}