import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter } from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { fetchVendors, deleteVendor } from "../services/vendorApi";
import { FaEye, FaEdit, FaTrash, FaPlus, FaCheck, FaTimes } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import VendorDetail from "./VendorDetail";
import { dynamicData } from "../../../../../model/dynamicData";

export default function VendorList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<dynamicData[]>([]);
  const [selectedVendor, setSelectedVendor] = useState<dynamicData | null>(null);
  const [selectedVendors, setSelectedVendors] = useState<dynamicData[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const getVendorData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchVendors();
      setData(res.data.data.results || []);
    } catch (error) {
      console.error("Failed to fetch vendors", error);
      dispatch(showToast({ message: "Failed to fetch vendors", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getVendorData();
  }, [getVendorData]);

  const handleView = useCallback((row: dynamicData) => {
    setSelectedVendor(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback(async (row: dynamicData) => {
    try {
      const res = await fetchVendors(row.id);
      if (res.status === 200) {
        setSelectedVendor(res.data.data.record);
      } else {
        setSelectedVendor(row);
      }
    } catch {
      setSelectedVendor(row);
    }
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedVendor(null);
    setFormMode("add");
  };

  const handleDelete = useCallback(async (row: dynamicData) => {
    if (!window.confirm(`Delete vendor ${row.display_name || row.name}?`)) return;
    
    try {
      await deleteVendor(row.id);
      dispatch(showToast({ message: "Vendor deleted successfully", type: "success" }));
      getVendorData();
      if (selectedVendor && selectedVendor.id === row.id) {
        setFormMode(null);
        setSelectedVendor(null);
      }
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete vendor", type: "error" }));
    }
  }, [dispatch, getVendorData, selectedVendor]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedVendors.length) return;
    if (!window.confirm(`Delete ${selectedVendors.length} vendor(s)?`)) return;

    try {
      await Promise.all(selectedVendors.map((v) => deleteVendor(v.id)));
      dispatch(showToast({ message: `${selectedVendors.length} vendor(s) deleted`, type: "success" }));
      getVendorData();
      setSelectedVendors([]);
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete some vendors", type: "error" }));
    }
  }, [selectedVendors, dispatch, getVendorData]);

  const handleFormSaved = () => {
    getVendorData();
    setFormMode(null);
    setSelectedVendor(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedVendor(null);
  };

  const filters: ColumnFilter[] = useMemo(() => [
    { key: "org_type", label: "Org Type", type: "text" },
    { key: "status", label: "Status", type: "text" },
    { key: "is_active", label: "Active", type: "select", options: [
      { value: "true", label: "Active" },
      { value: "false", label: "Inactive" },
    ]},
  ], []);

  const columns: TableColumn<dynamicData>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "display_name", name: "Display Name", selector: (row) => row.display_name || "--", sortable: true, width: "25%" },
    { id: "org_type", name: "Org Type", selector: (row) => row.org_type || "--", sortable: true, width: "12%" },
    { id: "status", name: "Status", selector: (row) => row.status || "--", sortable: true, width: "15%" },
    {
      id: "is_active",
      name: "Active",
      selector: (row) => (row.is_active ? "yes" : "no"),
      cell: (row) => (
        row.is_active 
          ? <FaCheck className="text-green-600" /> 
          : <FaTimes className="text-yellow-600" />
      ),
      sortable: true,
      width: "10%",
    },
    { id: "version", name: "Version", selector: (row) => row.version || "--", sortable: true, width: "10%" },
    {
      id: "actions",
      name: "Actions",
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
      width: "100px",
    },
  ], [handleDelete, handleEdit, handleView]);

  return (
    <>
      <PageBreadcrumb pageTitle="Vendor List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="Vendors"
              loading={loading}
              filters={filters}
              storageKey="vendor-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedVendors}
              exportFileName="vendors_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search vendors..."
              noDataMessage="No vendors found"
              customActions={
                <div className="flex gap-2">
                  {selectedVendors.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" />
                      Delete ({selectedVendors.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Vendor
                  </button>
                </div>
              }
            />
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
