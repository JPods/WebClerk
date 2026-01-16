import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { getRecord } from "../../../../../api/wcapi";
import { fetchLocations, deleteLocation } from "../services/locationApi";
import { FaEye, FaEdit, FaTrash, FaPlus } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import LocationDetail from "./LocationDetail";
import { dynamicData } from "../../../../../model/dynamicData";
import LocationListMob from "./LocationListMob";
export default function LocationList() {
  const [data, setData] = useState<dynamicData[]>([]);
  const [filteredData, setFilteredData] = useState<dynamicData[]>([]);
  const [filteredSearch, setFilteredSearch] = useState<string>("");
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
      setFilteredData(res.data.data.results);
      if (locationId) {
        const contactRes = await getRecord("contact", locationId);
        setSelectedLocation(contactRes.record);
        setFilteredData(contactRes.record);
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

  // --------------- Global Filtered ---------------------------//
  const filterData = (inputData: string) => {
    const searchQuery = inputData.trim().toLowerCase(); // Trim and lowercase for case-insensitive comparison
    setFilteredSearch(searchQuery);
    if (searchQuery) {
      const filtered = data.filter((element) => {
        // Combine all columns you want to search in as strings
        const valuesToSearch = [
          element.email,
          element.name,
          element.attention,
        ].map((value) => value && value.toString().trim().toLowerCase()); // Trim and lowercase each value

        // Check if any of the column values includes the search query
        return valuesToSearch.some(
          (value) => value && value.includes(searchQuery)
        );
      });

      setFilteredData(filtered); // Update filtered data
    } else {
      setFilteredData(data);
    }
  };
  const highlightMatch = useCallback(
    (text: string) => {
      if (!filteredSearch) return text;

      const escaped = filteredSearch.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const regex = new RegExp(`(${escaped})`, "gi");

      return text.split(regex).map((part, index) =>
        part.toLowerCase() === filteredSearch ? (
          <span key={index} className="text-red-600 font-semibold">
            {part}
          </span>
        ) : (
          part
        )
      );
    },
    [filteredSearch]
  );
  /* ---------------- Columns ---------------- */
  const userColumns: TableColumn<dynamicData>[] = useMemo(
    () => [
      { name: "id", selector: (row) => row.id, sortable: true, width: "5%" },
      {
        name: "address1",
        selector: (row) => row.address1 || "--",
        cell: (row) =>
          row.address1 ? highlightMatch(row.address1.toString()) : "--",
        sortable: true,
        width: "30%",
      },
      {
        name: "city",
        selector: (row) => row.city || "--",
        cell: (row) => (row.city ? highlightMatch(row.city.toString()) : "--"),
        sortable: true,
        width: "10%",
      },

      {
        name: "country",
        selector: (row) => row.country || "--",
        cell: (row) =>
          row.country ? highlightMatch(row.country.toString()) : "--",
        sortable: true,
        width: "15%",
      },
      {
        name: "address_type",
        selector: (row) => row.address_type || "--",
        cell: (row) =>
          row.address_type ? highlightMatch(row.address_type.toString()) : "--",
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
          </div>
        ),
        ignoreRowClick: true,
        allowOverflow: true,
        button: true,
      },
    ],
    [highlightMatch]
  );

  return (
    <>
      <PageBreadcrumb pageTitle="Location List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-between mb-0">
              <div className="flex  mb-2">
                <div className="relative">
                  <span className="absolute -translate-y-1/2 pointer-events-none left-4 top-1/2">
                    <svg
                      className="fill-gray-500 dark:fill-gray-400"
                      width="20"
                      height="20"
                      viewBox="0 0 20 20"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        fillRule="evenodd"
                        clipRule="evenodd"
                        d="M3.04175 9.37363C3.04175 5.87693 5.87711 3.04199 9.37508 3.04199C12.8731 3.04199 15.7084 5.87693 15.7084 9.37363C15.7084 12.8703 12.8731 15.7053 9.37508 15.7053C5.87711 15.7053 3.04175 12.8703 3.04175 9.37363ZM9.37508 1.54199C5.04902 1.54199 1.54175 5.04817 1.54175 9.37363C1.54175 13.6991 5.04902 17.2053 9.37508 17.2053C11.2674 17.2053 13.003 16.5344 14.357 15.4176L17.177 18.238C17.4699 18.5309 17.9448 18.5309 18.2377 18.238C18.5306 17.9451 18.5306 17.4703 18.2377 17.1774L15.418 14.3573C16.5365 13.0033 17.2084 11.2669 17.2084 9.37363C17.2084 5.04817 13.7011 1.54199 9.37508 1.54199Z"
                        fill=""
                      />
                    </svg>
                  </span>
                  <input
                    type="text"
                    value={filteredSearch}
                    onChange={(e) => filterData(e.target.value)}
                    placeholder="Search for record..."
                    className="dark:bg-dark-900 h-11 w-full rounded-lg border border-gray-200 bg-transparent py-2.5 pl-12 pr-14 text-sm text-gray-800 shadow-theme-xs placeholder:text-gray-400 focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-800 dark:bg-gray-900 dark:bg-white/[0.03] dark:text-white/90 dark:placeholder:text-white/30 dark:focus:border-brand-800 "
                  />
                  <div className="absolute right-2.5 top-1/2 inline-flex -translate-y-1/2 items-center gap-0.5 rounded-lg border border-gray-200 bg-gray-50 px-[7px] py-[4.5px] text-xs -tracking-[0.2px] text-gray-500 dark:border-gray-800 dark:bg-white/[0.03] dark:text-gray-400">
                    <span>
                      <button
                        type="button"
                        onClick={() => filterData("")}
                        className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                      >
                        &times;
                      </button>
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex mb-2">
                <button
                  onClick={handleAdd}
                  className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
                >
                  <FaPlus />
                  Location
                </button>
              </div>
            </div>

            <div className="w-full overflow-x-auto rounded-md cus-bg-purple-light dark:!bg-[#1e2636] dark:bg-gray-900 h-[calc(100vh-265px)]">
              {formMode ? (
                <div className="flex flex-col">
                  <LocationListMob
                    dataProp={filteredData}
                    handleView={handleView}
                    handleEdit={handleEdit}
                  />
                </div>
              ) : (
                <AdvancedDataTable
                  columns={userColumns.map((col) => ({
                    ...col,
                    name:
                      typeof col.name === "string"
                        ? col.name.toUpperCase()
                        : col.name,
                  }))}
                  data={filteredData}
                  storageKey="location_list"
                  loading={loading}
                  onRowActivate={handleEdit}
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
