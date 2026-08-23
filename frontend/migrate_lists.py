#!/usr/bin/env python3
"""Migration script to update List files to use AdvancedDataTable"""

import os

# Define the files and their new content
migrations = {}

# 1. OrganizationList.tsx
migrations['src/apps/orgs/models/organization/pages/OrganizationList.tsx'] = '''import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter } from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { fetchOrganizations, deleteOrganization } from "../services/organizationApi";
import { FaEye, FaEdit, FaTrash, FaPlus, FaCheck, FaTimes } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import OrganizationDetail from "./OrganizationDisplay";
import { dynamicData } from "../../../../../model/dynamicData";

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
'''

# 2. ManufacturerList.tsx
migrations['src/apps/orgs/models/manufacturer/pages/ManufacturerList.tsx'] = '''import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter } from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { fetchManufacturers, deleteManufacturer } from "../services/manufacturerApi";
import { FaEye, FaEdit, FaTrash, FaPlus, FaCheck, FaTimes } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import ManufacturerDetail from "./ManufacturerDisplay";
import { dynamicData } from "../../../../../model/dynamicData";

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
'''

# 3. BaseOrgModelList.tsx
migrations['src/apps/orgs/models/base_org_model/pages/BaseOrgModelList.tsx'] = '''import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import ComponentCard from "@/components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter } from "@/components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { getRecords, deleteRecord } from "@/api/wcapi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import BaseOrgModelDisplay from "./BaseOrgModelDisplay";

export default function BaseOrgModelList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedBaseOrgModel, setSelectedBaseOrgModel] = useState<any | null>(null);
  const [selectedBaseOrgModels, setSelectedBaseOrgModels] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const getBaseOrgModelData = useCallback(async () => {
    try {
      setLoading(true);
      const list = await getRecords('base_org_model');
      const recs = Array.isArray(list?.results) ? list.results : Array.isArray(list) ? list : [];
      setData(recs);
    } catch (error) {
      console.error("Failed to fetch base org models", error);
      dispatch(showToast({ message: "Failed to fetch base org models", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getBaseOrgModelData();
  }, [getBaseOrgModelData]);

  const handleView = useCallback((row: any) => {
    setSelectedBaseOrgModel(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback((row: any) => {
    setSelectedBaseOrgModel(row);
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedBaseOrgModel(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getBaseOrgModelData();
    setFormMode(null);
    setSelectedBaseOrgModel(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedBaseOrgModel(null);
  };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete base org model ${row.name || row.id}?`)) return;
    
    try {
      await deleteRecord('base_org_model', row.id);
      dispatch(showToast({ message: "Base Org Model deleted successfully", type: "success" }));
      getBaseOrgModelData();
      if (selectedBaseOrgModel && selectedBaseOrgModel.id === row.id) {
        setFormMode(null);
        setSelectedBaseOrgModel(null);
      }
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete base org model", type: "error" }));
    }
  }, [dispatch, getBaseOrgModelData, selectedBaseOrgModel]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedBaseOrgModels.length) return;
    if (!window.confirm(`Delete ${selectedBaseOrgModels.length} base org model(s)?`)) return;

    try {
      await Promise.all(selectedBaseOrgModels.map((m) => deleteRecord('base_org_model', m.id)));
      dispatch(showToast({ message: `${selectedBaseOrgModels.length} base org model(s) deleted`, type: "success" }));
      getBaseOrgModelData();
      setSelectedBaseOrgModels([]);
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete some base org models", type: "error" }));
    }
  }, [selectedBaseOrgModels, dispatch, getBaseOrgModelData]);

  const filters: ColumnFilter[] = useMemo(() => [
    { key: "type", label: "Type", type: "text" },
    { key: "status", label: "Status", type: "text" },
  ], []);

  const columns: TableColumn<any>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "name", name: "Name", selector: (row) => row.name || "--", sortable: true, width: "40%" },
    { id: "type", name: "Type", selector: (row) => row.type || "--", sortable: true, width: "25%" },
    { id: "status", name: "Status", selector: (row) => row.status || "--", sortable: true, width: "15%" },
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
      <PageBreadcrumb pageTitle="Base Org Model List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="Base Org Models"
              loading={loading}
              filters={filters}
              storageKey="base-org-model-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedBaseOrgModels}
              exportFileName="base_org_models_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search base org models..."
              noDataMessage="No base org models found"
              customActions={
                <div className="flex gap-2">
                  {selectedBaseOrgModels.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" />
                      Delete ({selectedBaseOrgModels.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Base Org Model
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <BaseOrgModelDisplay
              inline
              modeProp={formMode}
              dataProp={selectedBaseOrgModel}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
'''

