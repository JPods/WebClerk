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
import LinkageEntryDisplay from "./LinkageEntryDisplay";

export default function LinkageEntryList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedEntry, setSelectedEntry] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();

  const getLinkageEntryData = useCallback(async () => {
    try {
      setLoading(true);
      const list = await getRecords('linkage_entry');
      const recs = Array.isArray(list?.results) ? list.results : Array.isArray(list) ? list : [];
      setData(recs);
    } catch (error) {
      console.error("Failed to fetch linkage entries", error);
      dispatch(showToast({ message: "Failed to fetch linkage entries", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getLinkageEntryData();
  }, [getLinkageEntryData]);

  const handleView = (row: any) => {
    setSelectedEntry(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedEntry(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedEntry(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getLinkageEntryData();
    setFormMode(null);
    setSelectedEntry(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedEntry(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete linkage entry ${row.id}?`)) {
      try {
        await deleteRecord('linkage_entry', row.id);
        dispatch(showToast({ message: "Linkage Entry deleted successfully", type: "success" }));
        getLinkageEntryData();
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete linkage entry", type: "error" }));
      }
    }
  };

  const userColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row: any) => row.id, sortable: true, width: "80px" },
    { name: "Group", selector: (row: any) => row.group_id, sortable: true, width: "100px" },
    { name: "Model", selector: (row: any) => row.model_name || "--", sortable: true, width: "120px" },
    { name: "Record ID", selector: (row: any) => row.record_id, sortable: true, width: "100px" },
    { name: "Purpose", selector: (row: any) => row.purpose || "--", sortable: true, width: "120px" },
    { name: "Role", selector: (row: any) => row.role || "--", sortable: true, width: "100px" },
    { name: "Name", selector: (row: any) => row.name || "--", sortable: true },
  ];

  userColumns.push({
    name: "Action",
    cell: (row: any) => (
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
      <PageBreadcrumb pageTitle="Linkage Entries" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Linkage Entry
              </button>
            </div>
            <AdvancedDataTable
              columns={userColumns}
              data={data}
              storageKey="linkage_entry_list"
              loading={loading}
              onRowActivate={handleEdit}
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <LinkageEntryDisplay
              inline
              modeProp={formMode}
              dataProp={selectedEntry}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
