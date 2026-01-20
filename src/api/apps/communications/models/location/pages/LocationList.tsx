import PageBreadcrumb from "../../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../../components/common/ComponentCard";
import AdvancedDataTable, {
  ColumnFilter,
} from "../../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { getRecord } from "../../../../../wcapi";
import { fetchLocations, deleteLocation } from "../services/locationApi";
import { FaEye, FaEdit, FaTrash, FaPlus } from "react-icons/fa";
import { showToast } from "../../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import LocationDetail from "./LocationDetail";
import { dynamicData } from "../../../../../../model/dynamicData";
import LocationListMob from "./LocationListMob";

export default function LocationList() {
  const [data, setData] = useState<dynamicData[]>([]);
  const [selectedLocations, setSelectedLocations] = useState<dynamicData[]>([]);
  const [selectedLocation, setSelectedLocation] = useState<dynamicData | null>(
    null
  );
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    null
  );
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();
  const getLocationData = useCallback(async (locationId?: number) => {
    setLoading(true);
    try {
      const res = await fetchLocations();
      setData(res.data.data.results);
      if (locationId) {
        const contactRes = await getRecord("contact", locationId);
        setSelectedLocation(contactRes.record);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    getLocationData();
  }, [getLocationData]);

  const handleView = (row: dynamicData) => {
    setSelectedLocation(row);
    setFormMode("view");
  };

  const handleEdit = async (row: dynamicData) => {
    const res = await fetchLocations(row.id);
    if (res.status === 200) setSelectedLocation(res.data.data.record);
    else setSelectedLocation(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedLocation(null);
    setFormMode("add");
  };

  const handleDelete = async (row: dynamicData) => {
    if (window.confirm(`Delete location ${row.name}?`)) {
      try {
        await deleteLocation(row.id);
        dispatch(
          showToast({
            message: "Location deleted successfully",
            type: "success",
          })
        );
        getLocationData();
        if (selectedLocation && selectedLocation.id === row.id) {
          setFormMode(null);
          setSelectedLocation(null);
        }
      } catch (error) {
        dispatch(
          showToast({
            message: "Failed to delete location",
            type: "error",
          })
        );
      }
    }
  };

  const handleFormSaved = () => {
    getLocationData();
    setFormMode(null);
    setSelectedLocation(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedLocation(null);
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
    if (!selectedLocations.length) return;
    if (!window.confirm(`Delete ${selectedLocations.length} locations?`)) return;

    try {
      await Promise.all(selectedLocations.map((row) => deleteLocation(row.id)));
      dispatch(
        showToast({
          message: "Locations deleted successfully",
          type: "success",
        })
      );
      setSelectedLocations([]);
      getLocationData();
    } catch (error) {
      dispatch(
        showToast({
          message: "Failed to delete locations",
          type: "error",
        })
      );
    }
  };

  const userColumns: TableColumn<dynamicData>[] = useMemo(
    () => [
      { name: "id", selector: (row) => row.id, sortable: true, width: "5%" },
      {
        name: "address1",
        selector: (row) => row.address1 || "--",
        cell: (row) => (row.address1 ? row.address1.toString() : "--"),
        sortable: true,
        width: "30%",
      },
      {
        name: "city",
        selector: (row) => row.city || "--",
        cell: (row) => (row.city ? row.city.toString() : "--"),
        sortable: true,
        width: "10%",
      },
      {
        name: "country",
        selector: (row) => row.country || "--",
        cell: (row) => (row.country ? row.country.toString() : "--"),
        sortable: true,
        width: "15%",
      },
      {
        name: "address_type",
        selector: (row) => row.address_type || "--",
        cell: (row) =>
          row.address_type ? row.address_type.toString() : "--",
        sortable: true,
        width: "30%",
      },
      {
        name: "action",
        cell: (row) => (
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
      <PageBreadcrumb pageTitle="Location List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="w-full overflow-x-auto rounded-md cus-bg-purple-light h-[calc(100vh-265px)]">
              {formMode ? (
                <div className="flex flex-col">
                  <LocationListMob
                    dataProp={data}
                    handleView={handleView}
                    handleEdit={handleEdit}
                  />
                </div>
              ) : (
                <AdvancedDataTable
                  data={data}
                  columns={userColumns}
                  title="Locations"
                  storageKey="communications.location.list"
                  loading={loading}
                  filters={filters}
                  enableExport={true}
                  enableSelection={true}
                  onSelectionChange={setSelectedLocations}
                  exportFileName="locations_export"
                  searchPlaceholder="Search locations..."
                  noDataMessage="No locations found"
                  customActions={
                    <div className="flex gap-2">
                      {selectedLocations.length > 0 && (
                        <button
                          onClick={handleBulkDelete}
                          className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                        >
                          <FaTrash className="w-4 h-4" />
                          Delete ({selectedLocations.length})
                        </button>
                      )}
                      <button
                        onClick={handleAdd}
                        className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        <FaPlus className="w-4 h-4" />
                        New Location
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
            <LocationDetail
              inline
              modeProp={formMode}
              dataProp={selectedLocation}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