# 4. RepList.tsx
migrations['src/apps/orgs/models/rep/pages/RepList.tsx'] = '''import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter } from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { fetchReps, deleteRep } from "../services/repApi";
import { FaEye, FaEdit, FaTrash, FaPlus, FaCheck, FaTimes } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import RepDetail from "./RepDisplay";
import { dynamicData } from "../../../../../model/dynamicData";

export default function RepList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<dynamicData[]>([]);
  const [selectedRep, setSelectedRep] = useState<dynamicData | null>(null);
  const [selectedReps, setSelectedReps] = useState<dynamicData[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const getRepData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchReps();
      setData(res.data.data.results || []);
    } catch (error) {
      console.error("Failed to fetch reps", error);
      dispatch(showToast({ message: "Failed to fetch reps", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getRepData();
  }, [getRepData]);

  const handleView = useCallback((row: dynamicData) => {
    setSelectedRep(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback(async (row: dynamicData) => {
    try {
      const res = await fetchReps(row.id);
      if (res.status === 200) {
        setSelectedRep(res.data.data.record);
      } else {
        setSelectedRep(row);
      }
    } catch {
      setSelectedRep(row);
    }
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedRep(null);
    setFormMode("add");
  };

  const handleDelete = useCallback(async (row: dynamicData) => {
    if (!window.confirm(`Delete rep ${row.display_name || row.name}?`)) return;
    
    try {
      await deleteRep(row.id);
      dispatch(showToast({ message: "Rep deleted successfully", type: "success" }));
      getRepData();
      if (selectedRep && selectedRep.id === row.id) {
        setFormMode(null);
        setSelectedRep(null);
      }
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete rep", type: "error" }));
    }
  }, [dispatch, getRepData, selectedRep]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedReps.length) return;
    if (!window.confirm(`Delete ${selectedReps.length} rep(s)?`)) return;

    try {
      await Promise.all(selectedReps.map((r) => deleteRep(r.id)));
      dispatch(showToast({ message: `${selectedReps.length} rep(s) deleted`, type: "success" }));
      getRepData();
      setSelectedReps([]);
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete some reps", type: "error" }));
    }
  }, [selectedReps, dispatch, getRepData]);

  const handleFormSaved = () => {
    getRepData();
    setFormMode(null);
    setSelectedRep(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedRep(null);
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
      <PageBreadcrumb pageTitle="Rep List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="Reps"
              loading={loading}
              filters={filters}
              storageKey="rep-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedReps}
              exportFileName="reps_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search reps..."
              noDataMessage="No reps found"
              customActions={
                <div className="flex gap-2">
                  {selectedReps.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" />
                      Delete ({selectedReps.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Rep
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <RepDetail
              inline
              modeProp={formMode}
              dataProp={selectedRep}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
'''

