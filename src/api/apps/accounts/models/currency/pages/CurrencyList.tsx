import PageBreadcrumb from "../../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../../components/common/ComponentCard";
import AdvancedDataTable from "../../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { fetchCurrencies, deleteCurrency } from "../services/currencyApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import CurrencyDetail from "./CurrencyDetail";

export default function CurrencyList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedCurrency, setSelectedCurrency] = useState<any | null>(null);
  const [selectedCurrencies, setSelectedCurrencies] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const getCurrencyData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchCurrencies();
      if (res.status === 200) {
        setData(res.data.items || []);
      } else {
        dispatch(showToast({ message: "Failed to fetch currencies", type: "error" }));
      }
    } catch (error) {
      console.error("Failed to fetch currencies", error);
      dispatch(showToast({ message: "Failed to fetch currencies", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getCurrencyData();
  }, [getCurrencyData]);

  const handleView = useCallback((row: any) => {
    setSelectedCurrency(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback((row: any) => {
    setSelectedCurrency(row);
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedCurrency(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getCurrencyData();
    setFormMode(null);
    setSelectedCurrency(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedCurrency(null);
  };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete currency ${row.code}?`)) return;
    
    try {
      await deleteCurrency(row.id);
      dispatch(showToast({ message: "Currency deleted successfully", type: "success" }));
      getCurrencyData();
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete currency", type: "error" }));
    }
  }, [dispatch, getCurrencyData]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedCurrencies.length) return;
    if (!window.confirm(`Delete ${selectedCurrencies.length} currency(ies)?`)) return;

    try {
      await Promise.all(selectedCurrencies.map((c) => deleteCurrency(c.id)));
      dispatch(showToast({ message: `${selectedCurrencies.length} currency(ies) deleted`, type: "success" }));
      getCurrencyData();
      setSelectedCurrencies([]);
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete some currencies", type: "error" }));
    }
  }, [selectedCurrencies, dispatch, getCurrencyData]);

  const columns: TableColumn<any>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "code", name: "Code", selector: (row) => row.code || "--", sortable: true, width: "15%" },
    { id: "name", name: "Name", selector: (row) => row.name || "--", sortable: true, width: "25%" },
    { id: "symbol", name: "Symbol", selector: (row) => row.symbol || "--", sortable: true, width: "15%" },
    { id: "rate", name: "Rate", selector: (row) => row.rate || "--", sortable: true, width: "15%" },
    {
      id: "actions",
      name: "Actions",
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
      width: "100px",
    },
  ], [handleDelete, handleEdit, handleView]);

  return (
    <>
      <PageBreadcrumb pageTitle="Currency List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="Currencies"
              loading={loading}
              storageKey="currency-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedCurrencies}
              exportFileName="currencies_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search currencies..."
              noDataMessage="No currencies found"
              customActions={
                <div className="flex gap-2">
                  {selectedCurrencies.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" />
                      Delete ({selectedCurrencies.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Currency
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <CurrencyDetail
              inline
              modeProp={formMode}
              dataProp={selectedCurrency}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
