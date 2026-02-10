import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, {
  ColumnFilter,
} from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { getRecord } from "../../../../../api/wcapi";
import { fetchAddresses, deleteAddress } from "../services/addressApi";
import { FaEye, FaEdit, FaTrash, FaPlus } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import AddressDetail from "./AddressDetail";
import { dynamicData } from "../../../../../model/dynamicData";
import AddressListMob from "./AddressListMob";

export default function AddressList() {
  const [data, setData] = useState<dynamicData[]>([]);
  const [selectedAddresses, setSelectedAddresses] = useState<dynamicData[]>([]);
  const [selectedAddress, setSelectedAddress] = useState<dynamicData | null>(
    null
  );
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    null
  );
  const [loading, setLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);

  const dispatch = useDispatch();
  const getAddressData = useCallback(async (addressId?: number) => {
    setLoading(true);
    try {
      const res = await fetchAddresses();
      setData(res.data.data.results);
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
  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    const query = terms.join(' ');
    setLoading(true);
    try {
      const res = await fetchAddresses(undefined, { search: query });
      setData(res.data.data.results);
    } catch (error) {
      console.error("Database search error:", error);
      dispatch(showToast({ message: "Search failed", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  const handleView = (row: dynamicData) => {
    setSelectedAddress(row);
    setFormMode("view");
  };

  const handleEdit = async (row: dynamicData) => {
    const res = await fetchAddresses(row.id);
    if (res.status === 200) setSelectedAddress(res.data.data.record);
    else setSelectedAddress(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedAddress(null);
    setFormMode("add");
  };

  const handleDelete = async (row: dynamicData) => {
    if (window.confirm(`Delete address ${row.address1}?`)) {
      try {
        await deleteAddress(row.id);
        dispatch(
          showToast({
            message: "Address deleted successfully",
            type: "success",
          })
        );
        getAddressData();
        if (selectedAddress && selectedAddress.id === row.id) {
          setFormMode(null);
          setSelectedAddress(null);
        }
      } catch (error) {
        dispatch(
          showToast({
            message: "Failed to delete address",
            type: "error",
          })
        );
      }
    }
  };

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
      new Set(data.map((row) => (row.country ? String(row.country) : "")))
    )
      .filter(Boolean)
      .map((value) => ({ value, label: value }));
    const types = Array.from(
      new Set(data.map((row) => (row.address_type ? String(row.address_type) : "")))
    )
      .filter(Boolean)
      .map((value) => ({ value, label: value }));

    const next: ColumnFilter[] = [];
    if (countries.length) {
      next.push({ key: "country", label: "Country", type: "select", options: countries });
    }
    if (types.length) {
      next.push({ key: "address_type", label: "Type", type: "select", options: types });
    }
    return next;
  }, [data]);

  const handleBulkDelete = async () => {
    if (!selectedAddresses.length) return;
    if (!window.confirm(`Delete ${selectedAddresses.length} addresses?`)) return;

    try {
      await Promise.all(selectedAddresses.map((row) => deleteAddress(row.id)));
      dispatch(
        showToast({
          message: "Addresses deleted successfully",
          type: "success",
        })
      );
      setSelectedAddresses([]);
      getAddressData();
    } catch (error) {
      dispatch(
        showToast({
          message: "Failed to delete addresses",
          type: "error",
        })
      );
    }
  };

  const userColumns: TableColumn<dynamicData>[] = useMemo(
    () => [
      { name: "id", selector: (row: dynamicData) => row.id, sortable: true, width: "5%" },
      {
        name: "address1",
        selector: (row: dynamicData) => row.address1 || "--",
        cell: (row: dynamicData) => (row.address1 ? row.address1.toString() : "--"),
        sortable: true,
        width: "30%",
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
        cell: (row: dynamicData) => (row.country ? row.country.toString() : "--"),
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
    [handleDelete, handleEdit, handleView]
  );

  return (
    <>
      <PageBreadcrumb pageTitle="Address List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="w-full overflow-x-auto rounded-md cus-bg-purple-light h-[calc(100vh-265px)]">
              {formMode ? (
                <div className="flex flex-col">
                  <AddressListMob
                    dataProp={data}
                    handleView={handleView}
                    handleEdit={handleEdit}
                  />
                </div>
              ) : (
                <AdvancedDataTable
                  data={data}
                  columns={userColumns}
                  title="Addresses"
                  storageKey="communications.address.list"
                  loading={loading}
                  filters={filters}
                  enableExport={true}
                  enableSelection={true}
                  enableDatabaseSearch={true}
                  searchDatabase={searchDatabase}
                  onSearchModeChange={setSearchDatabase}
                  onDatabaseSearch={handleDatabaseSearch}
                  onSelectionChange={setSelectedAddresses}
                  exportFileName="addresses_export"
                  searchPlaceholder="Search addresses..."
                  noDataMessage="No addresses found"
                  customActions={
                    <div className="flex gap-2">
                      {selectedAddresses.length > 0 && (
                        <button
                          onClick={handleBulkDelete}
                          className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                        >
                          <FaTrash className="w-4 h-4" />
                          Delete ({selectedAddresses.length})
                        </button>
                      )}
                      <button
                        onClick={handleAdd}
                        className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        <FaPlus className="w-4 h-4" />
                        New Address
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