# 5. RequisitionList.tsx
migrations['src/apps/transactions/models/requisition/pages/RequisitionList.tsx'] = '''import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchRequisitions } from "../services/requisitionApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import RequisitionDetail from "./RequisitionDetail";

export default function RequisitionList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedRequisition, setSelectedRequisition] = useState<any | null>(null);
  const [selectedRequisitions, setSelectedRequisitions] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const getRequisitionData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchRequisitions();
      if (res.status === 200) {
        setData(res.data.items || []);
      } else {
        dispatch(showToast({ message: "Failed to fetch requisitions", type: "error" }));
      }
    } catch (error) {
      console.error("Failed to fetch requisitions", error);
      dispatch(showToast({ message: "Failed to fetch requisitions", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getRequisitionData();
  }, [getRequisitionData]);

  const handleView = useCallback((row: any) => {
    setSelectedRequisition(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback((row: any) => {
    setSelectedRequisition(row);
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedRequisition(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getRequisitionData();
    setFormMode(null);
    setSelectedRequisition(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedRequisition(null);
  };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete requisition ${row.requisition_no}?`)) return;
    
    try {
      await deleteAction(row.id);
      dispatch(showToast({ message: "Requisition deleted successfully", type: "success" }));
      getRequisitionData();
      if (selectedRequisition && selectedRequisition.id === row.id) {
        setFormMode(null);
        setSelectedRequisition(null);
      }
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete requisition", type: "error" }));
    }
  }, [dispatch, getRequisitionData, selectedRequisition]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedRequisitions.length) return;
    if (!window.confirm(`Delete ${selectedRequisitions.length} requisition(s)?`)) return;

    try {
      await Promise.all(selectedRequisitions.map((r) => deleteAction(r.id)));
      dispatch(showToast({ message: `${selectedRequisitions.length} requisition(s) deleted`, type: "success" }));
      getRequisitionData();
      setSelectedRequisitions([]);
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete some requisitions", type: "error" }));
    }
  }, [selectedRequisitions, dispatch, getRequisitionData]);

  const columns: TableColumn<any>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "requisition_no", name: "Requisition No", selector: (row) => row.requisition_no || "--", sortable: true, width: "30%" },
    { id: "dt_created", name: "Created", selector: (row) => row.dt_created ? new Date(row.dt_created * 1000).toLocaleDateString() : "--", sortable: true, width: "25%" },
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
      <PageBreadcrumb pageTitle="Requisition List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="Requisitions"
              loading={loading}
              storageKey="requisition-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedRequisitions}
              exportFileName="requisitions_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search requisitions..."
              noDataMessage="No requisitions found"
              customActions={
                <div className="flex gap-2">
                  {selectedRequisitions.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" />
                      Delete ({selectedRequisitions.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Requisition
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <RequisitionDetail
              inline
              modeProp={formMode}
              dataProp={selectedRequisition}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
'''

