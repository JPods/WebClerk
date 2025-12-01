import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import DataTable, { TableColumn } from "react-data-table-component";
//import { createTheme } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchContacts } from "../services/contactApi";
import { dynamicData } from "../../../../../model/dynamicData";
import { FaEye, FaEdit, FaTrash, FaPlus } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useTheme } from "../../../../../context/ThemeContext";
import ContactAdd from "./ContactDetail";
import Badge from "../../../../../components/ui/badge/Badge";

export default function ContactList() {
  const { theme } = useTheme();
  const [data, setData] = useState<dynamicData[]>([]);
  const [selectedContact, setSelectedContact] = useState<dynamicData | null>(
    null
  );
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    null
  );

  const dispatch = useDispatch();

  const getContactData = useCallback(async () => {
    try {
      const res = await fetchContacts();
      if (res.status === 200) {
        //console.log(res.data.items);
        setData(res.data.items);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch contacts", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch contacts", error);
    }
  }, [dispatch]);

  useEffect(() => {
    getContactData();
  }, [getContactData]);

  const handleView = (row: dynamicData) => {
    setSelectedContact(row);
    setFormMode("view");
  };

  const handleEdit = async (row: dynamicData) => {
    const res = await fetchContacts(row.id);
    if (res.status === 200) setSelectedContact(res.data.data.record);
    else setSelectedContact(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedContact(null);
    setFormMode("add");
  };

  const handleDelete = async (row: dynamicData) => {
    if (window.confirm(`Delete contact ${row.name_first}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(
          showToast({
            message: "Contact deleted successfully",
            type: "success",
          })
        );
        getContactData(); // Refresh data
        if (selectedContact && selectedContact.id === row.id) {
          setFormMode(null);
          setSelectedContact(null);
        }
      } catch (error) {
        dispatch(
          showToast({
            message: "Failed to delete contact" + error,
            type: "error",
          })
        );
      }
    }
  };

  const handleFormSaved = () => {
    getContactData();
    setFormMode(null);
    setSelectedContact(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedContact(null);
  };

  const userColumns: TableColumn<dynamicData>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true },
    { name: "Email", selector: (row) => row.email || "--", sortable: true },
    {
      name: "Name First",
      selector: (row) => row.name_first || "--",
      sortable: true,
    },
    {
      name: "Name Last",
      selector: (row) => row.name_last || "--",
      sortable: true,
    },
    { name: "Company", selector: (row) => row.company || "--", sortable: true },
    { name: "Role", selector: (row) => row.role || "--", sortable: true },
    {
      name: "Is Active",
      selector: (row) => (row.is_active ? "Inactive" : "Active"), // Plain string for filtering
      cell: (row) => (
        <>
          <Badge size="sm" color={row.is_active ? "success" : "warning"}>
            {row.is_active ? "Active" : "Inactive"}
          </Badge>
        </>
      ),
      sortable: true,
    },
    {
      name: "Is Staff",
      selector: (row) => (row.is_staff ? "Inactive" : "Active"), // Plain string for filtering
      cell: (row) => (
        <>
          <Badge size="sm" color={row.is_staff ? "success" : "warning"}>
            {row.is_staff ? "Active" : "Inactive"}
          </Badge>
        </>
      ),
      sortable: true,
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
      <PageBreadcrumb pageTitle="Contact List" />
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
                Add Contact
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
                progressPending={data.length === 0}
                progressComponent={
                  <div className="p-8 text-center">Loading contacts...</div>
                }
                onRowClicked={(row) => handleView(row)}
              />
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <ContactAdd
              inline
              modeProp={formMode}
              dataProp={selectedContact}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
