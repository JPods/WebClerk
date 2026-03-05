import { useState, useEffect, useMemo, useCallback } from "react";
import { TableColumn } from "react-data-table-component";
import { FaPlus, FaEye, FaEdit, FaTrash } from "react-icons/fa";
import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, {
  ColumnFilter,
} from "../../../../../components/common/AdvancedDataTable";
import { fetchContacts } from "../services/contactApi";
import { useNavigate } from "react-router";
import { useDispatch } from "react-redux";
import { showToast } from "../../../../../store/slices/toastSlice";
import ContactDetail from "./ContactDetail";
import ContactDetail2 from "./ContactDetail2";
import ContactDetail3 from "./ContactDetail3";
import ContactListMob from "./ContactListMob";
import { deleteRecord, getRecord } from "../../../../../api/wcapi";
import { useAppSelector } from "../../../../../store/hooks";
interface ContactData {
  id: string | number;
  email?: string;
  name_first?: string;
  name_last?: string;
  company?: string;
  role?: string;
  is_active?: boolean;
  is_staff?: boolean;
  [key: string]: any;
}

const ContactList = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const [data, setData] = useState<ContactData[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedContacts, setSelectedContacts] = useState<ContactData[]>([]);
  const [selectedContact, setSelectedContact] = useState<ContactData | null>(
    null,
  );
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    null,
  );
  const [detailVariant, setDetailVariant] = useState<1 | 2 | 3>(1);
  const [searchDatabase, setSearchDatabase] = useState(false);
  const [detailKey, setDetailKey] = useState(0);
  const { user } = useAppSelector((state) => state.auth);
  // Helper to extract translated text
  const getTranslatedText = useCallback(
    (
      translations: Record<string, string> | undefined,
      languages: string[] | undefined,
    ): string => {
      if (!translations || typeof translations !== "object") return "";

      // Try to get text in order of preference
      const preferredLangs = ["en", "ar", "bn", "es"];
      const availableLangs = languages || Object.keys(translations);

      for (const lang of preferredLangs) {
        if (translations[lang]) return translations[lang];
      }

      // Return first available translation
      for (const lang of availableLangs) {
        if (translations[lang]) return translations[lang];
      }

      return Object.values(translations)[0] || "";
    },
    [],
  );

  // Format date
  const formatDate = useCallback(
    (timestamp: number | string | null | undefined): string => {
      if (!timestamp) return "-";

      try {
        const date =
          typeof timestamp === "number"
            ? new Date(timestamp)
            : new Date(timestamp);

        if (isNaN(date.getTime())) return "-";

        return date.toLocaleDateString("en-US", {
          year: "numeric",
          month: "short",
          day: "numeric",
        });
      } catch {
        return "-";
      }
    },
    [],
  );

  // Fetch actions
  const fetchActions = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetchContacts();

      if (response.status === 200) {
        console.log("response.data.results", response.data.items);
        const apiData = Array.isArray(response?.data?.items)
          ? response.data.items
          : [];

        // Extract actions array from various possible structures
        let contacts: ContactData[] = [];

        if (Array.isArray(apiData)) {
          contacts = apiData;
        } else if (apiData && typeof apiData === "object") {
          if (Array.isArray(apiData)) {
            contacts = apiData;
          } else if (Array.isArray(apiData)) {
            contacts = apiData;
          } else if (Array.isArray(apiData)) {
            contacts = apiData;
          }
        }

        // Normalize action data

        setData(contacts);
      } else {
        throw new Error("Failed to fetch actions");
      }
    } catch (error) {
      console.error("Error fetching actions:", error);
      dispatch(
        showToast({
          message: "Failed to load actions. Please try again.",
          type: "error",
        }),
      );
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    fetchActions();
  }, [fetchActions]);

  // Handle database search
  const handleDatabaseSearch = useCallback(
    async (terms: string[]) => {
      const query = terms.join(" ");
      setLoading(true);
      try {
        const response = await fetchContacts({ search: query });
        if (response) {
          console.log("response.data", response.data.items);
          const apiData = Array.isArray(response?.data?.items)
            ? response.data.items
            : [];
          setData(apiData);
        }
      } catch (error) {
        console.error("Database search error:", error);
        dispatch(showToast({ message: "Search failed", type: "error" }));
      } finally {
        setLoading(false);
      }
    },
    [dispatch],
  );

  // Define table columns
  const columns: TableColumn<ContactData>[] = useMemo(
    () => [
      {
        name: "id",
        selector: (row: ContactData) => row.id || "-",
        sortable: true,
        width: "5%",
        cell: (row: ContactData) => (
          <div
            onClick={(e) => {
              e.stopPropagation();
              handleEdit(row);
            }}
            className="text-xs font-mono text-blue-600 dark:text-blue-400 cursor-pointer hover:underline"
          >
            {row.id || "-"}
          </div>
        ),
      },
      {
        name: "email",
        selector: (row: ContactData) => row.email || "-",
        sortable: true,
        wrap: true,
        width: "15%",
        cell: (row: ContactData) => row.email || "-",
      },
      {
        name: "name_first",
        selector: (row: ContactData) => row.name_first || "-",
        sortable: true,
        width: "13%",
        cell: (row: ContactData) => row.name_first || "-",
      },
      {
        name: "name_last",
        selector: (row: ContactData) => row.name_last || "-",
        sortable: true,
        width: "13%",
        cell: (row: ContactData) => row.name_last || "-",
      },
      {
        name: "company",
        selector: (row: ContactData) => row.company || "-",
        sortable: true,
        width: "15%",
        cell: (row: ContactData) => row.company || "-",
      },
      {
        name: "role",
        selector: (row: ContactData) => row.role || "-",
        sortable: true,
        width: "10%",
        cell: (row: ContactData) => row.role || "-",
      },
      {
        name: "is_active",
        selector: (row: ContactData) => (row.is_active ? "Yes" : "No"),
        sortable: true,
        width: "8%",
        cell: (row: ContactData) =>
          row.is_active ? (
            <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
              {"Yes"}
            </span>
          ) : (
            <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-red-500 dark:bg-red-500 dark:text-blue-200">
              {"No"}
            </span>
          ),
      },
      {
        name: "is_staff",
        selector: (row: ContactData) => (row.is_staff ? "Yes" : "No"),
        sortable: true,
        width: "8%",
        cell: (row: ContactData) =>
          row.is_staff ? (
            <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
              {"Yes"}
            </span>
          ) : (
            <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-red-500 dark:bg-red-500 dark:text-blue-200">
              {"No"}
            </span>
          ),
      },
      {
        name: "Actions",
        width: "140px",
        cell: (row: ContactData) => (
          <div className="flex items-center gap-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleView(row);
              }}
              className="p-2 text-blue-600 hover:bg-blue-50 rounded dark:hover:bg-blue-900/20 transition-colors"
              title="View"
            >
              <FaEye className="w-4 h-4" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleEdit(row);
              }}
              className="p-2 text-green-600 hover:bg-green-50 rounded dark:hover:bg-green-900/20 transition-colors"
              title="Edit"
            >
              <FaEdit className="w-4 h-4" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleDeleteRow(row);
              }}
              className="p-2 text-red-600 hover:bg-red-50 rounded dark:hover:bg-red-900/20 transition-colors"
              title="Delete"
            >
              <FaTrash className="w-4 h-4" />
            </button>
          </div>
        ),
      },
    ],
    [handleEdit, handleView, handleDeleteRow],
  );

  // Define filters
  const filters: ColumnFilter[] = useMemo(
    () => [
      {
        key: "id",
        label: "id",
        type: "text",
      },
      {
        key: "email",
        label: "email",
        type: "text",
      },
      {
        key: "name_first",
        label: "name_first",
        type: "text",
      },
      {
        key: "name_last",
        label: "name_last",
        type: "text",
      },
      {
        key: "company",
        label: "company",
        type: "text",
      },
      {
        key: "role",
        label: "role",
        type: "text",
      },
      // {
      //   key: "is_active",
      //   label: "is_active",
      //   type: "text",
      // },
      // {
      //   key: "is_staff",
      //   label: "is_staff",
      //   type: "text",
      // },
    ],
    [],
  );

  // Handle view action
  function handleView(row: ContactData) {
    setSelectedContact(row);
    setFormMode("view");
    setDetailKey((k) => k + 1);
  }

  // Handle edit action
  async function handleEdit(row: ContactData) {
    // Set selected item immediately using row data
    setSelectedContact(row);
    setFormMode("edit");
    setDetailKey((k) => k + 1);

    // Optionally fetch fresh data
    try {
      const res = await getRecord("contact", Number(row.id));
      if (res.record) setSelectedContact(res.record);
    } catch {
      // Keep using row data on error
    }
  }

  // Handle delete action (row-level)
  async function handleDeleteRow(row: ContactData) {
    const id = Number(row?.id);
    if (!Number.isFinite(id) || id <= 0) return;

    if (!window.confirm(`Delete contact #${id}?`)) return;

    try {
      await deleteRecord("contact", id);

      // Update UI immediately
      setData((prev) => prev.filter((r) => Number(r?.id) !== id));
      setSelectedContacts((prev) => prev.filter((r) => Number(r?.id) !== id));

      // If the deleted record is open in the inline detail, close it
      if (Number(selectedContact?.id) === id) {
        setSelectedContact(null);
        setFormMode(null);
      }

      dispatch(showToast({ message: "Contact deleted", type: "success" }));
    } catch (error) {
      console.error("[ContactList] delete failed:", error);
      dispatch(
        showToast({ message: "Failed to delete contact", type: "error" }),
      );
    }
  }

  // Handle add new action - navigate to separate page
  const handleAdd = () => {
    setSelectedContact(null);
    setFormMode("add");
    setDetailVariant(1);
    setDetailKey((k) => k + 1);
  };

  // Handle form saved
  const handleFormSaved = () => {
    fetchActions();
    setFormMode(null);
    setSelectedContact(null);
  };

  // Handle form cancel
  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedContact(null);
  };
  const roleLabel = useMemo(() => {
    const roleValue = user?.role;
    if (!roleValue) return "Not assigned";
    if (Array.isArray(roleValue)) {
      return roleValue.length ? roleValue.join(", ") : "Not assigned";
    }
    return roleValue;
  }, [user?.role]);

  const emptyStateMessage = useMemo(
    () => `There are no records to display for Role: ${roleLabel}`,
    [roleLabel],
  );

  const customActions = (
    <div className="flex gap-2">
      <button
        onClick={handleAdd}
        className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
      >
        <FaPlus className="w-3 h-3" />
      </button>
    </div>
  );

  const exportColumns = useMemo(
    () =>
      columns.map((col) => ({
        name: typeof col.name === "string" ? col.name : undefined,
        selector: typeof col.selector === "function" ? col.selector : undefined,
      })),
    [columns],
  );

  return (
    <>
      <PageBreadcrumb pageTitle="Contact List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard className=" cus-bg-purple-light rounded-md">
            {formMode ? (
              <div className="flex flex-col">
                <ContactListMob
                  dataProp={data}
                  selectedContact={selectedContact}
                  handleView={handleView}
                  handleEdit={handleEdit}
                  emptyMessage={emptyStateMessage}
                  filters={filters}
                  searchPlaceholder="Search contact, name_first, name_last..."
                  enableDatabaseSearch={true}
                  searchDatabase={searchDatabase}
                  onSearchModeChange={setSearchDatabase}
                  onDatabaseSearch={handleDatabaseSearch}
                  enableExport={true}
                  exportFileName="contact_export"
                  customActions={customActions}
                  loading={loading}
                  columnsForExport={exportColumns}
                />
              </div>
            ) : (
              <AdvancedDataTable
                data={data}
                columns={columns}
                title="Contact"
                loading={loading}
                filters={filters}
                enableExport={true}
                enableSelection={true}
                enableDatabaseSearch={true}
                searchDatabase={searchDatabase}
                onSearchModeChange={setSearchDatabase}
                onDatabaseSearch={handleDatabaseSearch}
                onSelectionChange={setSelectedContacts}
                exportFileName="contact_export"
                searchPlaceholder="Search contact, name_first, name_last..."
                noDataMessage="No contact found"
                customActions={customActions}
                onRowClicked={handleView}
              />
            )}
          </ComponentCard>
        </div>

        {formMode && (
          <div className="lg:col-span-2">
            {/* ── Detail variant selector badges ── */}
            <div className="flex items-center gap-2 mb-2 px-1">
              {([1, 2, 3] as const).map((v) => (
                <button
                  key={v}
                  type="button"
                  onClick={() => setDetailVariant(v)}
                  className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
                    detailVariant === v
                      ? "bg-blue-600 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600"
                  }`}
                >
                  Detail{v > 1 ? ` ${v}` : ""}
                </button>
              ))}
            </div>

            {detailVariant === 1 && (
              <ContactDetail
                key={`${detailKey}-1`}
                inline
                modeProp={formMode}
                dataProp={selectedContact}
                onSaved={handleFormSaved}
                onCancelInline={handleFormCancel}
              />
            )}
            {detailVariant === 2 && (
              <ContactDetail2
                key={`${detailKey}-2`}
                inline
                modeProp={formMode}
                dataProp={selectedContact}
                onSaved={handleFormSaved}
                onCancelInline={handleFormCancel}
              />
            )}
            {detailVariant === 3 && (
              <ContactDetail3
                key={`${detailKey}-3`}
                inline
                modeProp={formMode}
                dataProp={selectedContact}
                onSaved={handleFormSaved}
                onCancelInline={handleFormCancel}
              />
            )}
          </div>
        )}
      </div>
    </>
  );
};

export default ContactList;
