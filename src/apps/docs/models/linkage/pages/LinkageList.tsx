import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import ComponentCard from "@/components/common/ComponentCard";
import AdvancedDataTable from "@/components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { getRecords } from "@/api/wcapi";
import { FaEye, FaEdit, FaPlus, FaTrashAlt } from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { deleteRecord } from "@/api/wcapi";
import LinkageDisplay from "./LinkageDisplay";

export default function LinkageList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedLinkage, setSelectedLinkage] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();

  const getLinkageData = useCallback(async () => {
    try {
      setLoading(true);
      const list = await getRecords('linkage');
      const recs = Array.isArray(list?.results) ? list.results : Array.isArray(list) ? list : [];
      setData(recs);
    } catch (error) {
      console.error("Failed to fetch linkages", error);
      dispatch(showToast({ message: "Failed to fetch linkages", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getLinkageData();
  }, [getLinkageData]);

  const handleView = (row: any) => {
    setSelectedLinkage(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedLinkage(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedLinkage(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getLinkageData();
    setFormMode(null);
    setSelectedLinkage(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedLinkage(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete linkage ${row.id}?`)) {
      try {
        await deleteRecord('linkage', row.id);
        dispatch(showToast({ message: "Linkage deleted successfully", type: "success" }));
        getLinkageData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete linkage", type: "error" }));
      }
    }
  };

  // Hardcoded columns: id and common fields
  const userColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "10%" },
    { name: "Source", selector: (row) => row.source || "--", sortable: true, width: "30%" },
    { name: "Target", selector: (row) => row.target || "--", sortable: true, width: "30%" },
    { name: "Type", selector: (row) => row.type || "--", sortable: true, width: "30%" },
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
          <FaTrashAlt className="text-red-600 hover:scale-110 transition" />
        </button>
      </div>
    ),
    ignoreRowClick: true,
    allowOverflow: true,
    button: true,
  });

  return (
    <>
      <PageBreadcrumb pageTitle="Linkage List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Linkage
              </button>
            </div>
            <AdvancedDataTable
              columns={userColumns}
              data={data}
              storageKey="linkage_list"
              progressPending={loading}
              onRowActivate={handleEdit}
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <LinkageDisplay
              inline
              modeProp={formMode}
              dataProp={selectedLinkage}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}