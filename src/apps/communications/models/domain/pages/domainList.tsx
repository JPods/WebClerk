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
    null,
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

  const handleView = (row: dynamicData) => {
    setSelectedEmail(row);
    setFormMode("view");
  };

  const handleEdit = async (row: dynamicData) => {
    try {
      const res = await fetchDomains(row.id);
      if (res.status === 200) setSelectedEmail(res?.data?.items);
      else setSelectedEmail(row);
    } catch (error) {
      setSelectedEmail(row);
    }
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedEmail(null);
    setFormMode("add");
  };

  const handleDelete = async (row: dynamicData) => {
    if (window.confirm(`Delete domain ${row.id}?`)) {
      try {
        await deleteDomain(row.id);
        dispatch(
          showToast({
            message: "Domain deleted successfully",
            type: "success",
          }),
        );
        getEmailData(); // Refresh data
        if (selectedEmail && selectedEmail.id === row.id) {
          setFormMode(null);
          setSelectedEmail(null);
        }
      } catch (error) {
        dispatch(
          showToast({
            message: "Failed to delete domain",
            type: "error",
          }),
        );
      }
    }
  };

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

  const handleBulkDelete = async () => {
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
  };
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
        getValue: (row) => (row.path ? String(row.path) : "--"),
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
    ],
    [columnConfig, handleDelete, handleEdit, handleView],
  );

  return (
    <>
      <PageBreadcrumb pageTitle="Domain List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="w-full overflow-x-auto rounded-md cus-bg-purple-light dark:bg-[#1e2636] h-[calc(100vh-265px)]">
              {formMode ? (
                <DomainListMob
                  dataProp={data}
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
                  enableSelection={true}
                  enableDatabaseSearch={true}
                  searchDatabase={searchDatabase}
                  onSearchModeChange={setSearchDatabase}
                  onDatabaseSearch={handleDatabaseSearch}
                  onSelectionChange={setSelectedDomains}
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
                        onClick={handleAdd}
                        className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        <FaPlus className="w-4 h-4" />
                        New Domain
                      </button>
                    </div>
                  }
                  onRowClicked={handleEdit}
                  rowClickMode="onlyIdAndActions"
                  rowClickAllowedColumnNames={["id", "action", "actions"]}
                  rowKeyField="id"
                />
              )}
            </div>
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

type DomainListCardsProps = {
  data: dynamicData[];
  columns: DomainColumnConfig[];
  onView: (row: dynamicData) => void;
  onEdit: (row: dynamicData) => void;
};

function DomainListCards({
  data,
  columns,
  onView,
  onEdit,
}: DomainListCardsProps) {
  return (
    <div className="flex flex-col">
      {data.map((row, index) => (
        <div
          key={row.id ?? `domain-card-${index}`}
          className="flex flex-col min-h-55 border-t"
        >
          <div className="space-y-1 text-sm px-2 py-3">
            {columns.map((column) => (
              <p key={`${column.key}-${row.id ?? index}`}>
                <strong>{column.label}:</strong>{" "}
                {column.renderCell
                  ? column.renderCell(row)
                  : column.getValue(row)}
              </p>
            ))}
          </div>
          <div className="mt-auto px-2 pb-3 border-t flex justify-end gap-1 bg-white sticky bottom-0">
            <button
              onClick={() => onView(row)}
              title="View"
              className="h-6.25 w-6.25 flex items-center justify-center border rounded-md hover:text-green-600"
            >
              <FaEye className="text-green-600 hover:scale-110" />
            </button>
            <button
              onClick={() => onEdit(row)}
              title="Edit"
              className="h-6.25 w-6.25 flex items-center justify-center border rounded-md hover:text-blue-600"
            >
              <FaEdit className="text-blue-600 hover:scale-110" />
            </button>
          </div>
        </div>
      ))}
      {!data.length && (
        <p className="text-center text-gray-500 py-6">No domain found.</p>
      )}
    </div>
  );
}