# 6. WorkorderList.tsx
migrations['src/apps/transactions/models/work_order/pages/WorkorderList.tsx'] = '''import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchWorkorders, fetchWorkorderDetail } from "../services/workorderApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import WorkorderDetail from "./WorkorderDetail";

export default function WorkorderList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedWorkorder, setSelectedWorkorder] = useState<any | null>(null);
  const [selectedWorkorders, setSelectedWorkorders] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);

  const getWorkorderData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchWorkorders();
      if (res.status === 200) {
        setData(res.data.items || []);
      } else {
        dispatch(showToast({ message: "Failed to fetch workorders", type: "error" }));
      }
    } catch (error) {
      console.error("Failed to fetch workorders", error);
      dispatch(showToast({ message: "Failed to fetch workorders", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getWorkorderData();
  }, [getWorkorderData]);

  const openWorkorder = useCallback(
    async (row: any, modeToSet: "view" | "edit") => {
      const workorderId = row?.id;
      if (!workorderId) {
        dispatch(showToast({ message: "Workorder id missing", type: "error" }));
        return;
      }

      setFormMode(modeToSet);
      setDetailLoading(true);
      setSelectedWorkorder(null);

      try {
        const detail = await fetchWorkorderDetail(workorderId);
        const hasDetail = detail && Object.keys(detail).length > 0;
        if (!hasDetail) {
          throw new Error("Workorder not found");
        }
        setSelectedWorkorder({ ...row, ...detail });
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Failed to load workorder";
        dispatch(showToast({ message, type: "error" }));
        setFormMode(null);
        setSelectedWorkorder(null);
      } finally {
        setDetailLoading(false);
      }
    },
    [dispatch]
  );

  const handleView = useCallback((row: any) => {
    openWorkorder(row, "view");
  }, [openWorkorder]);

  const handleEdit = useCallback((row: any) => {
    openWorkorder(row, "edit");
  }, [openWorkorder]);

  const handleAdd = () => {
    setSelectedWorkorder(null);
    setFormMode("add");
    setDetailLoading(false);
  };

  const handleFormSaved = () => {
    getWorkorderData();
    setFormMode(null);
    setSelectedWorkorder(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedWorkorder(null);
  };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete workorder ${row.workorder_no}?`)) return;
    
    try {
      await deleteAction(row.id);
      dispatch(showToast({ message: "Workorder deleted successfully", type: "success" }));
      getWorkorderData();
      if (selectedWorkorder && selectedWorkorder.id === row.id) {
        setFormMode(null);
        setSelectedWorkorder(null);
      }
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete workorder", type: "error" }));
    }
  }, [dispatch, getWorkorderData, selectedWorkorder]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedWorkorders.length) return;
    if (!window.confirm(`Delete ${selectedWorkorders.length} workorder(s)?`)) return;

    try {
      await Promise.all(selectedWorkorders.map((w) => deleteAction(w.id)));
      dispatch(showToast({ message: `${selectedWorkorders.length} workorder(s) deleted`, type: "success" }));
      getWorkorderData();
      setSelectedWorkorders([]);
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete some workorders", type: "error" }));
    }
  }, [selectedWorkorders, dispatch, getWorkorderData]);

  const columns: TableColumn<any>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "workorder_no", name: "Workorder No", selector: (row) => row.workorder_no || "--", sortable: true, width: "30%" },
    { id: "dt_created", name: "Created", selector: (row) => row.dt_created ? new Date(row.dt_created * 1000).toLocaleDateString() : "--", sortable: true, width: "25%" },
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
      <PageBreadcrumb pageTitle="Workorder List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="Workorders"
              loading={loading}
              storageKey="workorder-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedWorkorders}
              exportFileName="workorders_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search workorders..."
              noDataMessage="No workorders found"
              customActions={
                <div className="flex gap-2">
                  {selectedWorkorders.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" />
                      Delete ({selectedWorkorders.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Workorder
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            {formMode !== "add" && (detailLoading || !selectedWorkorder) ? (
              <ComponentCard>
                <div className="p-8 text-center text-sm text-gray-500 dark:text-gray-400">
                  Loading workorder...
                </div>
              </ComponentCard>
            ) : (
              <WorkorderDetail
                inline
                modeProp={formMode}
                dataProp={formMode === "add" ? null : selectedWorkorder}
                onSaved={handleFormSaved}
                onCancelInline={handleFormCancel}
              />
            )}
          </div>
        )}
      </div>
    </>
  );
}
'''

# 7. ProjectList.tsx
migrations['src/apps/transactions/models/project/pages/ProjectList.tsx'] = '''import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter } from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchProjects } from "../services/projectApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import ProjectDetail from "./ProjectDetail";

export default function ProjectList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedProject, setSelectedProject] = useState<any | null>(null);
  const [selectedProjects, setSelectedProjects] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const getProjectData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchProjects();
      if (res.status === 200) {
        setData(res.data.items || []);
      } else {
        dispatch(showToast({ message: "Failed to fetch projects", type: "error" }));
      }
    } catch (error) {
      console.error("Failed to fetch projects", error);
      dispatch(showToast({ message: "Failed to fetch projects", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getProjectData();
  }, [getProjectData]);

  const handleView = useCallback((row: any) => {
    setSelectedProject(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback((row: any) => {
    setSelectedProject(row);
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedProject(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getProjectData();
    setFormMode(null);
    setSelectedProject(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedProject(null);
  };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete project ${row.name}?`)) return;
    
    try {
      await deleteAction(row.id);
      dispatch(showToast({ message: "Project deleted successfully", type: "success" }));
      getProjectData();
      if (selectedProject && selectedProject.id === row.id) {
        setFormMode(null);
        setSelectedProject(null);
      }
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete project", type: "error" }));
    }
  }, [dispatch, getProjectData, selectedProject]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedProjects.length) return;
    if (!window.confirm(`Delete ${selectedProjects.length} project(s)?`)) return;

    try {
      await Promise.all(selectedProjects.map((p) => deleteAction(p.id)));
      dispatch(showToast({ message: `${selectedProjects.length} project(s) deleted`, type: "success" }));
      getProjectData();
      setSelectedProjects([]);
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete some projects", type: "error" }));
    }
  }, [selectedProjects, dispatch, getProjectData]);

  const filters: ColumnFilter[] = useMemo(() => [
    { key: "status", label: "Status", type: "text" },
  ], []);

  const columns: TableColumn<any>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "name", name: "Name", selector: (row) => row.name || "--", sortable: true, width: "20%" },
    { id: "description", name: "Description", selector: (row) => row.description || "--", sortable: true, width: "25%" },
    { id: "status", name: "Status", selector: (row) => row.status || "--", sortable: true, width: "12%" },
    { id: "start_date", name: "Start Date", selector: (row) => row.start_date || "--", sortable: true, width: "12%" },
    { id: "end_date", name: "End Date", selector: (row) => row.end_date || "--", sortable: true, width: "12%" },
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
      <PageBreadcrumb pageTitle="Project List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="Projects"
              loading={loading}
              filters={filters}
              storageKey="project-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedProjects}
              exportFileName="projects_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search projects..."
              noDataMessage="No projects found"
              customActions={
                <div className="flex gap-2">
                  {selectedProjects.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" />
                      Delete ({selectedProjects.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Project
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <ProjectDetail
              inline
              modeProp={formMode}
              dataProp={selectedProject}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
'''

