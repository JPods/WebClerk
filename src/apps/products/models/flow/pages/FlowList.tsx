import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { fetchFlows, deleteFlow } from "../services/flowApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import FlowDetail from "./FlowDetail";

export default function FlowList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedFlow, setSelectedFlow] = useState<any | null>(null);
  const [selectedItems, setSelectedItems] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);

  const getData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchFlows();
      if (res.status === 200) {
        setData(res.data?.items || res.data?.data?.results || []);
      } else {
        dispatch(showToast({ message: "Failed to fetch flows", type: "error" }));
      }
    } catch (error) {
      dispatch(showToast({ message: "Failed to fetch flows", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => { getData(); }, [getData]);

  const handleView = useCallback((row: any) => { setSelectedFlow(row); setFormMode("view"); }, []);
  const handleEdit = useCallback((row: any) => { setSelectedFlow(row); setFormMode("edit"); }, []);
  const handleAdd = () => { setSelectedFlow(null); setFormMode("add"); };
  const handleFormSaved = () => { getData(); setFormMode(null); setSelectedFlow(null); };
  const handleFormCancel = () => { setFormMode(null); setSelectedFlow(null); };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete flow ${row.name || row.id}?`)) return;
    try {
      await deleteFlow(row.id);
      dispatch(showToast({ message: "Flow deleted successfully", type: "success" }));
      getData();
    } catch { dispatch(showToast({ message: "Failed to delete flow", type: "error" })); }
  }, [dispatch, getData]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedItems.length || !window.confirm(`Delete ${selectedItems.length} flow(s)?`)) return;
    try {
      await Promise.all(selectedItems.map((item) => deleteFlow(item.id)));
      dispatch(showToast({ message: `${selectedItems.length} flow(s) deleted`, type: "success" }));
      getData(); setSelectedItems([]);
    } catch { dispatch(showToast({ message: "Failed to delete some flows", type: "error" })); }
  }, [selectedItems, dispatch, getData]);

  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    try {
      setLoading(true);
      const searchQuery = terms.join(",");
      const res = await fetchFlows({ search: searchQuery });
      if (res.status === 200) {
        setData(res.data?.items || res.data?.data?.results || []);
      }
    } catch (error) {
      console.error("Database search failed:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const columns: TableColumn<any>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "name", name: "Name", selector: (row) => row.name || "--", sortable: true },
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
      <PageBreadcrumb pageTitle="Flow List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="Flows"
              loading={loading}
              storageKey="flow-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedItems}
              exportFileName="flow_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search flows..."
              noDataMessage="No flows found"
              enableDatabaseSearch={true}
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
              customActions={
                <div className="flex gap-2">
                  {selectedItems.length > 0 && (
                    <button onClick={handleBulkDelete} className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors">
                      <FaTrash className="w-4 h-4" /> Delete ({selectedItems.length})
                    </button>
                  )}
                  <button onClick={handleAdd} className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors">
                    <FaPlus className="w-4 h-4" /> Add Flow
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <FlowDetail inline modeProp={formMode} dataProp={selectedFlow} onSaved={handleFormSaved} onCancelInline={handleFormCancel} />
          </div>
        )}
      </div>
    </>
  );
}