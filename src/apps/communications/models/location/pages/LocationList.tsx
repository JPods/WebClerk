import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import DataTable, { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { fetchLocations, deleteLocation } from "../services/locationApi";
import { FaEye, FaEdit, FaTrash, FaPlus } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useTheme } from "../../../../../context/ThemeContext";
import LocationDetail from "./LocationDetail";
import { dynamicData } from "../../../../../model/dynamicData";
export default function LocationList() {
  const { theme } = useTheme();
  const [data, setData] = useState<any[]>([]);
  const [selectedLocation, setSelectedLocation] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    null
  );
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();

  const getLocationData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchLocations();
      if (res.status === 200) {
        setData(res.data.data.results);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch locations", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch locations", error);
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getLocationData();
  }, [getLocationData]);

  const handleView = (row: any) => {
    setSelectedLocation(row);
    setFormMode("view");
  };

  const handleEdit = async (row: dynamicData) => {
    const res = await fetchLocations(row.id);
    console.log("res.", res);
    if (res.status === 200) setSelectedLocation(res.data.data.record);
    else setSelectedLocation(row);
    setFormMode("edit");
    console.log("res", res);
  };

  const handleAdd = () => {
    setSelectedLocation(null);
    setFormMode("add");
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete location ${row.name}?`)) {
      try {
        await deleteLocation(row.id);
        dispatch(
          showToast({
            message: "Location deleted successfully",
            type: "success",
          })
        );
        getLocationData(); // Refresh data
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

  const userColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "5%" },

    {
      name: "Address1",
      selector: (row) => row.address1 || "--",
      sortable: true,
      width: "30%",
    },
    {
      name: "City",
      selector: (row) => row.city || "--",
      sortable: true,
      width: "10%",
    },
    {
      name: "Country",
      selector: (row) => row.country || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Address Type",
      selector: (row) => row.address_type || "--",
      sortable: true,
      width: "30%",
    },
    {
      name: "Action",
      cell: (row) => (
        <div className="flex gap-2">
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
  ];

  return (
    <>
      <PageBreadcrumb pageTitle="Location List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Location
              </button>
            </div>
            <div className="overflow-x-auto bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-400 rounded-md">
              <DataTable
                columns={userColumns.map((col) => ({
                  ...col,
                  name:
                    typeof col.name === "string"
                      ? col.name.toUpperCase()
                      : col.name,
                }))}
                data={data}
                pagination
                theme={theme === "dark" ? "tailwindDark" : "default"}
                highlightOnHover
                pointerOnHover
                progressPending={loading}
                progressComponent={
                  <div className="p-8 text-center">Loading locations...</div>
                }
                onRowClicked={(row) => handleView(row)}
                keyField="id"
              />
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
