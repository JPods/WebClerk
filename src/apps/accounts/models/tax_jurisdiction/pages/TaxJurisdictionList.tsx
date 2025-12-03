import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import ComponentCard from "@/components/common/ComponentCard";
import DataTable, { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { getRecords } from "@/api/wcapi";
import { FaEye, FaEdit, FaPlus, FaTrashAlt } from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useTheme } from "@/context/ThemeContext";
import { deleteRecord } from "@/api/wcapi";
import TaxJurisdictionDisplay from "./TaxJurisdictionDisplay";

export default function TaxJurisdictionList() {
  const { theme } = useTheme();
  const [data, setData] = useState<any[]>([]);
  const [selectedTaxJurisdiction, setSelectedTaxJurisdiction] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();

  const getTaxJurisdictionData = useCallback(async () => {
    try {
      setLoading(true);
      const list = await getRecords('tax_jurisdiction');
      const recs = Array.isArray(list?.results) ? list.results : Array.isArray(list) ? list : [];
      setData(recs);
    } catch (error) {
      console.error("Failed to fetch tax jurisdictions", error);
      dispatch(showToast({ message: "Failed to fetch tax jurisdictions", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getTaxJurisdictionData();
  }, [getTaxJurisdictionData]);

  const handleView = (row: any) => {
    setSelectedTaxJurisdiction(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedTaxJurisdiction(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedTaxJurisdiction(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getTaxJurisdictionData();
    setFormMode(null);
    setSelectedTaxJurisdiction(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedTaxJurisdiction(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete tax jurisdiction ${row.id}?`)) {
      try {
        await deleteRecord('tax_jurisdiction', row.id);
        dispatch(showToast({ message: "Tax Jurisdiction deleted successfully", type: "success" }));
        getTaxJurisdictionData(); // Refresh data
      } catch {
        dispatch(showToast({ message: "Failed to delete tax jurisdiction", type: "error" }));
      }
    }
  };

  // Hardcoded columns: id and common fields
  const userColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "10%" },
    { name: "Name", selector: (row) => row.name || "--", sortable: true, width: "30%" },
    { name: "Code", selector: (row) => row.code || "--", sortable: true, width: "20%" },
    { name: "Rate", selector: (row) => row.rate || "--", sortable: true, width: "20%" },
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
      <PageBreadcrumb pageTitle="Tax Jurisdiction List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Tax Jurisdiction
              </button>
            </div>
            <div className="overflow-x-auto bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-400 rounded-md">
              <DataTable
                columns={userColumns.map((col) => ({
                  ...col,
                  name: typeof col.name === "string" ? col.name.toUpperCase() : col.name,
                }))}
                data={data}
                pagination
                theme={theme === "dark" ? "tailwindDark" : "default"}
                highlightOnHover
                pointerOnHover
                progressPending={loading}
                progressComponent={<div className="p-8 text-center">Loading tax jurisdictions...</div>}
                onRowClicked={(row) => handleView(row)}
              />
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <TaxJurisdictionDisplay
              inline
              modeProp={formMode}
              dataProp={selectedTaxJurisdiction}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}