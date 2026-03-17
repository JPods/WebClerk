/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, {
  ColumnFilter,
  type AdvancedDataTableHandle,
} from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { getRecord } from "../../../../../api/wcapi";
import { fetchDomains, deleteDomain } from "../services/domainApi";
import { FaTrash, FaPlus } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import DomainDetail from "./DomainDetail";
import { dynamicData } from "../../../../../model/dynamicData";
import ButtonToolbar from "@/components/common/ButtonToolbar";

export default function DomainList() {
  const [data, setData] = useState<dynamicData[]>([]);
  const [selectedDomains, setSelectedDomains] = useState<dynamicData[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<dynamicData | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    "view",
  );
  const [loading, setLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState<boolean[]>([]);
  const tableRef = useRef<AdvancedDataTableHandle<any>>(null);
  const columnBtnRef = useRef<HTMLButtonElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  const dispatch = useDispatch();
  const getEmailData = useCallback(async (emailId?: number) => {
    setLoading(true);
    try {
      const res = await fetchDomains();
      setData(res?.data?.items);
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
        const res = await fetchDomains({ search: query });
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
      const res = await fetchDomains(row.id);
      if (res.status === 200 && res?.data?.items) {
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
      if (!window.confirm(`Delete domain ${row.id}?`)) return;

      try {
        await deleteDomain(row.id);
        dispatch(
          showToast({
            message: "Domain deleted successfully",
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
            message: "Failed to delete domain",
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

  const filters: ColumnFilter[] = useMemo(() => {
    const types = Array.from(
      new Set(data.map((row) => (row.type ? String(row.type) : ""))),
    )
      .filter(Boolean)
      .map((value) => ({ value, label: value }));

    return types.length
      ? [
          {
            key: "type",
            label: "Type",
            type: "select",
            options: types,
          },
        ]
      : [];
  }, [data]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedDomains.length) return;
    if (!window.confirm(`Delete ${selectedDomains.length} domains?`)) return;

    try {
      await Promise.all(selectedDomains.map((row) => deleteDomain(row.id)));
      dispatch(
        showToast({
          message: "Domains deleted successfully",
          type: "success",
        }),
      );
      setSelectedDomains([]);
      getEmailData();
    } catch (error) {
      dispatch(
        showToast({
          message: "Failed to delete domains",
          type: "error",
        }),
      );
    }
  }, [selectedDomains, dispatch, getEmailData]);

  const toggleSelectDomain = useCallback((row: dynamicData) => {
    setSelectedDomains((prev) => {
      const exists = prev.some((r) => r.id === row.id);
      if (exists) {
        return prev.filter((r) => r.id !== row.id);
      }
      return [...prev, row];
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    setSelectedDomains((prev) => {
      if (prev.length === data.length) {
        return [];
      }
      return [...data];
    });
  }, [data]);

  /* ---------------- Columns ---------------- */
  const columns: TableColumn<dynamicData>[] = useMemo(
    () => [
      {
        name: "id",
        selector: (row: dynamicData) =>
          row.id !== undefined ? String(row.id) : "--",
        sortable: true,
        width: "5%",
      },
      {
        name: "contact",
        selector: (row: dynamicData) =>
          row?.refs?.links?.contact?.[0]?.contact?.display_name ?? "--",
        cell: (row: dynamicData) =>
          row?.refs?.links?.contact?.[0]?.contact?.display_name
            ? `[id: ${row?.refs?.links?.contact?.[0]?.contact?.id}] ${row?.refs?.links?.contact?.[0]?.contact?.display_name}`
            : "--",
        sortable: true,
        width: "15%",
      },
      {
        name: "path",
        selector: (row: dynamicData) =>
          row.path
            ? String(row.path).length > 160
              ? `${String(row.path).slice(0, 160)}...`
              : String(row.path)
            : "--",
        sortable: true,
        width: "60%",
      },
      {
        name: "type",
        selector: (row: dynamicData) => (row.type ? String(row.type) : "--"),
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
      selectedDomains,
      data.length,
      toggleSelectDomain,
      toggleSelectAll,
    ],
  );

  const customActions = (
    <div className="flex gap-2">
      <button
        onClick={handleAdd}
        className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
      >
        <FaPlus className="w-3 h-3" />
      </button>
      {selectedDomains.length > 0 && (
        <button
          onClick={handleBulkDelete}
          className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
        >
          <FaTrash className="w-3 h-3" />({selectedDomains.length})
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
        pageTitle="Domain List"
        title="Domain"
        modelKey="domain"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        handleBulkDelete={handleBulkDelete}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        selectedRows={selectedDomains}
        selectedCount={selectedDomains.length}
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
        storageKey="domain-list"
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
              title="Domains"
              storageKey="communications.domain.list"
              loading={loading}
              filters={filters}
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedDomains}
              onDeleteSelected={handleBulkDelete}
              enableDatabaseSearch={true}
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
              exportFileName="domains_export"
              searchPlaceholder="Search domains..."
              noDataMessage="No domains found"
              customActions={customActions}
              //onRowClicked={handleView}
              onRowDoubleClicked={handleView}
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
            <DomainDetail
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