# 8. PurchaseReceiptList.tsx
migrations['src/apps/transactions/models/purchase_receipt/pages/PurchaseReceiptList.tsx'] = '''import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchPurchaseReceipts } from "../services/purchaseReceiptApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import PurchaseReceiptDetail from "./PurchaseReceiptDetail";

export default function PurchaseReceiptList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedPurchaseReceipt, setSelectedPurchaseReceipt] = useState<any | null>(null);
  const [selectedPurchaseReceipts, setSelectedPurchaseReceipts] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const getPurchaseReceiptData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchPurchaseReceipts();
      if (res.status === 200) {
        setData(res.data.items || []);
      } else {
        dispatch(showToast({ message: "Failed to fetch purchase receipts", type: "error" }));
      }
    } catch (error) {
      console.error("Failed to fetch purchase receipts", error);
      dispatch(showToast({ message: "Failed to fetch purchase receipts", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getPurchaseReceiptData();
  }, [getPurchaseReceiptData]);

  const handleView = useCallback((row: any) => {
    setSelectedPurchaseReceipt(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback((row: any) => {
    setSelectedPurchaseReceipt(row);
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedPurchaseReceipt(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getPurchaseReceiptData();
    setFormMode(null);
    setSelectedPurchaseReceipt(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedPurchaseReceipt(null);
  };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete purchase receipt ${row.id}?`)) return;
    
    try {
      await deleteAction(row.id);
      dispatch(showToast({ message: "Purchase receipt deleted successfully", type: "success" }));
      getPurchaseReceiptData();
      if (selectedPurchaseReceipt && selectedPurchaseReceipt.id === row.id) {
        setFormMode(null);
        setSelectedPurchaseReceipt(null);
      }
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete purchase receipt", type: "error" }));
    }
  }, [dispatch, getPurchaseReceiptData, selectedPurchaseReceipt]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedPurchaseReceipts.length) return;
    if (!window.confirm(`Delete ${selectedPurchaseReceipts.length} purchase receipt(s)?`)) return;

    try {
      await Promise.all(selectedPurchaseReceipts.map((r) => deleteAction(r.id)));
      dispatch(showToast({ message: `${selectedPurchaseReceipts.length} purchase receipt(s) deleted`, type: "success" }));
      getPurchaseReceiptData();
      setSelectedPurchaseReceipts([]);
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete some purchase receipts", type: "error" }));
    }
  }, [selectedPurchaseReceipts, dispatch, getPurchaseReceiptData]);

  const columns: TableColumn<any>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "purchase_id", name: "Purchase ID", selector: (row) => row.purchase_id || "--", sortable: true, width: "15%" },
    { id: "receipt_date", name: "Receipt Date", selector: (row) => row.receipt_date || "--", sortable: true, width: "18%" },
    { id: "received_by", name: "Received By", selector: (row) => row.received_by || "--", sortable: true, width: "18%" },
    { id: "notes", name: "Notes", selector: (row) => row.notes || "--", sortable: true, width: "20%" },
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
      <PageBreadcrumb pageTitle="Purchase Receipt List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="Purchase Receipts"
              loading={loading}
              storageKey="purchase-receipt-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedPurchaseReceipts}
              exportFileName="purchase_receipts_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search purchase receipts..."
              noDataMessage="No purchase receipts found"
              customActions={
                <div className="flex gap-2">
                  {selectedPurchaseReceipts.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" />
                      Delete ({selectedPurchaseReceipts.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Purchase Receipt
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <PurchaseReceiptDetail
              inline
              modeProp={formMode}
              dataProp={selectedPurchaseReceipt}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
'''

