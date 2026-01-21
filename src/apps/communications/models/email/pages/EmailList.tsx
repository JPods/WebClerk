import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, {
  ColumnFilter,
} from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { getRecord } from "../../../../../api/wcapi";
import { fetchEmails, deleteEmail } from "../services/emailApi";
import { FaEye, FaEdit, FaTrash, FaPlus } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import EmailDetail from "./EmailDetail";
import Badge from "@/components/ui/badge/Badge";
import { dynamicData } from "../../../../../model/dynamicData";
import EmailListMobile from "../components/EmailListMobile";

export default function EmailList() {
  const [data, setData] = useState<dynamicData[]>([]);
  const [selectedEmails, setSelectedEmails] = useState<dynamicData[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<dynamicData | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    null
  );
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();
  const getEmailData = useCallback(async (emailId?: number) => {
    setLoading(true);
    try {
      const res = await fetchEmails();
      setData(res.data.data.results);
      if (emailId) {
        const contactRes = await getRecord("contact", emailId);
        setSelectedEmail(contactRes.record);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    getEmailData();
  }, [getEmailData]);

  const handleView = (row: dynamicData) => {
    setSelectedEmail(row);
    setFormMode("view");
  };

  const handleEdit = async (row: dynamicData) => {
    try {
      const res = await fetchEmails(row.id);
      if (res.status === 200) setSelectedEmail(res.data.data.record);
      else setSelectedEmail(row);
    } catch (error) {
      setSelectedEmail(row);
    }
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedEmail(null);
    setFormMode("add");
  };

  const handleDelete = async (row: dynamicData) => {
    if (window.confirm(`Delete email ${row.id}?`)) {
      try {
        await deleteEmail("email", row.id);
        dispatch(
          showToast({
            message: "Email deleted successfully",
            type: "success",
          })
        );
        getEmailData(); // Refresh data
        if (selectedEmail && selectedEmail.id === row.id) {
          setFormMode(null);
          setSelectedEmail(null);
        }
      } catch (error) {
        dispatch(
          showToast({
            message: "Failed to delete email",
            type: "error",
          })
        );
      }
    }
  };

  const handleFormSaved = () => {
    getEmailData();
    setFormMode(null);
    setSelectedEmail(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedEmail(null);
  };

  const filters: ColumnFilter[] = useMemo(
    () => [
      {
        key: "is_primary",
        label: "Primary",
        type: "select",
        options: [
          { value: "true", label: "Yes" },
          { value: "false", label: "No" },
        ],
      },
      {
        key: "is_verified",
        label: "Verified",
        type: "select",
        options: [
          { value: "true", label: "Yes" },
          { value: "false", label: "No" },
        ],
      },
    ],
    []
  );

  const handleBulkDelete = async () => {
    if (!selectedEmails.length) return;
    if (!window.confirm(`Delete ${selectedEmails.length} emails?`)) return;

    try {
      await Promise.all(
        selectedEmails.map((row) => deleteEmail("email", row.id))
      );
      dispatch(
        showToast({
          message: "Emails deleted successfully",
          type: "success",
        })
      );
      setSelectedEmails([]);
      getEmailData();
    } catch (error) {
      dispatch(
        showToast({
          message: "Failed to delete emails",
          type: "error",
        })
      );
    }
  };
  /* ---------------- Columns ---------------- */
  const userColumns: TableColumn<dynamicData>[] = useMemo(
    () => [
      { name: "id", selector: (row) => row.id, sortable: true, width: "5%" },
      {
        name: "email",
        selector: (row) => row.email || "--",
        cell: (row) => (row.email ? row.email.toString() : "--"),
        sortable: true,
        width: "15%",
      },
      {
        name: "name",
        selector: (row) => row.name || "--",
        cell: (row) => (row.name ? row.name.toString() : "--"),
        sortable: true,
        width: "20%",
      },

      {
        name: "attention",
        selector: (row) => row.attention || "--",
        cell: (row) => (row.attention ? row.attention.toString() : "--"),
        sortable: true,
        width: "25%",
      },

      {
        name: "is_primary",
        selector: (row) => (row.is_primary ? "Yes" : "No"), // Plain string for filtering
        cell: (row) => (
          <>
            <Badge size="sm" color={row.is_primary ? "success" : "warning"}>
              {row.is_primary ? "Yes" : "No"}
            </Badge>
          </>
        ),
        sortable: true,
        width: "10%",
      },
      {
        name: "is_verified",
        selector: (row) => (row.is_verified ? "Yes" : "No"), // Plain string for filtering
        cell: (row) => (
          <>
            <Badge size="sm" color={row.is_verified ? "success" : "warning"}>
              {row.is_verified ? "Yes" : "No"}
            </Badge>
          </>
        ),
        sortable: true,
        width: "10%",
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
      <PageBreadcrumb pageTitle="Email List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="w-full overflow-x-auto rounded-md cus-bg-purple-light dark:bg-[#1e2636] h-[calc(100vh-265px)]">
                  {formMode ? ( 
                <div className="flex flex-col">
                  <EmailListMobile
                    dataProp={data}
                    handleView={handleView}
                    handleEdit={handleEdit}
                  />
                </div>
              ) : (
                <AdvancedDataTable
                  data={data}
                  columns={userColumns}
                  title="Emails"
                  storageKey="communications.email.list"
                  loading={loading}
                  filters={filters}
                  enableExport={true}
                  enableSelection={true}
                  onSelectionChange={setSelectedEmails}
                  exportFileName="emails_export"
                  searchPlaceholder="Search emails, names, attention..."
                  noDataMessage="No emails found"
                  customActions={
                    <div className="flex gap-2">
                      {selectedEmails.length > 0 && (
                        <button
                          onClick={handleBulkDelete}
                          className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                        >
                          <FaTrash className="w-4 h-4" />
                          Delete ({selectedEmails.length})
                        </button>
                      )}
                      <button
                        onClick={handleAdd}
                        className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        <FaPlus className="w-4 h-4" />
                        New Email
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
            <EmailDetail
              inline
              modeProp={formMode}
              dataProp={selectedEmail}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
