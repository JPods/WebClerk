import PageBreadcrumb from "../../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../../components/common/ComponentCard";
import AdvancedDataTable from "../../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { fetchServices, deleteService } from "../services/serviceApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import ServiceDetail from "./ServiceDetail";

export default function ServiceList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedService, setSelectedService] = useState<any | null>(null);
  const [selectedItems, setSelectedItems] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const getData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchServices();
      if (res.status === 200) {
        setData(res.data?.items || res.data?.data?.results || []);
      } else {
        dispatch(showToast({ message: "Failed to fetch services", type: "error" }));
      }
    } catch (error) {
      dispatch(showToast({ message: "Failed to fetch services", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => { getData(); }, [getData]);

  const handleView = useCallback((row: any) => { setSelectedService(row); setFormMode("view"); }, []);
  const handleEdit = useCallback((row: any) => { setSelectedService(row); setFormMode("edit"); }, []);
  const handleAdd = () => { setSelectedService(null); setFormMode("add"); };
  const handleFormSaved = () => { getData(); setFormMode(null); setSelectedService(null); };
  const handleFormCancel = () => { setFormMode(null); setSelectedService(null); };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete service ${row.name || row.id}?`)) return;
    try {
      await deleteService(row.id);
      dispatch(showToast({ message: "Service deleted successfully", type: "success" }));
      getData();
    } catch { dispatch(showToast({ message: "Failed to delete service", type: "error" })); }
  }, [dispatch, getData]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedItems.length || !window.confirm(`Delete ${selectedItems.length} service(s)?`)) return;
    try {
      await Promise.all(selectedItems.map((item) => deleteService(item.id)));
      dispatch(showToast({ message: `${selectedItems.length} service(s) deleted`, type: "success" }));
      getData(); setSelectedItems([]);
    } catch { dispatch(showToast({ message: "Failed to delete some services", type: "error" })); }
  }, [selectedItems, dispatch, getData]);

  const columns: TableColumn<any>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "name", name: "Name", selector: (row) => row.name || "--", sortable: true },
    { id: "description", name: "Description", selector: (row) => row.description || "--", sortable: true },
    { id: "cost", name: "Cost", selector: (row) => row.cost || "--", sortable: true, width: "120px" },
    { id: "date", name: "Date", selector: (row) => row.date || "--", sortable: true, width: "120px" },
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
      <PageBreadcrumb pageTitle="Service List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="Services"
              loading={loading}
              storageKey="service-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedItems}
              exportFileName="service_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search services..."
              noDataMessage="No services found"
              customActions={
                <div className="flex gap-2">
                  {selectedItems.length > 0 && (
                    <button onClick={handleBulkDelete} className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors">
                      <FaTrash className="w-4 h-4" /> Delete ({selectedItems.length})
                    </button>
                  )}
                  <button onClick={handleAdd} className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors">
                    <FaPlus className="w-4 h-4" /> Add Service
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <ServiceDetail inline modeProp={formMode} dataProp={selectedService} onSaved={handleFormSaved} onCancelInline={handleFormCancel} />
          </div>
        )}
      </div>
    </>
  );
}