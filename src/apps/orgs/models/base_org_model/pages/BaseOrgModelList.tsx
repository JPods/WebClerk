import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import ComponentCard from "@/components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter } from "@/components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { getRecords, deleteRecord } from "@/api/wcapi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import BaseOrgModelDisplay from "./BaseOrgModelDisplay";

export default function BaseOrgModelList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedBaseOrgModel, setSelectedBaseOrgModel] = useState<any | null>(null);
  const [selectedBaseOrgModels, setSelectedBaseOrgModels] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const getBaseOrgModelData = useCallback(async () => {
    try {
      setLoading(true);
      const list = await getRecords('base_org_model');
      const recs = Array.isArray(list?.results) ? list.results : Array.isArray(list) ? list : [];
      setData(recs);
    } catch (error) {
      console.error("Failed to fetch base org models", error);
      dispatch(showToast({ message: "Failed to fetch base org models", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getBaseOrgModelData();
  }, [getBaseOrgModelData]);

  const handleView = useCallback((row: any) => {
    setSelectedBaseOrgModel(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback((row: any) => {
    setSelectedBaseOrgModel(row);
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedBaseOrgModel(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getBaseOrgModelData();
    setFormMode(null);
    setSelectedBaseOrgModel(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedBaseOrgModel(null);
  };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete base org model ${row.name || row.id}?`)) return;
    
    try {
      await deleteRecord('base_org_model', row.id);
      dispatch(showToast({ message: "Base Org Model deleted successfully", type: "success" }));
      getBaseOrgModelData();
      if (selectedBaseOrgModel && selectedBaseOrgModel.id === row.id) {
        setFormMode(null);
        setSelectedBaseOrgModel(null);
      }
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete base org model", type: "error" }));
    }
  }, [dispatch, getBaseOrgModelData, selectedBaseOrgModel]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedBaseOrgModels.length) return;
    if (!window.confirm(`Delete ${selectedBaseOrgModels.length} base org model(s)?`)) return;

    try {
      await Promise.all(selectedBaseOrgModels.map((m) => deleteRecord('base_org_model', m.id)));
      dispatch(showToast({ message: `${selectedBaseOrgModels.length} base org model(s) deleted`, type: "success" }));
      getBaseOrgModelData();
      setSelectedBaseOrgModels([]);
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete some base org models", type: "error" }));
    }
  }, [selectedBaseOrgModels, dispatch, getBaseOrgModelData]);

  const filters: ColumnFilter[] = useMemo(() => [
    { key: "type", label: "Type", type: "text" },
    { key: "status", label: "Status", type: "text" },
  ], []);

  const columns: TableColumn<any>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "name", name: "Name", selector: (row) => row.name || "--", sortable: true, width: "40%" },
    { id: "type", name: "Type", selector: (row) => row.type || "--", sortable: true, width: "25%" },
    { id: "status", name: "Status", selector: (row) => row.status || "--", sortable: true, width: "15%" },
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
      <PageBreadcrumb pageTitle="Base Org Model List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="Base Org Models"
              loading={loading}
              filters={filters}
              storageKey="base-org-model-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedBaseOrgModels}
              exportFileName="base_org_models_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search base org models..."
              noDataMessage="No base org models found"
              customActions={
                <div className="flex gap-2">
                  {selectedBaseOrgModels.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" />
                      Delete ({selectedBaseOrgModels.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Base Org Model
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <BaseOrgModelDisplay
              inline
              modeProp={formMode}
              dataProp={selectedBaseOrgModel}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
