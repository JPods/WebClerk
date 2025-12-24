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
  const [filteredData, setFilteredData] = useState<dynamicData[]>([]);
  const [filteredSearch, setFilteredSearch] = useState<string>("");

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
      setFilteredData(res.data.results);
      if (contactId) {
        const contactRes = await getRecord("contact", contactId);
        setSelectedContact(contactRes.record);
        setFilteredData(contactRes.record);
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

  // --------------- Global Filtered ---------------------------//
  const filterData = (inputData: string) => {
    const searchQuery = inputData.trim().toLowerCase(); // Trim and lowercase for case-insensitive comparison
    setFilteredSearch(searchQuery);
    if (searchQuery) {
      const filtered = data.filter((element) => {
        // Combine all columns you want to search in as strings
        const valuesToSearch = [
          element.email,
          element.name_first,
          element.name_last,
          element.company,
          element.role,
        ].map((value) => value && value.toString().trim().toLowerCase()); // Trim and lowercase each value

        // Check if any of the column values includes the search query
        return valuesToSearch.some(
          (value) => value && value.includes(searchQuery)
        );
      });

      setFilteredData(filtered); // Update filtered data
    } else {
      setFilteredData(data);
    }
  };
  const highlightMatch = useCallback(
    (text: string) => {
      if (!filteredSearch) return text;

      const escaped = filteredSearch.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const regex = new RegExp(`(${escaped})`, "gi");

      return text.split(regex).map((part, index) =>
        part.toLowerCase() === filteredSearch ? (
          <span key={index} className="text-red-600 font-semibold">
            {part}
          </span>
        ) : (
          part
        )
      );
    },
    [filteredSearch]
  );
  const userColumns: TableColumn<dynamicData>[] = useMemo(
    () => [
      { name: "id", selector: (row) => row.id, sortable: true, width: "5%" },
      {
        name: "email",
        selector: (row) => row.email || "--",
        cell: (row) =>
          row.email ? highlightMatch(row.email.toString()) : "--",
        sortable: true,
        width: "15%",
      },
      {
        name: "name_first",
        selector: (row) => row.name_first || "--",
        cell: (row) =>
          row.name_first ? highlightMatch(row.name_first.toString()) : "--",
        sortable: true,
        width: "13%",
      },
      {
        name: "name_last",
        selector: (row) => row.name_last || "--",
        cell: (row) =>
          row.name_last ? highlightMatch(row.name_last.toString()) : "--",
        sortable: true,
        width: "13%",
      },
      {
        name: "company",
        selector: (row) => row.company || "--",
        cell: (row) =>
          row.company ? highlightMatch(row.company.toString()) : "--",
        sortable: true,
        width: "15%",
      },
      {
        name: "role",
        selector: (row) => row.role || "--",
        cell: (row) => (row.role ? highlightMatch(row.role.toString()) : "--"),
        sortable: true,
        width: "10%",
      },
      {
        name: "is_active",
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
        name: "is_staff",
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
        name: "action",
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
    [highlightMatch]
  );

  /* ---------------- UI ---------------- */
  return (
    <>
      <PageBreadcrumb pageTitle="Contact List" />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* List */}
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-between mb-0">
              <div className="flex  mb-2">
                <div className="relative">
                  <span className="absolute -translate-y-1/2 pointer-events-none left-4 top-1/2">
                    <svg
                      className="fill-gray-500 dark:fill-gray-400"
                      width="20"
                      height="20"
                      viewBox="0 0 20 20"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        fillRule="evenodd"
                        clipRule="evenodd"
                        d="M3.04175 9.37363C3.04175 5.87693 5.87711 3.04199 9.37508 3.04199C12.8731 3.04199 15.7084 5.87693 15.7084 9.37363C15.7084 12.8703 12.8731 15.7053 9.37508 15.7053C5.87711 15.7053 3.04175 12.8703 3.04175 9.37363ZM9.37508 1.54199C5.04902 1.54199 1.54175 5.04817 1.54175 9.37363C1.54175 13.6991 5.04902 17.2053 9.37508 17.2053C11.2674 17.2053 13.003 16.5344 14.357 15.4176L17.177 18.238C17.4699 18.5309 17.9448 18.5309 18.2377 18.238C18.5306 17.9451 18.5306 17.4703 18.2377 17.1774L15.418 14.3573C16.5365 13.0033 17.2084 11.2669 17.2084 9.37363C17.2084 5.04817 13.7011 1.54199 9.37508 1.54199Z"
                        fill=""
                      />
                    </svg>
                  </span>
                  <input
                    type="text"
                    value={filteredSearch}
                    onChange={(e) => filterData(e.target.value)}
                    placeholder="Search for record..."
                    className="dark:bg-dark-900 h-11 w-full rounded-lg border border-gray-200 bg-transparent py-2.5 pl-12 pr-14 text-sm text-gray-800 shadow-theme-xs placeholder:text-gray-400 focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-800 dark:bg-gray-900 dark:bg-white/[0.03] dark:text-white/90 dark:placeholder:text-white/30 dark:focus:border-brand-800 "
                  />
                  <button className="absolute right-2.5 top-1/2 inline-flex -translate-y-1/2 items-center gap-0.5 rounded-lg border border-gray-200 bg-gray-50 px-[7px] py-[4.5px] text-xs -tracking-[0.2px] text-gray-500 dark:border-gray-800 dark:bg-white/[0.03] dark:text-gray-400">
                    <span>
                      <button
                        type="button"
                        onClick={() => filterData("")}
                        className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                      >
                        &times;
                      </button>
                    </span>
                  </button>
                </div>
              </div>
              <div className="flex mb-2">
                <button
                  onClick={handleAdd}
                  className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
                >
                  <FaPlus />
                  Add Contact
                </button>
              </div>
            </div>
            <div className="w-full overflow-x-auto rounded-md cus-bg-purple-light dark:bg-gray-900 h-[calc(100vh-265px)]">
              {isMobile || formMode ? (
                <div className="flex flex-col">
                  <ContactListMob
                    dataProp={filteredData}
                    handleView={handleView}
                    handleEdit={handleEdit}
                  />
                </div>
              ) : (
                <DataTable
                  columns={userColumns.map((col) => ({
                    ...col,
                    name: typeof col.name === "string" && col.name,
                  }))}
                  data={filteredData}
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
                  className="text-2xl p-2"
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
