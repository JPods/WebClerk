import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { getRecords, deleteRecord } from "../../../../../api/wcapi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import TermDisplay from "./TermDisplay";

export default function TermList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedTerm, setSelectedTerm] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();

  const getTermData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getRecords('term');
      setData(res.results || []);
    } catch (error) {
      console.error("Failed to fetch terms", error);
      dispatch(showToast({ message: "Failed to fetch terms", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getTermData();
  }, [getTermData]);

  const handleView = (row: any) => {
    setSelectedTerm(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedTerm(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedTerm(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getTermData();
    setFormMode(null);
    setSelectedTerm(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedTerm(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete term ${row.name}?`)) {
      try {
        await deleteRecord('term', row.id);
        dispatch(showToast({ message: "Term deleted successfully", type: "success" }));
        getTermData();
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete term", type: "error" }));
      }
    }
  };

  const userColumns: TableColumn<any>[] = useMemo(() => [
    { name: "ID", selector: (row: any) => row.id, sortable: true, width: "80px" },
    { name: "Name", selector: (row: any) => row.name || "--", sortable: true },
    { name: "Description", selector: (row: any) => row.description || "--", sortable: true },
    { name: "Duration", selector: (row: any) => row.duration || "--", sortable: true },
    {
      name: "Actions",
      cell: (row: any) => (
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
      button: true,
    },
  ], []);

  return (
    <>
      <PageBreadcrumb pageTitle="Terms" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600"
              >
                <FaPlus />
                Add Term
              </button>
            </div>
            <AdvancedDataTable
              columns={userColumns}
              data={data}
              loading={loading}
              storageKey="term_list"
              onRowActivate={handleEdit}
              title="Terms"
              exportFileName="terms"
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <TermDisplay
              inline
              modeProp={formMode}
              dataProp={selectedTerm}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
