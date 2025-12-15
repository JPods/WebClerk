import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import DataTable, { TableColumn } from "react-data-table-component";
//import { createTheme } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchDomains } from "../services/domainApi";
import { dynamicData } from "../../../../../model/dynamicData";
import { FaEye, FaEdit, FaTrash, FaPlus } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useTheme } from "../../../../../context/ThemeContext";
import DomainAdd from "./Domain";
import Badge from "../../../../../components/ui/badge/Badge";

export default function DomainList() {
  const { theme } = useTheme();
  const [data, setData] = useState<dynamicData[]>([]);
  const [selectedDomain, setSelectedDomain] = useState<dynamicData | null>(
    null
  );
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    null
  );

  const dispatch = useDispatch();

  const getDomainData = useCallback(async () => {
    try {
      const res = await fetchDomains();
      if (res.status === 200) {
        //alert("ddd");
        console.log(res.data.items);
        setData(res.data.items);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch domains", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch domains", error);
    }
  }, [dispatch]);

  useEffect(() => {
    getDomainData();
  }, [getDomainData]);

  const handleView = (row: dynamicData) => {
    setSelectedDomain(row);
    setFormMode("view");
  };

  const handleEdit = async (row: dynamicData) => {
    const res = await fetchDomains(row.id);
    if (res.status === 200) setSelectedDomain(res.data.item);
    else setSelectedDomain(row);
    setFormMode("edit");
    console.log("res", res);
  };

  console.log("res.data.items", selectedDomain);
  const handleAdd = () => {
    setSelectedDomain(null);
    setFormMode("add");
  };

  const handleDelete = async (row: dynamicData) => {
    if (window.confirm(`Delete domain ${row.name_first}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(
          showToast({
            message: "Domains deleted successfully",
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
            message: "Failed to delete domain" + error,
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

  const userColumns: TableColumn<dynamicData>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "5%" },
    {
      name: "Path",
      selector: (row) => row.path || "--",
      sortable: true,
      width: "60%", // ⬅ reduced
      wrap: true,
    },
    {
      name: "Type",
      selector: (row) => row.type || "--",
      sortable: true,
      width: "10%",
    },
    {
      name: "Is Active",
      selector: (row) => (row.is_active ? "Active" : "Inactive"),
      cell: (row) => (
        <Badge size="sm" color={row.is_active ? "success" : "warning"}>
          {row.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
      sortable: true,
      width: "10%",
    },
    {
      name: "Action",
      cell: (row) => (
        <div className="flex gap-2 justify-center">
          <button onClick={() => handleView(row)} title="View">
            <FaEye className="text-blue-600 hover:scale-110 transition" />
          </button>
          <button onClick={() => handleEdit(row)} title="Edit">
            <FaEdit className="text-green-600 hover:scale-110 transition" />
          </button>
          {/* <button onClick={() => handleDelete(row)} title="Delete">
            <FaTrash className="text-red-600 hover:scale-110 transition" />
          </button> */}
        </div>
      ),
      ignoreRowClick: true,
      button: true,
      width: "15%", // ⬅ increased
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
                disabled={data.length === 0 && !data}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Domain
              </button>
            </div>
            <div className="w-full overflow-x-auto bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-400 rounded-md">
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
                progressPending={data.length === 0}
                progressComponent={
                  <div className="p-8 text-center">Loading record...</div>
                }
                onRowClicked={(row) => handleView(row)}
                responsive
                // dense
              />
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <DomainAdd
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
