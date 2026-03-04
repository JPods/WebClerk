import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, {
  ColumnFilter,
} from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import {
  useEffect,
  useState,
  useCallback,
  useMemo,
  type ReactNode,
} from "react";
import { getRecord } from "../../../../../api/wcapi";
import { fetchDomains, deleteDomain } from "../services/domainApi";
import { FaEye, FaEdit, FaTrash, FaPlus } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import DomainDetail from "./DomainDetail";
import { dynamicData } from "../../../../../model/dynamicData";
import DomainListMob from "./DomainListMob";

type DomainColumnConfig = {
  key: string;
  label: string;
  width?: string;
  sortable?: boolean;
  getValue: (row: dynamicData) => string;
  renderCell?: (row: dynamicData) => ReactNode;
};

export default function DomainList() {
  const [data, setData] = useState<dynamicData[]>([]);
  const [selectedDomains, setSelectedDomains] = useState<dynamicData[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<dynamicData | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    "view",
  );
  const [loading, setLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);

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
  const columnConfig = useMemo<DomainColumnConfig[]>(
    () => [
      {
        key: "id",
        label: "id",
        width: "5%",
        sortable: true,
        getValue: (row) => (row.id !== undefined ? String(row.id) : "--"),
      },
      {
        key: "path",
        label: "path",
        width: "75%",
        sortable: true,
        getValue: (row) =>
          row.path
            ? String(
                (row.path ?? "--").length > 160
                  ? `${(row.path ?? "--").slice(0, 160)}...`
                  : row.path ?? "--",
              )
            : "--",
      },
      {
        key: "type",
        label: "type",
        width: "10%",
        sortable: true,
        getValue: (row) => (row.type ? String(row.type) : "--"),
      },
    ],
    [],
  );

  const userColumns: TableColumn<dynamicData>[] = useMemo(
    () => [
      {
        name: (
          <input
            type="checkbox"
            checked={selectedDomains.length === data.length && data.length > 0}
            onChange={toggleSelectAll}
            className="w-4 h-4 cursor-pointer"
          />
        ),
        cell: (row: dynamicData) => (
          <input
            type="checkbox"
            checked={selectedDomains.some((r) => r.id === row.id)}
            onChange={() => toggleSelectDomain(row)}
            className="w-4 h-4 cursor-pointer"
          />
        ),
        ignoreRowClick: true,
        allowOverflow: true,
        button: true,
        width: "80px",
        sortable: false,
        reorder: false,
      },
      ...columnConfig.map((col) => ({
        name: col.label,
        selector: (row: dynamicData) => col.getValue(row),
        cell: col.renderCell ?? ((row: dynamicData) => col.getValue(row)),
        sortable: col.sortable,
        width: col.width,
      })),
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
      columnConfig,
      handleDelete,
      selectedDomains,
      data.length,
      toggleSelectDomain,
      toggleSelectAll,
    ],
  );

  return (
    <>
      <PageBreadcrumb pageTitle="Domain List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard className=" cus-bg-purple-light rounded-md">
            {formMode ? (
              <DomainListMob
                dataProp={data}
                selectedDomain={selectedEmail}
                handleView={handleView}
                handleEdit={handleEdit}
              />
            ) : (
              <AdvancedDataTable
                data={data}
                columns={userColumns}
                title="Domains"
                storageKey="communications.domain.list"
                loading={loading}
                filters={filters}
                enableExport={true}
                enableSelection={false}
                enableDatabaseSearch={true}
                searchDatabase={searchDatabase}
                onSearchModeChange={setSearchDatabase}
                onDatabaseSearch={handleDatabaseSearch}
                exportFileName="domains_export"
                searchPlaceholder="Search domains..."
                noDataMessage="No domains found"
                customActions={
                  <div className="flex gap-2">
                    {selectedDomains.length > 0 && (
                      <button
                        onClick={handleBulkDelete}
                        className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                      >
                        <FaTrash className="w-4 h-4" />
                        Delete ({selectedDomains.length})
                      </button>
                    )}
                    <button
                      onClick={handleView}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      <FaPlus className="w-4 h-4" />
                      New Domain
                    </button>
                  </div>
                }
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