# 9. LedgerList.tsx
migrations['src/apps/accounts/models/ledger/pages/LedgerList.tsx'] = '''import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import ComponentCard from "@/components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter } from "@/components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { getRecords, deleteRecord } from "@/api/wcapi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import LedgerDisplay from "./LedgerDisplay";

export default function LedgerList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedLedger, setSelectedLedger] = useState<any | null>(null);
  const [selectedLedgers, setSelectedLedgers] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const getLedgerData = useCallback(async () => {
    try {
      setLoading(true);
      const list = await getRecords('ledger');
      const recs = Array.isArray(list?.results) ? list.results : Array.isArray(list) ? list : [];
      setData(recs);
    } catch (error) {
      console.error("Failed to fetch ledgers", error);
      dispatch(showToast({ message: "Failed to fetch ledgers", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getLedgerData();
  }, [getLedgerData]);

  const handleView = useCallback((row: any) => {
    setSelectedLedger(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback((row: any) => {
    setSelectedLedger(row);
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedLedger(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getLedgerData();
    setFormMode(null);
    setSelectedLedger(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedLedger(null);
  };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete ledger ${row.name || row.id}?`)) return;
    
    try {
      await deleteRecord('ledger', row.id);
      dispatch(showToast({ message: "Ledger deleted successfully", type: "success" }));
      getLedgerData();
      if (selectedLedger && selectedLedger.id === row.id) {
        setFormMode(null);
        setSelectedLedger(null);
      }
    } catch {
      dispatch(showToast({ message: "Failed to delete ledger", type: "error" }));
    }
  }, [dispatch, getLedgerData, selectedLedger]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedLedgers.length) return;
    if (!window.confirm(`Delete ${selectedLedgers.length} ledger(s)?`)) return;

    try {
      await Promise.all(selectedLedgers.map((l) => deleteRecord('ledger', l.id)));
      dispatch(showToast({ message: `${selectedLedgers.length} ledger(s) deleted`, type: "success" }));
      getLedgerData();
      setSelectedLedgers([]);
    } catch {
      dispatch(showToast({ message: "Failed to delete some ledgers", type: "error" }));
    }
  }, [selectedLedgers, dispatch, getLedgerData]);

  const filters: ColumnFilter[] = useMemo(() => [
    { key: "type", label: "Type", type: "text" },
  ], []);

  const columns: TableColumn<any>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "name", name: "Name", selector: (row) => row.name || "--", sortable: true, width: "30%" },
    { id: "type", name: "Type", selector: (row) => row.type || "--", sortable: true, width: "25%" },
    { id: "balance", name: "Balance", selector: (row) => row.balance || "--", sortable: true, width: "20%" },
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
      <PageBreadcrumb pageTitle="Ledger List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="Ledgers"
              loading={loading}
              filters={filters}
              storageKey="ledger-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedLedgers}
              exportFileName="ledgers_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search ledgers..."
              noDataMessage="No ledgers found"
              customActions={
                <div className="flex gap-2">
                  {selectedLedgers.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" />
                      Delete ({selectedLedgers.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Ledger
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <LedgerDisplay
              inline
              modeProp={formMode}
              dataProp={selectedLedger}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
'''

