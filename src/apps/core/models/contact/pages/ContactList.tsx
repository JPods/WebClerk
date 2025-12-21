import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import DataTable, { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { getRecord } from "../../../../../api/wcapi";
import { dynamicData } from "../../../../../model/dynamicData";
import { FaEye, FaEdit, FaPlus, FaCheck, FaTimes } from "react-icons/fa";
import { useTheme } from "../../../../../context/ThemeContext";
import ContactAdd from "./ContactDetail";
import { fetchContacts } from "../services/contactApi";
import ContactListMob from "./ContactListMob";

export default function ContactList() {
  const { theme } = useTheme();

  const [data, setData] = useState<dynamicData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedContact, setSelectedContact] = useState<dynamicData | null>(
    null
  );
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    null
  );
  const [isMobile, setIsMobile] = useState<boolean>(false);

  /* ---------------- Fetch Contacts ---------------- */
  const getContactData = useCallback(async (contactId?: number) => {
    setLoading(true);
    try {
      const res = await fetchContacts();
      setData(res.data.results);

      if (contactId) {
        const contactRes = await getRecord("contact", contactId);
        setSelectedContact(contactRes.record);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    getContactData();
  }, [getContactData]);

  /* ---------------- Mobile Detection ---------------- */
  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 1024);
    };

    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  /* ---------------- Handlers ---------------- */
  const handleView = (row: dynamicData) => {
    setSelectedContact(row);
    setFormMode("view");
  };

  const handleEdit = async (row: dynamicData) => {
    try {
      const res = await getRecord("contact", row.id);
      setSelectedContact(res.record);
    } catch {
      setSelectedContact(row);
    }
    setFormMode("edit");
  };

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

  /* ---------------- Columns ---------------- */
  const userColumns: TableColumn<dynamicData>[] = useMemo(
    () => [
      { name: "ID", selector: (row) => row.id, sortable: true, width: "5%" },
      {
        name: "Email",
        selector: (row) => row.email || "--",
        sortable: true,
        width: "15%",
      },
      {
        name: "First Name",
        selector: (row) => row.name_first || "--",
        sortable: true,
        width: "13%",
      },
      {
        name: "Last Name",
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
        name: "Active",
        selector: (row) => (row.is_active ? "yes" : "no"),
        cell: (row) =>
          row.is_active ? (
            <FaCheck className="text-green-600" />
          ) : (
            <FaTimes className="text-red-500" />
          ),
        sortable: true,
        width: "8%",
      },
      {
        name: "Staff",
        selector: (row) => (row.is_staff ? "yes" : "no"),
        cell: (row) =>
          row.is_staff ? (
            <FaCheck className="text-green-600" />
          ) : (
            <FaTimes className="text-red-500" />
          ),
        sortable: true,
        width: "8%",
      },
      {
        name: "Action",
        cell: (row) => (
          <div className="flex gap-3">
            <button onClick={() => handleView(row)} title="View">
              <FaEye className="text-blue-600 hover:scale-110 transition" />
            </button>
            <button onClick={() => handleEdit(row)} title="Edit">
              <FaEdit className="text-green-600 hover:scale-110 transition" />
            </button>
          </div>
        ),
        ignoreRowClick: true,
        allowOverflow: true,
        button: true,
      },
    ],
    []
  );

  /* ---------------- UI ---------------- */
  return (
    <>
      <PageBreadcrumb pageTitle="Contact List" />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* List */}
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
              >
                <FaPlus />
                Add Contact
              </button>
            </div>

            <div className="w-full overflow-x-auto rounded-md bg-white dark:bg-gray-900 h-[calc(100vh-260px)]">
              {isMobile || formMode ? (
                <div className="flex flex-col">
                  <ContactListMob
                    dataProp={data}
                    handleView={handleView}
                    handleEdit={handleEdit}
                  />
                </div>
              ) : (
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
                  responsive
                  highlightOnHover
                  pointerOnHover
                  theme={theme === "dark" ? "tailwindDark" : "default"}
                  progressPending={loading}
                  progressComponent={
                    <div className="p-8 text-center text-gray-500">
                      Loading contacts...
                    </div>
                  }
                  onRowClicked={handleView}
                />
              )}
            </div>
          </ComponentCard>
        </div>

        {/* Form */}
        {formMode && (
          <div className="lg:col-span-2">
            <ContactAdd
              inline
              modeProp={formMode}
              dataProp={selectedContact}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
              getContactData={getContactData}
            />
          </div>
        )}
      </div>
    </>
  );
}
