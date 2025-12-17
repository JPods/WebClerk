import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import DataTable, { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { fetchDomains, deleteDomain } from "../services/domainApi";
import { FaEye, FaEdit, FaTrash, FaPlus } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useTheme } from "../../../../../context/ThemeContext";
import DomainDetail from "./domain1";


export default function DomainList() {
  const { theme } = useTheme();
  const [data, setData] = useState<any[]>([]);
  const [selectedDomain, setSelectedDomain] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();

  const getDomainData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchDomains();
      if (res.status === 200) {
        //alert("ddd");
        setData(res.data.data.results);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch domains", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch domains", error);
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getDomainData();
  }, [getDomainData]);

  const handleView = (row: any) => {
    setSelectedDomain(row);
    setFormMode("view");
  };

  const handleEdit = async (row: any) => {
     const res = await fetchDomains({ id: row.id });
     if (res.status === 200) setSelectedDomain(res.data.items[0]);
     else setSelectedDomain(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedDomain(null);
    setFormMode("add");
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete domain ${row.path}?`)) {
      try {
        await deleteDomain(row.id);
        dispatch(
          showToast({
            message: "Domain deleted successfully",
            type: "success",
          })
        );
        getDomainData(); // Refresh data
        if (selectedDomain && selectedDomain.id === row.id) {
          setFormMode(null);
          setSelectedDomain(null);
        }
      } catch (error) {
        dispatch(
          showToast({
            message: "Failed to delete domain",
            type: "error",
          })
        );
      }
    }
  };

  const handleFormSaved = () => {
    getDomainData();
    setFormMode(null);
    setSelectedDomain(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedDomain(null);
  };

  const userColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "5%" },
    {
      name: "Path",
      selector: (row) => row.path || "--",
      sortable: true,
      width: "25%",
    },
    {
      name: "Type",
      selector: (row) => row.type || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Status",
      selector: (row) => row.status || "--",
      sortable: true,
      width: "10%",
    },
    {
      name: "Comment",
      selector: (row) => row.comment || "--",
      sortable: true,
      width: "30%",
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
      <PageBreadcrumb pageTitle="Domain List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Domain
              </button>
            </div>
            <div className="overflow-x-auto bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-400 rounded-md">
              <DataTable
                columns={userColumns.map((col) => ({
                  ...col,
                  name:
                    typeof col.name === "string"
                      ? col.name.toUpperCase()
                      : col.name,
                }))}
                data={data}
                pagination
                theme={theme === "dark" ? "tailwindDark" : "default"}
                highlightOnHover
                pointerOnHover
                progressPending={loading}
                progressComponent={
                  <div className="p-8 text-center">Loading domains...</div>
                }
                onRowClicked={(row) => handleView(row)}
                keyField="id"
              />
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <DomainDetail
              inline
              modeProp={formMode}
              dataProp={selectedDomain}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}