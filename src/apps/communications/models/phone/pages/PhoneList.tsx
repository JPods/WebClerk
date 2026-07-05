/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import DataGrid from "@/components/common/DataGrid";
import type { ColumnFilter } from "@/components/common/ButtonToolbar";
import ComponentCard from "../../../../../components/common/ComponentCard";
import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { fetchPhones, deletePhone } from "../services/phoneApi";
import { getRecord } from "../../../../../api/wcapi";
import { FaTrash, FaPlus } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import PhoneDetail from "./PhoneDetail";
import { dynamicData } from "../../../../../model/dynamicData";
import ButtonToolbar from "@/components/common/ButtonToolbar";
import { defaultCountries, usePhoneInput } from "react-international-phone";
import { useColumnContextMenu } from "@/hooks/useColumnContextMenu";

export default function PhoneList() {
  const [data, setData] = useState<dynamicData[]>([]);
  const [selectedPhones, setSelectedPhones] = useState<dynamicData[]>([]);
  const [selectedPhone, setSelectedPhone] = useState<dynamicData | null>(null);
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
  const getPhoneData = useCallback(async (phoneId?: number) => {
    setLoading(true);
    try {
      const res = await fetchPhones();
      setData(res.data.items);
      if (phoneId) {
        const contactRes = await getRecord("contact", phoneId);
        setSelectedPhone(contactRes.record);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    getPhoneData();
  }, [getPhoneData]);

  // Handle database search
  const handleDatabaseSearch = useCallback(
    async (terms: string[]) => {
      const query = terms.join(" ");
      setLoading(true);
      try {
        const res = await fetchPhones({ search: query });
        setData(res.data.items);
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
    setSelectedPhone(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback(async (row: dynamicData) => {
    // Set selected item immediately using row data
    setSelectedPhone(row);
    setFormMode("edit");

    // Optionally fetch fresh data
    try {
      const res = await fetchPhones(row.id);
      if (res.status === 200 && res.data.items) {
        const items = res.data.items;
        const item = Array.isArray(items)
          ? items.find((i: dynamicData) => String(i.id) === String(row.id))
          : items;
        if (item) setSelectedPhone(item);
      }
    } catch (error) {
      // Keep using row data on error
    }
  }, []);

  const handleAdd = () => {
    setSelectedPhone(null);
    setFormMode("add");
  };

  const handleDelete = useCallback(
    async (row: dynamicData) => {
      if (!window.confirm(`Delete phone ${row.number}?`)) return;

      try {
        await deletePhone(row.id);
        dispatch(
          showToast({
            message: "Phone deleted successfully",
            type: "success",
          }),
        );
        getPhoneData();
        // Clear selection if deleted row was selected
        setSelectedPhone((prev) => (prev?.id === row.id ? null : prev));
        setFormMode((prev) => (selectedPhone?.id === row.id ? null : prev));
      } catch (error) {
        dispatch(
          showToast({
            message: "Failed to delete phone",
            type: "error",
          }),
        );
      }
    },
    [dispatch, getPhoneData, selectedPhone?.id],
  );

  const handleFormSaved = () => {
    getPhoneData();
    setFormMode(null);
    setSelectedPhone(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedPhone(null);
  };

  const filters: ColumnFilter[] = useMemo(() => {
    const countryCodes = Array.from(
      new Set(
        data.map((row) => (row.country_code ? String(row.country_code) : "")),
      ),
    )
      .filter(Boolean)
      .map((value) => ({ value, label: value }));

    return [
      {
        key: "opt_out",
        label: "Opt Out",
        type: "select",
        options: [
          { value: "true", label: "Yes" },
          { value: "false", label: "No" },
        ],
      },
      ...(countryCodes.length
        ? [
            {
              key: "country_code",
              label: "Country Code",
              type: "select",
              options: countryCodes,
            } as ColumnFilter,
          ]
        : []),
    ];
  }, [data]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedPhones.length) return;
    if (!window.confirm(`Delete ${selectedPhones.length} phones?`)) return;

    try {
      await Promise.all(selectedPhones.map((row) => deletePhone(row.id)));
      dispatch(
        showToast({
          message: "Phones deleted successfully",
          type: "success",
        }),
      );
      setSelectedPhones([]);
      getPhoneData();
    } catch (error) {
      dispatch(
        showToast({
          message: "Failed to delete phones",
          type: "error",
        }),
      );
    }
  }, [selectedPhones, dispatch, getPhoneData]);

  const toggleSelectPhone = useCallback((row: dynamicData) => {
    setSelectedPhones((prev) => {
      const exists = prev.some((r) => r.id === row.id);
      if (exists) {
        return prev.filter((r) => r.id !== row.id);
      }
      return [...prev, row];
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    setSelectedPhones((prev) => {
      if (prev.length === data.length) {
        return [];
      }
      return [...data];
    });
  }, [data]);

  /**
   * PhoneDisplay - Format and display phone numbers using react-international-phone
   * Uses the library's formatting logic for consistent display with the input component
   */
  const PhoneDisplay: React.FC<{ value?: string | null }> = ({ value }) => {
    const { inputValue } = usePhoneInput({
      value: value || "",
      countries: defaultCountries,
      defaultCountry: "us",
      forceDialCode: true,
    });

    if (!value) return <>--</>;
    return <>{inputValue}</>;
  };

  // Columns hook - similar pattern to useCustomerColumns
  const usePhoneColumns = (
    handleDelete: (row: dynamicData) => void,
  ): any[] =>
    useMemo(
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
          name: "number",
          selector: (row: dynamicData) => row.number || "--",
          cell: (row: dynamicData) => <PhoneDisplay value={row.number} />,
          sortable: true,
          width: "20%",
        },
        {
          name: "name",
          selector: (row: dynamicData) => row.name || "--",
          cell: (row: dynamicData) => (row.name ? row.name.toString() : "--"),
          sortable: true,
          width: "25%",
        },

        {
          name: "country_code",
          selector: (row: dynamicData) => row.country_code || "--",
          cell: (row: dynamicData) =>
            row.country_code ? row.country_code.toString() : "--",
          sortable: true,
          width: "15%",
        },

        {
          name: "opt_out",
          selector: (row: dynamicData) => (row.opt_out ? "Yes" : "No"), // Plain string for filtering
          cell: (row: dynamicData) => (row.opt_out ? "Yes" : "No"),
          sortable: true,
          width: "15%",
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
      [handleDelete],
    );

  const columns = usePhoneColumns(handleDelete);

  const customActions = (
    <div className="flex gap-2">
      <button
        onClick={handleAdd}
        className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
      >
        <FaPlus className="w-4 h-4" />
      </button>
      {selectedPhones.length > 0 && (
        <button
          onClick={handleBulkDelete}
          className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
        >
          <FaTrash className="w-3 h-3" />({selectedPhones.length})
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

  const columnCtx = useColumnContextMenu("communications.phone.list", visibleColumns);
  return (
    <>
      <ButtonToolbar
        pageTitle="Phone List"
        title="Phone"
        modelKey="phone"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        handleBulkDelete={handleBulkDelete}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        selectedRows={selectedPhones}
        selectedCount={selectedPhones.length}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={getPhoneData}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={columns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="phone-list"
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
              title="Phones"
              storageKey="communications.phone.list"
              loading={loading}
              filters={filters}
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedPhones}
              onDeleteSelected={handleBulkDelete}
              enableDatabaseSearch={true}
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
              exportFileName="phones_export"
              searchPlaceholder="Search phones..."
              noDataMessage="No phones found"
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
              allFields={columnCtx.allFields}
              namedViews={columnCtx.namedViews}
              onDeleteColumn={columnCtx.onDeleteColumn}
              onAddColumn={columnCtx.onAddColumn}
              onSaveLayout={columnCtx.onSaveLayout}
              onSaveLayoutAs={columnCtx.onSaveLayoutAs}
              onLoadView={columnCtx.onLoadView}
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <PhoneDetail
              inline
              modeProp={formMode}
              dataProp={selectedPhone}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
