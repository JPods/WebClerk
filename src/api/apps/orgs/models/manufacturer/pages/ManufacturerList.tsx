import PageBreadcrumb from "../../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../../components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter } from "../../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { fetchManufacturers, deleteManufacturer } from "../services/manufacturerApi";
import { FaEye, FaEdit, FaTrash, FaPlus, FaCheck, FaTimes } from "react-icons/fa";
import { showToast } from "../../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import ManufacturerDetail from "./ManufacturerDisplay";
import { dynamicData } from "../../../../../../model/dynamicData";

export default function ManufacturerList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<dynamicData[]>([]);
  const [selectedManufacturer, setSelectedManufacturer] = useState<dynamicData | null>(null);
  const [selectedManufacturers, setSelectedManufacturers] = useState<dynamicData[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const getManufacturerData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchManufacturers();
      setData(res.data.data.results || []);
    } catch (error) {
      console.error("Failed to fetch manufacturers", error);
      dispatch(showToast({ message: "Failed to fetch manufacturers", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getManufacturerData();
  }, [getManufacturerData]);

  const handleView = useCallback((row: dynamicData) => {
    setSelectedManufacturer(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback(async (row: dynamicData) => {
    try {
      const res = await fetchManufacturers(row.id);
      if (res.status === 200) {
        setSelectedManufacturer(res.data.data.record);
      } else {
        setSelectedManufacturer(row);
      }
    } catch {
      setSelectedManufacturer(row);
    }
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedManufacturer(null);
    setFormMode("add");
  };

  const handleDelete = useCallback(async (row: dynamicData) => {
    if (!window.confirm(`Delete manufacturer ${row.display_name || row.name}?`)) return;
    
    try {
      await deleteManufacturer(row.id);
      dispatch(showToast({ message: "Manufacturer deleted successfully", type: "success" }));
      getManufacturerData();
      if (selectedManufacturer && selectedManufacturer.id === row.id) {
        setFormMode(null);
        setSelectedManufacturer(null);
      }
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete manufacturer", type: "error" }));
    }
  }, [dispatch, getManufacturerData, selectedManufacturer]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedManufacturers.length) return;
    if (!window.confirm(`Delete ${selectedManufacturers.length} manufacturer(s)?`)) return;

    try {
      await Promise.all(selectedManufacturers.map((m) => deleteManufacturer(m.id)));
      dispatch(showToast({ message: `${selectedManufacturers.length} manufacturer(s) deleted`, type: "success" }));
      getManufacturerData();
      setSelectedManufacturers([]);
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete some manufacturers", type: "error" }));
    }
  }, [selectedManufacturers, dispatch, getManufacturerData]);

  const handleFormSaved = () => {
    getManufacturerData();
    setFormMode(null);
    setSelectedManufacturer(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedManufacturer(null);
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
      <PageBreadcrumb pageTitle="Manufacturer List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="Manufacturers"
              loading={loading}
              filters={filters}
              storageKey="manufacturer-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedManufacturers}
              exportFileName="manufacturers_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search manufacturers..."
              noDataMessage="No manufacturers found"
              customActions={
                <div className="flex gap-2">
                  {selectedManufacturers.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" />
                      Delete ({selectedManufacturers.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Manufacturer
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <ManufacturerDetail
              inline
              modeProp={formMode}
              dataProp={selectedManufacturer}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
