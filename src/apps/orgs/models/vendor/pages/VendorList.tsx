import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import DataTable, { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { getRecord } from "../../../../../api/wcapi";
import { fetchVendors, deleteVendor } from "../services/vendorApi";
import {
  FaEye,
  FaEdit,
  FaTrash,
  FaPlus,
  FaCheck,
  FaTimes,
} from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useTheme } from "../../../../../context/ThemeContext";
import VendorDetail from "./VendorDetail";
import { dynamicData } from "../../../../../model/dynamicData";
import VendorListMob from "./VendorListMob";

export default function VendorList() {
  const { theme } = useTheme();
  const [data, setData] = useState<dynamicData[]>([]);
  const [filteredData, setFilteredData] = useState<dynamicData[]>([]);
  const [filteredSearch, setFilteredSearch] = useState<string>("");
  const [selectedVendor, setSelectedVendor] = useState<dynamicData | null>(
    null
  );
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    null
  );
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();

  const getLocationData = useCallback(async (vendorId?: number) => {
    setLoading(true);
    try {
      const res = await fetchVendors();
      setData(res.data.data.results);
      setFilteredData(res.data.data.results);
      if (vendorId) {
        const contactRes = await getRecord("vendor", vendorId);
        setSelectedVendor(contactRes.record);
        setFilteredData(contactRes.record);
      }
    } finally {
      setLoading(false);
    }
  }, []);
  //console.log("filteredData,data", filteredData, data);

  useEffect(() => {
    getLocationData();
  }, [getLocationData]);

  const handleView = (row: dynamicData) => {
    setSelectedVendor(row);
    setFormMode("view");
  };

  const handleEdit = async (row: dynamicData) => {
    const res = await fetchVendors(row.id);
    console.log("res.", res);
    if (res.status === 200) setSelectedVendor(res.data.data.record);
    else setSelectedVendor(row);
    setFormMode("edit");
    console.log("res", res);
  };

  const handleAdd = () => {
    setSelectedVendor(null);
    setFormMode("add");
  };

  const handleDelete = async (row: dynamicData) => {
    if (window.confirm(`Delete Vendor ${row.name}?`)) {
      try {
        await deleteVendor(row.id);
        dispatch(
          showToast({
            message: "Vendor deleted successfully",
            type: "success",
          })
        );
        getLocationData(); // Refresh data
        if (selectedVendor && selectedVendor.id === row.id) {
          setFormMode(null);
          setSelectedVendor(null);
        }
      } catch (error) {
        dispatch(
          showToast({
            message: "Failed to delete Vendor",
            type: "error",
          })
        );
      }
    }
  };

  const handleFormSaved = () => {
    getLocationData();
    setFormMode(null);
    setSelectedVendor(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedVendor(null);
  };

  // --------------- Global Filtered ---------------------------//
  const filterData = (inputData: string) => {
    const searchQuery = inputData.trim().toLowerCase(); // Trim and lowercase for case-insensitive comparison
    setFilteredSearch(searchQuery);
    if (searchQuery) {
      const filtered = data.filter((element) => {
        // Combine all columns you want to search in as strings
        const valuesToSearch = [
          element.display_name,
          element.org_type,
          element.status,
          element.version,
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

  const userColumns: TableColumn<dynamicData>[] = [
    { name: "id", selector: (row) => row.id, sortable: true, width: "5%" },

    {
      name: "display_name",
      selector: (row) => row.display_name || "--",
      cell: (row) =>
        row.display_name ? highlightMatch(row.display_name.toString()) : "--",
      sortable: true,
      width: "25%",
    },
    {
      name: "org_type",
      selector: (row) => row.org_type || "--",
      cell: (row) =>
        row.org_type ? highlightMatch(row.org_type.toString()) : "--",
      sortable: true,
      width: "10%",
    },
    {
      name: "status",
      selector: (row) => row.status || "--",
      cell: (row) =>
        row.status ? highlightMatch(row.status.toString()) : "--",
      sortable: true,
      width: "30%",
    },

    {
      name: "is_active",
      selector: (row) => (row.is_active ? "yes" : "no"),
      cell: (row) => (
        <>
          {row.is_active ? (
            <FaCheck className="text-success-600 hover:scale-110 transition" />
          ) : (
            <FaTimes className="text-warning-600 hover:scale-110 transition" />
          )}
        </>
      ),
      sortable: true,
      width: "10%",
    },
    {
      name: "version",
      selector: (row) => row.version || "--",
      cell: (row) =>
        row.version ? highlightMatch(row.version.toString()) : "--",
      sortable: true,
      width: "10%",
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
      <PageBreadcrumb pageTitle="Vendor List" />
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
                  Vendor
                </button>
              </div>
            </div>

            <div className="w-full overflow-x-auto rounded-md cus-bg-purple-light dark:!bg-[#1e2636] dark:bg-gray-900 h-[calc(100vh-265px)]">
              {formMode ? (
                <div className="flex flex-col">
                  <VendorListMob
                    dataProp={filteredData}
                    handleView={handleView}
                    handleEdit={handleEdit}
                  />
                </div>
              ) : (
                <DataTable
                  columns={userColumns.map((col) => ({
                    ...col,
                    name: typeof col.name === "string" && col.name,
                  }))}
                  data={filteredData}
                  pagination
                  theme={theme === "dark" ? "tailwindDark" : "default"}
                  highlightOnHover
                  pointerOnHover
                  progressPending={loading}
                  progressComponent={
                    <div className="p-8 text-sm text-center text-gray-500">
                      Loading locations...
                    </div>
                  }
                  onRowClicked={(row) => handleView(row)}
                  keyField="id"
                  className="text-2xl p-2"
                />
              )}
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <VendorDetail
              inline
              modeProp={formMode}
              dataProp={selectedVendor}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