# 10. TaxJurisdictionList.tsx
migrations['src/apps/accounts/models/tax_jurisdiction/pages/TaxJurisdictionList.tsx'] = '''import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import ComponentCard from "@/components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter } from "@/components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { getRecords, deleteRecord } from "@/api/wcapi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import TaxJurisdictionDisplay from "./TaxJurisdictionDisplay";

export default function TaxJurisdictionList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedTaxJurisdiction, setSelectedTaxJurisdiction] = useState<any | null>(null);
  const [selectedTaxJurisdictions, setSelectedTaxJurisdictions] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const getTaxJurisdictionData = useCallback(async () => {
    try {
      setLoading(true);
      const list = await getRecords('tax_jurisdiction');
      const recs = Array.isArray(list?.results) ? list.results : Array.isArray(list) ? list : [];
      setData(recs);
    } catch (error) {
      console.error("Failed to fetch tax jurisdictions", error);
      dispatch(showToast({ message: "Failed to fetch tax jurisdictions", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getTaxJurisdictionData();
  }, [getTaxJurisdictionData]);

  const handleView = useCallback((row: any) => {
    setSelectedTaxJurisdiction(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback((row: any) => {
    setSelectedTaxJurisdiction(row);
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedTaxJurisdiction(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getTaxJurisdictionData();
    setFormMode(null);
    setSelectedTaxJurisdiction(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedTaxJurisdiction(null);
  };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete tax jurisdiction ${row.name || row.id}?`)) return;
    
    try {
      await deleteRecord('tax_jurisdiction', row.id);
      dispatch(showToast({ message: "Tax Jurisdiction deleted successfully", type: "success" }));
      getTaxJurisdictionData();
      if (selectedTaxJurisdiction && selectedTaxJurisdiction.id === row.id) {
        setFormMode(null);
        setSelectedTaxJurisdiction(null);
      }
    } catch {
      dispatch(showToast({ message: "Failed to delete tax jurisdiction", type: "error" }));
    }
  }, [dispatch, getTaxJurisdictionData, selectedTaxJurisdiction]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedTaxJurisdictions.length) return;
    if (!window.confirm(`Delete ${selectedTaxJurisdictions.length} tax jurisdiction(s)?`)) return;

    try {
      await Promise.all(selectedTaxJurisdictions.map((t) => deleteRecord('tax_jurisdiction', t.id)));
      dispatch(showToast({ message: `${selectedTaxJurisdictions.length} tax jurisdiction(s) deleted`, type: "success" }));
      getTaxJurisdictionData();
      setSelectedTaxJurisdictions([]);
    } catch {
      dispatch(showToast({ message: "Failed to delete some tax jurisdictions", type: "error" }));
    }
  }, [selectedTaxJurisdictions, dispatch, getTaxJurisdictionData]);

  const filters: ColumnFilter[] = useMemo(() => [
    { key: "code", label: "Code", type: "text" },
  ], []);

  const columns: TableColumn<any>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "name", name: "Name", selector: (row) => row.name || "--", sortable: true, width: "30%" },
    { id: "code", name: "Code", selector: (row) => row.code || "--", sortable: true, width: "20%" },
    { id: "rate", name: "Rate", selector: (row) => row.rate || "--", sortable: true, width: "20%" },
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
      <PageBreadcrumb pageTitle="Tax Jurisdiction List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="Tax Jurisdictions"
              loading={loading}
              filters={filters}
              storageKey="tax-jurisdiction-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedTaxJurisdictions}
              exportFileName="tax_jurisdictions_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search tax jurisdictions..."
              noDataMessage="No tax jurisdictions found"
              customActions={
                <div className="flex gap-2">
                  {selectedTaxJurisdictions.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" />
                      Delete ({selectedTaxJurisdictions.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Tax Jurisdiction
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <TaxJurisdictionDisplay
              inline
              modeProp={formMode}
              dataProp={selectedTaxJurisdiction}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
'''

