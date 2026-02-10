import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import { TableColumn } from "react-data-table-component";
import AdvancedDataTable from "../../../../../components/common/AdvancedDataTable";
import { useEffect, useState, useCallback } from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchItemXrefs } from "../services/itemXrefApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useTheme } from "../../../../../context/ThemeContext";
import ItemXrefDetail from "./ItemXrefDetail";

export default function ItemXrefList() {
  const { theme } = useTheme();
  const [data, setData] = useState<any[]>([]);
  const [selectedItemXref, setSelectedItemXref] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);

  const dispatch = useDispatch();

  const getItemXrefData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchItemXrefs();
      if (res.status === 200) {
        setData(res.data.items || []);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch item xrefs", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch item xrefs", error);
      dispatch(showToast({ message: "Failed to fetch item xrefs", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getItemXrefData();
  }, [getItemXrefData]);

  const handleView = (row: any) => {
    setSelectedItemXref(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedItemXref(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedItemXref(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getItemXrefData();
    setFormMode(null);
    setSelectedItemXref(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedItemXref(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete item xref ${row.id}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(showToast({ message: "Item xref deleted successfully", type: "success" }));
        getItemXrefData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete item xref", type: "error" }));
      }
    }
  };

  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    try {
      setLoading(true);
      const searchQuery = terms.join(",");
      const res = await fetchItemXrefs({ search: searchQuery });
      if (res.status === 200) {
        setData(res.data.items || []);
      }
    } catch (error) {
      console.error("Database search failed:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const userColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "5%" },
    {
      name: "Item ID 1",
      selector: (row) => row.item_id_1 || "--",
      sortable: true,
      width: "20%",
    },
    {
      name: "Item ID 2",
      selector: (row) => row.item_id_2 || "--",
      sortable: true,
      width: "20%",
    },
    {
      name: "Relationship Type",
      selector: (row) => row.relationship_type || "--",
      sortable: true,
      width: "25%",
    },
    {
      name: "Description",
      selector: (row) => row.description || "--",
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
      <PageBreadcrumb pageTitle="Item Xref List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Item Xref
              </button>
            </div>
            <div className="overflow-x-auto bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-400 rounded-md">
              <AdvancedDataTable
                columns={userColumns.map((col) => ({
                  ...col,
                  name: typeof col.name === "string" ? col.name.toUpperCase() : col.name,
                }))}
                data={data}
                storageKey="item_xref_list"
                onRowActivate={handleEdit}
                loading={loading}
                enableDatabaseSearch={true}
                searchDatabase={searchDatabase}
                onSearchModeChange={setSearchDatabase}
                onDatabaseSearch={handleDatabaseSearch}
              />
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <ItemXrefDetail
              inline
              modeProp={formMode}
              dataProp={selectedItemXref}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}