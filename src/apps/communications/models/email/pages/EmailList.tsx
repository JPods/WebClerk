import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import DataTable, { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchEmails } from "../services/emailApi";
import { FaEye, FaEdit, FaTrash, FaPlus } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useTheme } from "../../../../../context/ThemeContext";
import EmailDetail from "./EmailDetail";

export default function EmailList() {
  const { theme } = useTheme();
  const [data, setData] = useState<any[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);

  const dispatch = useDispatch();

  const getEmailData = useCallback(async () => {
    try {
      const res = await fetchEmails();
      if (res.status === 200) {
        setData(res.data.items);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch emails", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch emails", error);
    }
  }, [dispatch]);

  useEffect(() => {
    getEmailData();
  }, [getEmailData]);

  const handleView = (row: any) => {
    setSelectedEmail(row);
    setFormMode("view");
  };

  const handleEdit = async (row: any) => {
    const res = await fetchEmails(row.id);
    if (res.status === 200) setSelectedEmail(res.data.item);
    else setSelectedEmail(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedEmail(null);
    setFormMode("add");
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete email ${row.subject}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(
          showToast({
            message: "Email deleted successfully",
            type: "success",
          })
        );
        getEmailData(); // Refresh data
        if (selectedEmail && selectedEmail.id === row.id) {
          setFormMode(null);
          setSelectedEmail(null);
        }
      } catch (error) {
        dispatch(
          showToast({
            message: "Failed to delete email" + error,
            type: "error",
          })
        );
      }
    }
  };

  const handleFormSaved = () => {
    getEmailData();
    setFormMode(null);
    setSelectedEmail(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedEmail(null);
  };

  const userColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "5%" },
    {
      name: "Subject",
      selector: (row) => row.subject || "--",
      sortable: true,
      width: "25%",
    },
    {
      name: "From",
      selector: (row) => row.from_email || "--",
      sortable: true,
      width: "20%",
    },
    {
      name: "To",
      selector: (row) => row.to_email || "--",
      sortable: true,
      width: "20%",
    },
    {
      name: "Status",
      selector: (row) => row.status || "--",
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
      <PageBreadcrumb pageTitle="Email List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Email
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
                progressComponent={
                  <div className="p-8 text-center">Loading emails...</div>
                }
                onRowClicked={(row) => handleView(row)}
              />
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <EmailDetail
              inline
              modeProp={formMode}
              dataProp={selectedEmail}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}