# 11. GLJournalList.tsx
migrations['src/apps/accounts/models/gl_journal/pages/GLJournalList.tsx'] = '''import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import ComponentCard from "@/components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter } from "@/components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { fetchGLJournals, deleteGLJournal } from "../services/glJournalApi";
import GLJournalDetail from "./GLJournalDetail";

export default function GLJournalList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedGLJournal, setSelectedGLJournal] = useState<any | null>(null);
  const [selectedGLJournals, setSelectedGLJournals] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const getGLJournalData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchGLJournals();
      if (res.status === 200) {
        setData(res.data.items || []);
      } else {
        dispatch(showToast({ message: "Failed to fetch gl journals", type: "error" }));
      }
    } catch (error) {
      console.error("Failed to fetch gl journals", error);
      dispatch(showToast({ message: "Failed to fetch gl journals", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getGLJournalData();
  }, [getGLJournalData]);

  const handleView = useCallback((row: any) => {
    setSelectedGLJournal(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback((row: any) => {
    setSelectedGLJournal(row);
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedGLJournal(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getGLJournalData();
    setFormMode(null);
    setSelectedGLJournal(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedGLJournal(null);
  };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete gl journal ${row.id}?`)) return;
    
    try {
      await deleteGLJournal(row.id);
      dispatch(showToast({ message: "GL Journal deleted successfully", type: "success" }));
      getGLJournalData();
      if (selectedGLJournal && selectedGLJournal.id === row.id) {
        setFormMode(null);
        setSelectedGLJournal(null);
      }
    } catch {
      dispatch(showToast({ message: "Failed to delete gl journal", type: "error" }));
    }
  }, [dispatch, getGLJournalData, selectedGLJournal]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedGLJournals.length) return;
    if (!window.confirm(`Delete ${selectedGLJournals.length} gl journal(s)?`)) return;

    try {
      await Promise.all(selectedGLJournals.map((j) => deleteGLJournal(j.id)));
      dispatch(showToast({ message: `${selectedGLJournals.length} gl journal(s) deleted`, type: "success" }));
      getGLJournalData();
      setSelectedGLJournals([]);
    } catch {
      dispatch(showToast({ message: "Failed to delete some gl journals", type: "error" }));
    }
  }, [selectedGLJournals, dispatch, getGLJournalData]);

  const filters: ColumnFilter[] = useMemo(() => [
    { key: "type", label: "Type", type: "text" },
  ], []);

  const columns: TableColumn<any>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "date", name: "Date", selector: (row) => row.date || "--", sortable: true, width: "15%" },
    { id: "description", name: "Description", selector: (row) => row.description || "--", sortable: true, width: "30%" },
    { id: "amount", name: "Amount", selector: (row) => row.amount || "--", sortable: true, width: "15%" },
    { id: "type", name: "Type", selector: (row) => row.type || "--", sortable: true, width: "12%" },
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
      <PageBreadcrumb pageTitle="GL Journal List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="GL Journals"
              loading={loading}
              filters={filters}
              storageKey="gl-journal-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedGLJournals}
              exportFileName="gl_journals_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search gl journals..."
              noDataMessage="No gl journals found"
              customActions={
                <div className="flex gap-2">
                  {selectedGLJournals.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" />
                      Delete ({selectedGLJournals.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add GL Journal
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <GLJournalDetail
              inline
              modeProp={formMode}
              dataProp={selectedGLJournal}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
'''

# Run migrations
def main():
    base_path = os.path.dirname(os.path.abspath(__file__))
    success = []
    failed = []
    
    for file_path, content in migrations.items():
        full_path = os.path.join(base_path, file_path)
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            success.append(file_path)
            print(f"✓ Migrated: {file_path}")
        except Exception as e:
            failed.append((file_path, str(e)))
            print(f"✗ Failed: {file_path} - {e}")
    
    print(f"\n=== Migration Summary ===")
    print(f"Successful: {len(success)}")
    print(f"Failed: {len(failed)}")
    
    if failed:
        print("\nFailed files:")
        for f, err in failed:
            print(f"  - {f}: {err}")

if __name__ == "__main__":
    main()
