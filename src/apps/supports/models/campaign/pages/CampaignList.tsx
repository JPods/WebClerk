import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import ComponentCard from "@/components/common/ComponentCard";
import AdvancedDataTable from "@/components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { getRecords } from "@/api/wcapi";
import { FaEye, FaEdit, FaPlus, FaTrashAlt } from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { deleteRecord } from "@/api/wcapi";
import CampaignDisplay from "./CampaignDisplay";

export default function CampaignList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedCampaign, setSelectedCampaign] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);

  const dispatch = useDispatch();

  const getCampaignData = useCallback(async () => {
    try {
      setLoading(true);
      const list = await getRecords('campaign');
      const recs = Array.isArray(list?.results) ? list.results : Array.isArray(list) ? list : [];
      setData(recs);
    } catch (error) {
      console.error("Failed to fetch campaigns", error);
      dispatch(showToast({ message: "Failed to fetch campaigns", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getCampaignData();
  }, [getCampaignData]);

  // Handle database search
  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    const query = terms.join(' ');
    setLoading(true);
    try {
      const list = await getRecords('campaign', { search: query });
      const recs = Array.isArray(list?.results) ? list.results : Array.isArray(list) ? list : [];
      setData(recs);
    } catch (error) {
      console.error("Database search error:", error);
      dispatch(showToast({ message: "Search failed", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  const handleView = (row: any) => {
    setSelectedCampaign(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedCampaign(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedCampaign(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getCampaignData();
    setFormMode(null);
    setSelectedCampaign(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedCampaign(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete campaign ${row.id}?`)) {
      try {
        await deleteRecord('campaign', row.id);
        dispatch(showToast({ message: "Campaign deleted successfully", type: "success" }));
        getCampaignData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete campaign", type: "error" }));
      }
    }
  };

  // Hardcoded columns: id and common fields
  const userColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "10%" },
    { name: "Name", selector: (row) => row.name || "--", sortable: true, width: "30%" },
    { name: "Start Date", selector: (row) => row.start_date || "--", sortable: true, width: "20%" },
    { name: "End Date", selector: (row) => row.end_date || "--", sortable: true, width: "20%" },
    { name: "Status", selector: (row) => row.status || "--", sortable: true, width: "20%" },
  ];

  userColumns.push({
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
          <FaTrashAlt className="text-red-600 hover:scale-110 transition" />
        </button>
      </div>
    ),
    ignoreRowClick: true,
    allowOverflow: true,
    button: true,
  });

  return (
    <>
      <PageBreadcrumb pageTitle="Campaign List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Campaign
              </button>
            </div>
            <div className="overflow-x-auto bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-400 rounded-md">
              <AdvancedDataTable
                columns={userColumns.map((col) => ({
                  ...col,
                  name: typeof col.name === "string" ? col.name.toUpperCase() : col.name,
                }))}
                data={data}
                storageKey="campaign_list"
                loading={loading}
                onRowActivate={handleEdit}
                enableDatabaseSearch={true}
                searchDatabase={searchDatabase}
                onSearchModeChange={setSearchDatabase}
                onDatabaseSearch={handleDatabaseSearch}
              />
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <CampaignDisplay
              inline
              modeProp={formMode}
              dataProp={selectedCampaign}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}