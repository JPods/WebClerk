import PageBreadcrumb from "../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../components/common/ComponentCard";
import AdvancedDataTable from "../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { deleteAction } from "../../../../api/userProfile";
import { fetchConnections } from "../services/connectionApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import ConnectionDetail from "./ConnectionDetail";

export default function ConnectionList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedConnection, setSelectedConnection] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();

  const getConnectionData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchConnections();
      if (res.status === 200) {
        setData(res.data.items);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch connections", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch connections", error);
      dispatch(showToast({ message: "Failed to fetch connections", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getConnectionData();
  }, [getConnectionData]);

  const handleView = (row: any) => {
    setSelectedConnection(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedConnection(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedConnection(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getConnectionData();
    setFormMode(null);
    setSelectedConnection(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedConnection(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete connection ${row.name}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(showToast({ message: "Connection deleted successfully", type: "success" }));
        getConnectionData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete connection", type: "error" }));
      }
    }
  };

  const userColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "5%" },
    {
      name: "Name",
      selector: (row) => row.name || "--",
      sortable: true,
      width: "20%",
    },
    {
      name: "Type",
      selector: (row) => row.type || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Host",
      selector: (row) => row.host || "--",
      sortable: true,
      width: "20%",
    },
    {
      name: "Port",
      selector: (row) => row.port || "--",
      sortable: true,
      width: "10%",
    },
    {
      name: "Username",
      selector: (row) => row.username || "--",
      sortable: true,
      width: "15%",
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
      <PageBreadcrumb pageTitle="Connection List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Connection
              </button>
            </div>
            <div className="overflow-x-auto bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-400 rounded-md">
              <AdvancedDataTable
                columns={userColumns.map((col) => ({
                  ...col,
                  name: typeof col.name === "string" ? col.name.toUpperCase() : col.name,
                }))}
                data={data}
                storageKey="connection_list"
                loading={loading}
                onRowActivate={handleEdit}
              />
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <ConnectionDetail
              inline
              modeProp={formMode}
              dataProp={selectedConnection}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}