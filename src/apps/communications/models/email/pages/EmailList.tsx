import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, {
  ColumnFilter,
} from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { getRecord } from "../../../../../api/wcapi";
import { fetchEmails, deleteEmail } from "../services/emailApi";
import { FaEye, FaEdit, FaTrash, FaPlus } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import EmailDetail from "./EmailDetail";
import Badge from "@/components/ui/badge/Badge";
import { dynamicData } from "../../../../../model/dynamicData";
import EmailListMob from "./EmailListMob";

export default function EmailList() {
  const [data, setData] = useState<dynamicData[]>([]);
  const [selectedEmails, setSelectedEmails] = useState<dynamicData[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<dynamicData | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);

  const dispatch = useDispatch();
  const getEmailData = useCallback(async (emailId?: number) => {
    setLoading(true);
    try {
      const response = await fetchEmails();
      if (response.status === 200) {
        setData(response?.data?.items);
      }
      if (emailId) {
        const contactRes = await getRecord("contact", emailId);
        setSelectedEmail(contactRes.record);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    getEmailData();
  }, [getEmailData]);

  // Handle database search
  const handleDatabaseSearch = useCallback(
    async (terms: string[]) => {
      const query = terms.join(" ");
      setLoading(true);
      try {
        const res = await fetchEmails({ search: query });
        setData(res?.data?.items);
      } catch (error) {
        console.error("Database search error:", error);
        dispatch(showToast({ message: "Search failed", type: "error" }));
      } finally {
        setLoading(false);
      }
    },
    [dispatch],
  );

  const handleView = useCallback((row: dynamicData) => {
    setSelectedEmail(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback(async (row: dynamicData) => {
    // Set selected item immediately using row data
    setSelectedEmail(row);
    setFormMode("edit");

    // Optionally fetch fresh data
    try {
      const res = await fetchEmails(row.id);
      if (res.status === 200 && res.data.items) {
        const items = res.data.items;
        const item = Array.isArray(items)
          ? items.find((i: dynamicData) => String(i.id) === String(row.id))
          : items;
        if (item) setSelectedEmail(item);
      }
    } catch (error) {
      // Keep using row data on error
    }
  }, []);

  const handleAdd = () => {
    setSelectedEmail(null);
    setFormMode("add");
  };

  const handleDelete = useCallback(
    async (row: dynamicData) => {
      if (!window.confirm(`Delete email ${row.id}?`)) return;

      try {
        await deleteEmail("email", row.id);
        dispatch(
          showToast({
            message: "Email deleted successfully",
            type: "success",
          }),
        );
        getEmailData();
        // Clear selection if deleted row was selected
        setSelectedEmail((prev) => (prev?.id === row.id ? null : prev));
        setFormMode((prev) => (selectedEmail?.id === row.id ? null : prev));
      } catch (error) {
        dispatch(
          showToast({
            message: "Failed to delete email",
            type: "error",
          }),
        );
      }
    },
    [dispatch, getEmailData, selectedEmail?.id],
  );

  const handleFormSaved = () => {
    getEmailData();
    setFormMode(null);
    setSelectedEmail(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedEmail(null);
  };

  const filters: ColumnFilter[] = useMemo(
    () => [
      {
        key: "is_primary",
        label: "Primary",
        type: "select",
        options: [
          { value: "true", label: "Yes" },
          { value: "false", label: "No" },
        ],
      },
      {
        key: "is_verified",
        label: "Verified",
        type: "select",
        options: [
          { value: "true", label: "Yes" },
          { value: "false", label: "No" },
        ],
      },
    ],
    [],
  );

  const handleBulkDelete = useCallback(async () => {
    if (!selectedEmails.length) return;
    if (!window.confirm(`Delete ${selectedEmails.length} emails?`)) return;

    try {
      await Promise.all(
        selectedEmails.map((row) => deleteEmail("email", row.id)),
      );
      dispatch(
        showToast({
          message: "Emails deleted successfully",
          type: "success",
        }),
      );
      setSelectedEmails([]);
      getEmailData();
    } catch (error) {
      dispatch(
        showToast({
          message: "Failed to delete emails",
          type: "error",
        }),
      );
    }
  }, [selectedEmails, dispatch, getEmailData]);

  const toggleSelectEmail = useCallback((row: dynamicData) => {
    setSelectedEmails((prev) => {
      const exists = prev.some((r) => r.id === row.id);
      if (exists) {
        return prev.filter((r) => r.id !== row.id);
      }
      return [...prev, row];
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    setSelectedEmails((prev) => {
      if (prev.length === data.length) {
        return [];
      }
      return [...data];
    });
  }, [data]);
  /* ---------------- Columns ---------------- */
  const userColumns: TableColumn<dynamicData>[] = useMemo(
    () => [
      {
        name: (
          <input
            type="checkbox"
            checked={selectedEmails.length === data.length && data.length > 0}
            onChange={toggleSelectAll}
            className="w-4 h-4 cursor-pointer"
          />
        ),
        cell: (row: dynamicData) => (
          <input
            type="checkbox"
            checked={selectedEmails.some((r) => r.id === row.id)}
            onChange={() => toggleSelectEmail(row)}
            className="w-4 h-4 cursor-pointer"
          />
        ),
        ignoreRowClick: true,
        allowOverflow: true,
        button: true,
        width: "50px",
        sortable: false,
        reorder: false,
      },
      {
        name: "id",
        selector: (row: dynamicData) => row.id,
        sortable: true,
        width: "5%",
      },
      {
        name: "contact",
        selector: (row) => {
          row?.refs?.links?.contact?.[0]?.contact?.display_name;
        },
        cell: (row) =>
          row?.refs?.links?.contact?.[0]?.contact?.display_name
            ? `[id: ${row?.refs?.links?.contact?.[0]?.contact?.id}] ${row?.refs?.links?.contact?.[0]?.contact?.display_name}`
            : "--",
        sortable: true,
        width: "15%",
      },
      {
        name: "email",
        selector: (row: dynamicData) => row.email || "--",
        cell: (row: dynamicData) => (row.email ? row.email.toString() : "--"),
        sortable: true,
        width: "15%",
      },
      {
        name: "name",
        selector: (row: dynamicData) => row.name || "--",
        cell: (row: dynamicData) => (row.name ? row.name.toString() : "--"),
        sortable: true,
        width: "20%",
      },

      {
        name: "attention",
        selector: (row: dynamicData) => row.attention || "--",
        cell: (row: dynamicData) =>
          row.attention ? row.attention.toString() : "--",
        sortable: true,
        width: "25%",
      },

      {
        name: "is_primary",
        selector: (row: dynamicData) => (row.is_primary ? "Yes" : "No"), // Plain string for filtering
        cell: (row: dynamicData) => (
          <>
            <Badge size="sm" color={row.is_primary ? "success" : "warning"}>
              {row.is_primary ? "Yes" : "No"}
            </Badge>
          </>
        ),
        sortable: true,
        width: "10%",
      },
      {
        name: "is_verified",
        selector: (row: dynamicData) => (row.is_verified ? "Yes" : "No"), // Plain string for filtering
        cell: (row: dynamicData) => (
          <>
            <Badge size="sm" color={row.is_verified ? "success" : "warning"}>
              {row.is_verified ? "Yes" : "No"}
            </Badge>
          </>
        ),
        sortable: true,
        width: "10%",
      },
      {
        name: "action",
        cell: (row: dynamicData) => (
          <div className="flex gap-3">
            <button onClick={() => handleDelete(row)} title="Delete">
              <FaTrash className="text-red-600 hover:scale-110 transition" />
            </button>
          </div>
        ),
        ignoreRowClick: true,
        allowOverflow: true,
        button: true,
      },
    ],
    [
      handleDelete,
      selectedEmails,
      data.length,
      toggleSelectEmail,
      toggleSelectAll,
    ],
  );

  const customActions = (
    <div className="flex gap-2">
      <button
        onClick={handleAdd}
        className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
      >
        <FaPlus className="w-4 h-4" />
      </button>
      {selectedEmails.length > 0 && (
        <button
          onClick={handleBulkDelete}
          className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
        >
          <FaTrash className="w-3 h-3" />({selectedEmails.length})
        </button>
      )}
    </div>
  );

  const exportColumns = useMemo(
    () =>
      userColumns
        .filter((col) => typeof col.name === "string")
        .map((col) => ({
          name: typeof col.name === "string" ? col.name : undefined,
          selector:
            typeof col.selector === "function" ? col.selector : undefined,
        })),
    [userColumns],
  );

  return (
    <>
      <PageBreadcrumb pageTitle="Email List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard className=" cus-bg-purple-light rounded-md">
            {formMode ? (
              <div className="flex flex-col">
                <EmailListMob
                  dataProp={data}
                  selectedEmail={selectedEmail}
                  handleView={handleView}
                  handleEdit={handleEdit}
                  emptyMessage="No emails found"
                  filters={filters}
                  searchPlaceholder="Search emails, names, attention..."
                  enableDatabaseSearch={true}
                  searchDatabase={searchDatabase}
                  onSearchModeChange={setSearchDatabase}
                  onDatabaseSearch={handleDatabaseSearch}
                  enableExport={true}
                  exportFileName="emails_export"
                  customActions={customActions}
                  loading={loading}
                  columnsForExport={exportColumns}
                />
              </div>
            ) : (
              <AdvancedDataTable
                data={data}
                columns={userColumns}
                title="Emails"
                storageKey="communications.email.list"
                loading={loading}
                filters={filters}
                enableExport={true}
                enableSelection={false}
                enableDatabaseSearch={true}
                searchDatabase={searchDatabase}
                onSearchModeChange={setSearchDatabase}
                onDatabaseSearch={handleDatabaseSearch}
                exportFileName="emails_export"
                searchPlaceholder="Search emails, names, attention..."
                noDataMessage="No emails found"
                customActions={customActions}
                onRowClicked={handleView}
                rowClickMode="onlyIdAndActions"
                rowClickAllowedColumnNames={["id", "action", "actions"]}
                rowKeyField="id"
              />
            )}
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
