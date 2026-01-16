import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { fetchSerials, deleteSerial } from "../services/serialApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import SerialDetail from "./SerialDetail";

export default function SerialList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedSerial, setSelectedSerial] = useState<any | null>(null);
  const [selectedItems, setSelectedItems] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const getData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchSerials();
      if (res.status === 200) {
        setData(res.data?.items || res.data?.data?.results || []);
      } else {
        dispatch(showToast({ message: "Failed to fetch serials", type: "error" }));
      }
    } catch (error) {
      dispatch(showToast({ message: "Failed to fetch serials", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => { getData(); }, [getData]);

  const handleView = useCallback((row: any) => { setSelectedSerial(row); setFormMode("view"); }, []);
  const handleEdit = useCallback((row: any) => { setSelectedSerial(row); setFormMode("edit"); }, []);
  const handleAdd = () => { setSelectedSerial(null); setFormMode("add"); };
  const handleFormSaved = () => { getData(); setFormMode(null); setSelectedSerial(null); };
  const handleFormCancel = () => { setFormMode(null); setSelectedSerial(null); };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete serial ${row.serial_number || row.id}?`)) return;
    try {
      await deleteSerial(row.id);
      dispatch(showToast({ message: "Serial deleted successfully", type: "success" }));
      getData();
    } catch { dispatch(showToast({ message: "Failed to delete serial", type: "error" })); }
  }, [dispatch, getData]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedItems.length || !window.confirm(`Delete ${selectedItems.length} serial(s)?`)) return;
    try {
      await Promise.all(selectedItems.map((item) => deleteSerial(item.id)));
      dispatch(showToast({ message: `${selectedItems.length} serial(s) deleted`, type: "success" }));
      getData(); setSelectedItems([]);
    } catch { dispatch(showToast({ message: "Failed to delete some serials", type: "error" })); }
  }, [selectedItems, dispatch, getData]);

  const columns: TableColumn<any>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "serial_number", name: "Serial Number", selector: (row) => row.serial_number || "--", sortable: true },
    { id: "item_id", name: "Item ID", selector: (row) => row.item_id || "--", sortable: true },
    { id: "status", name: "Status", selector: (row) => row.status || "--", sortable: true, width: "120px" },
    { id: "description", name: "Description", selector: (row) => row.description || "--", sortable: true },
    {
      id: "actions",
      name: "Actions",
      cell: (row) => (
        <div className="flex gap-2">
          <button onClick={() => handleView(row)} title="View"><FaEye className="text-blue-600 hover:scale-110 transition" /></button>
          <button onClick={() => handleEdit(row)} title="Edit"><FaEdit className="text-green-600 hover:scale-110 transition" /></button>
          <button onClick={() => handleDelete(row)} title="Delete"><FaTrash className="text-red-600 hover:scale-110 transition" /></button>
        </div>
      ),
      ignoreRowClick: true, allowOverflow: true, button: true, width: "100px",
    },
  ], [handleDelete, handleEdit, handleView]);

  return (
    <>
      <PageBreadcrumb pageTitle="Serial List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="Serials"
              loading={loading}
              storageKey="serial-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedItems}
              exportFileName="serial_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search serials..."
              noDataMessage="No serials found"
              customActions={
                <div className="flex gap-2">
                  {selectedItems.length > 0 && (
                    <button onClick={handleBulkDelete} className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors">
                      <FaTrash className="w-4 h-4" /> Delete ({selectedItems.length})
                    </button>
                  )}
                  <button onClick={handleAdd} className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors">
                    <FaPlus className="w-4 h-4" /> Add Serial
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <SerialDetail inline modeProp={formMode} dataProp={selectedSerial} onSaved={handleFormSaved} onCancelInline={handleFormCancel} />
          </div>
        )}
      </div>
    </>
  );
}