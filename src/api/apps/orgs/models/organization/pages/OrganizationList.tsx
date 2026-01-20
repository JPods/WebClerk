import PageBreadcrumb from "../../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../../components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter } from "../../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { fetchOrganizations, deleteOrganization } from "../services/organizationApi";
import { FaEye, FaEdit, FaTrash, FaPlus, FaCheck, FaTimes } from "react-icons/fa";
import { showToast } from "../../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import OrganizationDetail from "./OrganizationDisplay";
import { dynamicData } from "../../../../../../model/dynamicData";

export default function OrganizationList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<dynamicData[]>([]);
  const [selectedOrganization, setSelectedOrganization] = useState<dynamicData | null>(null);
  const [selectedOrganizations, setSelectedOrganizations] = useState<dynamicData[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const getOrganizationData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchOrganizations();
      setData(res.data.data.results || []);
    } catch (error) {
      console.error("Failed to fetch organizations", error);
      dispatch(showToast({ message: "Failed to fetch organizations", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getOrganizationData();
  }, [getOrganizationData]);

  const handleView = useCallback((row: dynamicData) => {
    setSelectedOrganization(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback(async (row: dynamicData) => {
    try {
      const res = await fetchOrganizations(row.id);
      if (res.status === 200) {
        setSelectedOrganization(res.data.data.record);
      } else {
        setSelectedOrganization(row);
      }
    } catch {
      setSelectedOrganization(row);
    }
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedOrganization(null);
    setFormMode("add");
  };

  const handleDelete = useCallback(async (row: dynamicData) => {
    if (!window.confirm(`Delete organization ${row.display_name || row.name}?`)) return;
    
    try {
      await deleteOrganization(row.id);
      dispatch(showToast({ message: "Organization deleted successfully", type: "success" }));
      getOrganizationData();
      if (selectedOrganization && selectedOrganization.id === row.id) {
        setFormMode(null);
        setSelectedOrganization(null);
      }
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete organization", type: "error" }));
    }
  }, [dispatch, getOrganizationData, selectedOrganization]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedOrganizations.length) return;
    if (!window.confirm(`Delete ${selectedOrganizations.length} organization(s)?`)) return;

    try {
      await Promise.all(selectedOrganizations.map((o) => deleteOrganization(o.id)));
      dispatch(showToast({ message: `${selectedOrganizations.length} organization(s) deleted`, type: "success" }));
      getOrganizationData();
      setSelectedOrganizations([]);
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete some organizations", type: "error" }));
    }
  }, [selectedOrganizations, dispatch, getOrganizationData]);

  const handleFormSaved = () => {
    getOrganizationData();
    setFormMode(null);
    setSelectedOrganization(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedOrganization(null);
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
      <PageBreadcrumb pageTitle="Organization List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="Organizations"
              loading={loading}
              filters={filters}
              storageKey="organization-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedOrganizations}
              exportFileName="organizations_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search organizations..."
              noDataMessage="No organizations found"
              customActions={
                <div className="flex gap-2">
                  {selectedOrganizations.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" />
                      Delete ({selectedOrganizations.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Organization
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <OrganizationDetail
              inline
              modeProp={formMode}
              dataProp={selectedOrganization}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
