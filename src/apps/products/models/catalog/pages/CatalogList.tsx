import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import DataTable, { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchCatalogs } from "../services/catalogApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useTheme } from "../../../../../context/ThemeContext";
import CatalogDetail from "./CatalogDetail";

export default function CatalogList() {
  const { theme } = useTheme();
  const [data, setData] = useState<any[]>([]);
  const [selectedCatalog, setSelectedCatalog] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();

  const getCatalogData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchCatalogs();
      if (res.status === 200) {
        setData(res.data.items);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch catalogs", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch catalogs", error);
      dispatch(showToast({ message: "Failed to fetch catalogs", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getCatalogData();
  }, [getCatalogData]);

  const handleView = (row: any) => {
    setSelectedCatalog(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedCatalog(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedCatalog(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getCatalogData();
    setFormMode(null);
    setSelectedCatalog(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedCatalog(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete catalog ${row.name}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(showToast({ message: "Catalog deleted successfully", type: "success" }));
        getCatalogData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete catalog", type: "error" }));
      }
    }
  };

  const catalogColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "5%" },
    {
      name: "Name",
      selector: (row) => row.name || "--",
      sortable: true,
      width: "30%",
    },
    {
      name: "Description",
      selector: (row) => row.description || "--",
      sortable: true,
      width: "40%",
    },
    {
      name: "Category",
      selector: (row) => row.category || "--",
      sortable: true,
      width: "20%",
    },
    {
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
            <FaTrash className="text-red-600 hover:scale-110 transition" />
          </button>
        </div>
      ),
      ignoreRowClick: true,
      allowOverflow: true,
      button: true,
    },
  ];

  return (
    <>
      <PageBreadcrumb pageTitle="Catalog List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Catalog
              </button>
            </div>
            <div className="overflow-x-auto bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-400 rounded-md">
              <DataTable
                columns={catalogColumns.map((col) => ({
                  ...col,
                  name: typeof col.name === "string" ? col.name.toUpperCase() : col.name,
                }))}
                data={data}
                pagination
                theme={theme === "dark" ? "tailwindDark" : "default"}
                highlightOnHover
                pointerOnHover
                progressPending={loading}
                progressComponent={<div className="p-8 text-center">Loading catalogs...</div>}
                onRowClicked={(row) => handleView(row)}
              />
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <CatalogDetail
              inline
              modeProp={formMode}
              dataProp={selectedCatalog}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}