import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import DataTable, { TableColumn } from "react-data-table-component";
//import { createTheme } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { getRecords, getRecord } from "../../../../../api/wcapi";
import { dynamicData } from "../../../../../model/dynamicData";
import { FaEye, FaEdit, FaPlus, FaCheck, FaTimes } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useTheme } from "../../../../../context/ThemeContext";
import ContactAdd from "./ContactDetail";
import Badge from "../../../../../components/ui/badge/Badge";
import { fetchContacts } from "../services/contactApi";
export default function ContactList() {
  const { theme } = useTheme();
  const [data, setData] = useState<dynamicData[]>([]);
  const [selectedContact, setSelectedContact] = useState<dynamicData | null>(
    null
  );
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    null
  );
  const [isMobile, setIsMobile] = useState<boolean>(false);

  const dispatch = useDispatch();
  console.log("data", data);
  const getContactData = useCallback(async () => {
    try {
      const res = await fetchContacts();
      if (res.status === 200) {
        console.log(res.data.results);
        setData(res.data.results);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch contacts", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch contacts", error);
      dispatch(
        showToast({ message: "Failed to fetch contacts", type: "error" })
      );
    }
  }, [dispatch]);

  useEffect(() => {
    getContactData();
  }, [getContactData]);

  useEffect(() => {
    // Function to check if the screen is mobile or not
    const handleResize = () => {
      if (window.innerWidth <= 768) {
        setIsMobile(true); // Considered mobile screen if width <= 768px
      } else {
        setIsMobile(false); // Otherwise, consider it as desktop
      }
    };

    // Call the function once to set the initial state
    handleResize();

    // Set up the event listener for window resize
    window.addEventListener("resize", handleResize);

    // Cleanup the event listener on component unmount
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  const handleView = (row: dynamicData) => {
    setSelectedContact(row);
    setFormMode("view");
  };

  const handleEdit = async (row: dynamicData) => {
    try {
      const res = await getRecord("contact", row.id);
      setSelectedContact(res.record);
    } catch (error) {
      setSelectedContact(row);
    }
    setFormMode("edit");
  };

  console.log("res.data.items", selectedContact);
  const handleAdd = () => {
    setSelectedContact(null);
    setFormMode("add");
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
    { name: "ID", selector: (row) => row.id, sortable: true, width: "5%" },
    {
      name: "Email",
      selector: (row) => row.email || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Name First",
      selector: (row) => row.name_first || "--",
      sortable: true,
      width: "13%",
    },
    {
      name: "Name Last",
      selector: (row) => row.name_last || "--",
      sortable: true,
      width: "13%",
    },
    {
      name: "Company",
      selector: (row) => row.company || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Role",
      selector: (row) => row.role || "--",
      sortable: true,
      width: "10%",
    },
    {
      name: "Is Active",
      selector: (row) => (row.is_active ? "yes" : "no"), // Plain string for filtering
      cell: (row) => (
        <>
          {row.is_active ? (
            <FaCheck className="text-success-600 hover:scale-110 transition" />
          ) : (
            <FaTimes className="text-warning-600 hover:scale-110 transition" />
          )}
        </>
      ),
      sortable: true,
      width: "10%",
    },

    {
      name: "Is Staff",
      selector: (row) => (row.is_staff ? "yes" : "no"), // Plain string for filtering
      cell: (row) => (
        <div className="flex justify-center">
          {row.is_staff ? (
            <FaCheck className="text-success-600 hover:scale-110 transition" />
          ) : (
            <FaTimes className="text-warning-600 hover:scale-110 transition" />
          )}
        </div>
      ),
      sortable: true,
      width: "10%",
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
          {/* <button onClick={() => handleDelete(row)} title="Delete">
            <FaTrash className="text-red-600 hover:scale-110 transition" />
          </button> */}
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
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Contact
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
