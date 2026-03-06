import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, {
  ColumnFilter,
  type AdvancedDataTableHandle,
} from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { getRecord } from "../../../../../api/wcapi";
import { fetchAddresses, deleteAddress } from "../services/addressApi";
import { FaTrash, FaPlus } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import AddressDetail from "./AddressDetail";
import { dynamicData } from "../../../../../model/dynamicData";
import ButtonToolbar from "@/components/common/ButtonToolbar";

export default function AddressList() {
  const [data, setData] = useState<dynamicData[]>([]);
  const [selectedAddresses, setSelectedAddresses] = useState<dynamicData[]>([]);
  const [selectedAddress, setSelectedAddress] = useState<dynamicData | null>(
    null,
  );
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    null,
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
  const getAddressData = useCallback(async (addressId?: number) => {
    setLoading(true);
    try {
      const res = await fetchAddresses();
      setData(res.data.items);
      if (addressId) {
        const contactRes = await getRecord("address", addressId);
        setSelectedAddress(contactRes.record);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    getAddressData();
  }, [getAddressData]);

  // Handle database search
  const handleDatabaseSearch = useCallback(
    async (terms: string[]) => {
      const query = terms.join(" ");
      setLoading(true);
      try {
        const res = await fetchAddresses({ search: query });
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
    setSelectedAddress(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback(async (row: dynamicData) => {
    // Set selected item immediately using row data
    setSelectedAddress(row);
    setFormMode("edit");

    // Optionally fetch fresh data
    try {
      const res = await fetchAddresses(row.id);
      if (res.status === 200 && res.data.items) {
        const items = res.data.items;
        const item = Array.isArray(items)
          ? items.find((i: dynamicData) => String(i.id) === String(row.id))
          : items;
        if (item) setSelectedAddress(item);
      }
    } catch (error) {
      // Keep using row data on error
    }
  }, []);

  const handleAdd = () => {
    setSelectedAddress(null);
    setFormMode("add");
  };

  const handleDelete = useCallback(
    async (row: dynamicData) => {
      if (!window.confirm(`Delete address ${row.address1}?`)) return;

      try {
        await deleteAddress(row.id);
        dispatch(
          showToast({
            message: "Address deleted successfully",
            type: "success",
          }),
        );
        getAddressData();
        // Clear selection if deleted row was selected
        setSelectedAddress((prev) => (prev?.id === row.id ? null : prev));
        setFormMode((prev) => (selectedAddress?.id === row.id ? null : prev));
      } catch (error) {
        dispatch(
          showToast({
            message: "Failed to delete address",
            type: "error",
          }),
        );
      }
    },
    [dispatch, getAddressData, selectedAddress?.id],
  );

  const handleFormSaved = () => {
    getAddressData();
    setFormMode(null);
    setSelectedAddress(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedAddress(null);
  };

  const filters: ColumnFilter[] = useMemo(() => {
    const countries = Array.from(
      new Set(data.map((row) => (row.country ? String(row.country) : ""))),
    )
      .filter(Boolean)
      .map((value) => ({ value, label: value }));
    const types = Array.from(
      new Set(
        data.map((row) => (row.address_type ? String(row.address_type) : "")),
      ),
    )
      .filter(Boolean)
      .map((value) => ({ value, label: value }));

    const next: ColumnFilter[] = [];
    if (countries.length) {
      next.push({
        key: "country",
        label: "Country",
        type: "select",
        options: countries,
      });
    }
    if (types.length) {
      next.push({
        key: "address_type",
        label: "Type",
        type: "select",
        options: types,
      });
    }
    return next;
  }, [data]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedAddresses.length) return;
    if (!window.confirm(`Delete ${selectedAddresses.length} addresses?`))
      return;

    try {
      await Promise.all(selectedAddresses.map((row) => deleteAddress(row.id)));
      dispatch(
        showToast({
          message: "Addresses deleted successfully",
          type: "success",
        }),
      );
      setSelectedAddresses([]);
      getAddressData();
    } catch (error) {
      dispatch(
        showToast({
          message: "Failed to delete addresses",
          type: "error",
        }),
      );
    }
  }, [selectedAddresses, dispatch, getAddressData]);

  const columns: TableColumn<dynamicData>[] = useMemo(
    () => [
      {
        name: "id",
        selector: (row: dynamicData) => row.id,
        sortable: true,
        width: "6%",
      },
      {
        name: "contact",
        selector: (row: dynamicData) =>
          row?.refs?.links?.contact?.[0]?.contact?.display_name || "--",
        cell: (row: dynamicData) =>
          row?.refs?.links?.contact?.[0]?.contact?.display_name
            ? `[id: ${row?.refs?.links?.contact?.[0]?.contact?.id}] ${row?.refs?.links?.contact?.[0]?.contact?.display_name}`
            : "--",
        sortable: true,
        width: "15%",
      },
      {
        name: "address1",
        selector: (row: dynamicData) => row.address1 || "--",
        cell: (row: dynamicData) =>
          row.address1 ? row.address1.toString() : "--",
        sortable: true,
        width: "20%",
      },
      {
        name: "city",
        selector: (row: dynamicData) => row.city || "--",
        cell: (row: dynamicData) => (row.city ? row.city.toString() : "--"),
        sortable: true,
        width: "10%",
      },
      {
        name: "country",
        selector: (row: dynamicData) => row.country || "--",
        cell: (row: dynamicData) =>
          row.country ? row.country.toString() : "--",
        sortable: true,
        width: "15%",
      },
      {
        name: "address_type",
        selector: (row: dynamicData) => row.address_type || "--",
        cell: (row: dynamicData) =>
          row.address_type ? row.address_type.toString() : "--",
        sortable: true,
        width: "30%",
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
        width: "10%",
        sortable: false,
      },
    ],
    [handleDelete, handleEdit, handleView],
  );

  const customActions = (
    <div className="flex gap-2">
      <button
        onClick={handleAdd}
        className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
      >
        <FaPlus className="w-4 h-4" />
      </button>
      {selectedAddresses.length > 0 && (
        <button
          onClick={handleBulkDelete}
          className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
        >
          <FaTrash className="w-3 h-3" />({selectedAddresses.length})
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
        pageTitle="Address List"
        title="Address"
        modelKey="address"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        handleBulkDelete={handleBulkDelete}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        selectedRows={selectedAddresses}
        selectedCount={selectedAddresses.length}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={getAddressData}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={columns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="address-list"
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
              title="Addresses"
              storageKey="communications.address.list"
              loading={loading}
              filters={filters}
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedAddresses}
              onDeleteSelected={handleBulkDelete}
              enableDatabaseSearch={true}
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
              externalSearchTerm={searchTerm}
              onExternalSearchTermChange={setSearchTerm}
              filtersOpen={filtersOpen}
              onFiltersOpenChange={setFiltersOpen}
              exportFileName="addresses_export"
              searchPlaceholder="Search addresses..."
              noDataMessage="No addresses found"
              customActions={customActions}
              onRowClicked={handleView}
              rowClickMode="onlyIdAndActions"
              rowClickAllowedColumnNames={["id", "action", "actions"]}
              rowKeyField="id"
              hideHeader={true}
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <AddressDetail
              inline
              modeProp={formMode}
              dataProp={selectedAddress}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
