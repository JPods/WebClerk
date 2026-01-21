import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import ComponentCard from "@/components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter } from "@/components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { getRecords, deleteRecord } from "@/api/wcapi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import LedgerDisplay from "./LedgerDisplay";

export default function LedgerList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedLedger, setSelectedLedger] = useState<any | null>(null);
  const [selectedLedgers, setSelectedLedgers] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const getLedgerData = useCallback(async () => {
    try {
      setLoading(true);
      const list = await getRecords('ledger');
      const recs = Array.isArray(list?.results) ? list.results : Array.isArray(list) ? list : [];
      setData(recs);
    } catch (error) {
      console.error("Failed to fetch ledgers", error);
      dispatch(showToast({ message: "Failed to fetch ledgers", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getLedgerData();
  }, [getLedgerData]);

  const handleView = useCallback((row: any) => {
    setSelectedLedger(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback((row: any) => {
    setSelectedLedger(row);
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedLedger(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getLedgerData();
    setFormMode(null);
    setSelectedLedger(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedLedger(null);
  };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete ledger ${row.name || row.id}?`)) return;
    
    try {
      await deleteRecord('ledger', row.id);
      dispatch(showToast({ message: "Ledger deleted successfully", type: "success" }));
      getLedgerData();
      if (selectedLedger && selectedLedger.id === row.id) {
        setFormMode(null);
        setSelectedLedger(null);
      }
    } catch {
      dispatch(showToast({ message: "Failed to delete ledger", type: "error" }));
    }
  }, [dispatch, getLedgerData, selectedLedger]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedLedgers.length) return;
    if (!window.confirm(`Delete ${selectedLedgers.length} ledger(s)?`)) return;

    try {
      await Promise.all(selectedLedgers.map((l) => deleteRecord('ledger', l.id)));
      dispatch(showToast({ message: `${selectedLedgers.length} ledger(s) deleted`, type: "success" }));
      getLedgerData();
      setSelectedLedgers([]);
    } catch {
      dispatch(showToast({ message: "Failed to delete some ledgers", type: "error" }));
    }
  }, [selectedLedgers, dispatch, getLedgerData]);

  const filters: ColumnFilter[] = useMemo(() => [
    { key: "type", label: "Type", type: "text" },
  ], []);

  const columns: TableColumn<any>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "name", name: "Name", selector: (row) => row.name || "--", sortable: true, width: "30%" },
    { id: "type", name: "Type", selector: (row) => row.type || "--", sortable: true, width: "25%" },
    { id: "balance", name: "Balance", selector: (row) => row.balance || "--", sortable: true, width: "20%" },
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
      <PageBreadcrumb pageTitle="Ledger List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="Ledgers"
              loading={loading}
              filters={filters}
              storageKey="ledger-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedLedgers}
              exportFileName="ledgers_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search ledgers..."
              noDataMessage="No ledgers found"
              customActions={
                <div className="flex gap-2">
                  {selectedLedgers.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" />
                      Delete ({selectedLedgers.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Ledger
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <LedgerDisplay
              inline
              modeProp={formMode}
              dataProp={selectedLedger}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
