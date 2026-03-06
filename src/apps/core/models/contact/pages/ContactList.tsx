import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { TableColumn } from "react-data-table-component";
import { FaPlus, FaEye, FaEdit, FaTrash } from "react-icons/fa";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, {
  ColumnFilter,
  AdvancedDataTableHandle,
} from "../../../../../components/common/AdvancedDataTable";
import { fetchContacts } from "../services/contactApi";
import { useDispatch } from "react-redux";
import { showToast } from "../../../../../store/slices/toastSlice";
import ContactDetail from "./ContactDetail";
import ContactDetail2 from "./ContactDetail2";
import ContactDetail3 from "./ContactDetail3";
import { deleteRecord, getRecord } from "../../../../../api/wcapi";
import ButtonToolbar from "@/components/common/ButtonToolbar";
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
  const [searchTerm, setSearchTerm] = useState("");
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState<boolean[]>([]);
  const tableRef = useRef<AdvancedDataTableHandle<ContactData>>(null);
  const columnBtnRef = useRef<HTMLButtonElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

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

  // Filter columns based on visibility from PageBreadcrumb
  const visibleColumns = useMemo(() => {
    if (columnVisibility.length === 0) return columns;
    return columns.filter((_, index) => columnVisibility[index] !== false);
  }, [columns, columnVisibility]);

  // Filter data based on filterValues from PageBreadcrumb
  const filteredData = useMemo(() => {
    if (Object.keys(filterValues).length === 0) return data;

    return data.filter((row) => {
      return Object.entries(filterValues).every(([key, value]) => {
        if (!value) return true; // Skip empty filters
        const rowValue = String(row[key] || "").toLowerCase();
        return rowValue.includes(value.toLowerCase());
      });
    });
  }, [data, filterValues]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedContacts.length) return;
    if (!window.confirm(`Delete ${selectedContacts.length} contact(s)?`))
      return;
    setLoading(true);
    try {
      for (const row of selectedContacts) {
        const id = Number(row?.id);
        if (Number.isFinite(id) && id > 0) {
          await deleteRecord("contact", id);
        }
      }
      setData((prev) =>
        prev.filter(
          (r) =>
            !selectedContacts.some((sc) => Number(sc?.id) === Number(r?.id)),
        ),
      );
      setSelectedContacts([]);
      dispatch(showToast({ message: "Contacts deleted", type: "success" }));
    } catch (error) {
      console.error("[ContactList] bulk delete failed:", error);
      dispatch(
        showToast({ message: "Failed to delete contacts", type: "error" }),
      );
    } finally {
      setLoading(false);
    }
  }, [selectedContacts, dispatch]);
  return (
    <>
      <ButtonToolbar
        pageTitle="Contact List"
        title="Contact"
        modelKey="contact"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        handleBulkDelete={handleBulkDelete}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        selectedRows={selectedContacts}
        selectedCount={selectedContacts.length}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={fetchActions}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        // Column management
        columns={columns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="contact-list"
        // Filters
        filters={filters}
        filterValues={filterValues}
        onFilterValuesChange={setFilterValues}
        filtersOpen={filtersOpen}
        onFiltersOpenChange={setFiltersOpen}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard className=" cus-bg-purple-light rounded-md">
            <AdvancedDataTable
              ref={tableRef}
              data={filteredData}
              columns={visibleColumns}
              title="Contact"
              loading={loading}
              hideHeader={true}
              enableExport={true}
              enableSelection={true}
              enableDatabaseSearch={true}
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
              onSelectionChange={setSelectedContacts}
              onDeleteSelected={handleBulkDelete}
              externalSearchTerm={searchTerm}
              onExternalSearchTermChange={setSearchTerm}
              filtersOpen={filtersOpen}
              onFiltersOpenChange={setFiltersOpen}
              exportFileName="contact_export"
              searchPlaceholder="Search contact, name_first, name_last..."
              noDataMessage="No contact found"
              customActions={customActions}
              onRowClicked={handleView}
            />
            {/* )} */}
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
