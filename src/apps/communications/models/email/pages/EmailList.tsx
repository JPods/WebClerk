/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import DataGrid from "@/components/common/DataGrid";
import type { ColumnFilter } from "@/components/common/ButtonToolbar";
import ComponentCard from "../../../../../components/common/ComponentCard";
import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { getRecord } from "../../../../../api/wcapi";
import { fetchEmails, deleteEmail } from "../services/emailApi";
import { FaTrash, FaPlus } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import EmailDetail from "./EmailDetail";
import Badge from "@/components/ui/badge/Badge";
import { dynamicData } from "../../../../../model/dynamicData";
import ButtonToolbar from "@/components/common/ButtonToolbar";

export default function EmailList() {
  const [data, setData] = useState<dynamicData[]>([]);
  const [selectedEmails, setSelectedEmails] = useState<dynamicData[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<dynamicData | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState<boolean[]>([]);
  const tableRef = useRef<any>(null);
  const columnBtnRef = useRef<HTMLButtonElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

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
  const columns: any[] = useMemo(
    () => [
      {
        name: "id",
        selector: (row: dynamicData) => row.id,
        sortable: true,
        width: "5%",
      },
      {
        name: "contact",
        selector: (row: dynamicData) => {
          row?.refs?.links?.contact?.[0]?.contact?.display_name;
        },
        cell: (row: dynamicData) =>
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

  // Filter data based on filterValues from ButtonToolbar
  const filteredData = useMemo(() => {
    if (Object.keys(filterValues).length === 0) return data;
    return data.filter((row: any) => {
      return Object.entries(filterValues).every(([key, value]) => {
        if (!value) return true;
        const rowValue = String(row[key] || "").toLowerCase();
        return rowValue.includes(value.toLowerCase());
      });
    });
  }, [data, filterValues]);

  // Filter columns based on visibility from ButtonToolbar
  const visibleColumns = useMemo(() => {
    if (columnVisibility.length === 0) return columns;
    return columns.filter(
      (_: any, index: number) => columnVisibility[index] !== false,
    );
  }, [columns, columnVisibility]);
  return (
    <>
      <ButtonToolbar
        pageTitle="Email List"
        title="Email"
        modelKey="email"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        handleBulkDelete={handleBulkDelete}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        selectedRows={selectedEmails}
        selectedCount={selectedEmails.length}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={getEmailData}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={columns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="email-list"
        filters={filters}
        filterValues={filterValues}
        onFilterValuesChange={setFilterValues}
        filtersOpen={filtersOpen}
        onFiltersOpenChange={setFiltersOpen}
      />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard className=" cus-bg-purple-light rounded-md">
            <DataGrid
              ref={tableRef}
              data={filteredData}
              columns={visibleColumns}
              title="Emails"
              storageKey="communications.email.list"
              loading={loading}
              filters={filters}
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedEmails}
              onDeleteSelected={handleBulkDelete}
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
              externalSearchTerm={searchTerm}
              onExternalSearchTermChange={setSearchTerm}
              filtersOpen={filtersOpen}
              onFiltersOpenChange={setFiltersOpen}
              hideHeader={true}
            />
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
