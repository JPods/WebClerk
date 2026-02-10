/**
 * EmployeeList - Employee listing page using AdvancedDataTable
 * Admin-only access
 */
import OrgEntityList from "@/apps/orgs/components/OrgEntityList";
import { fetchEmployees, deleteEmployee } from "../services/employeeApi";
import EmployeeDetail from "./EmployeeDetail";
import { AdminGuard } from "@/components/auth/AdminGuard";
import { TableColumn } from "react-data-table-component";
import { ColumnFilter } from "@/components/common/AdvancedDataTable";
import { FaEye, FaEdit, FaTrash } from "react-icons/fa";
import { useState, useCallback } from "react";

const columns = (actions: {
  onView: (row: any) => void;
  onEdit: (row: any) => void;
  onDelete: (row: any) => void;
}): TableColumn<any>[] => [
  {
    name: "ID",
    selector: (row: any) => row.id,
    sortable: true,
    width: "80px",
    cell: (row: any) => (
      <div
        onClick={(e) => {
          e.stopPropagation();
          actions.onEdit(row);
        }}
        className="text-xs font-mono text-blue-600 dark:text-blue-400 cursor-pointer hover:underline"
      >
        {row.id}
      </div>
    ),
  },
  {
    name: "Name",
    selector: (row: any) => row.display_name || row.name || "--",
    sortable: true,
    cell: (row: any) => (
      <div className="font-medium text-gray-900 dark:text-white">
        {row.display_name || row.name || "--"}
      </div>
    ),
  },
  {
    name: "Status",
    selector: (row: any) => row.status || "--",
    sortable: true,
    width: "120px",
    cell: (row: any) => (
      <span
        className={`px-2 py-1 rounded-full text-xs font-medium ${
          row.status === "active"
            ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
            : row.status === "pending"
            ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
            : row.status === "suspended"
            ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
            : "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200"
        }`}
      >
        {row.status || "Unknown"}
      </span>
    ),
  },
  {
    name: "Active",
    selector: (row: any) => row.is_active ? "Yes" : "No",
    sortable: true,
    width: "100px",
    cell: (row: any) => (
      <span
        className={`px-2 py-1 rounded-full text-xs font-medium ${
          row.is_active
            ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200"
            : "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400"
        }`}
      >
        {row.is_active ? "Yes" : "No"}
      </span>
    ),
  },
  {
    name: "Email",
    selector: (row: any) => row.email || "--",
    sortable: true,
  },
  {
    name: "Actions",
    width: "140px",
    cell: (row: any) => (
      <div className="flex gap-2">
        <button
          onClick={(e) => {
            e.stopPropagation();
            actions.onView(row);
          }}
          title="View"
          className="p-2 text-blue-600 text-xs hover:bg-blue-50 rounded dark:hover:bg-blue-900/20 transition-colors"
        >
          <FaEye className="w-4 h-4" />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            actions.onEdit(row);
          }}
          title="Edit"
          className="p-2 text-green-600 text-xs hover:bg-green-50 rounded dark:hover:bg-green-900/20 transition-colors"
        >
          <FaEdit className="w-4 h-4" />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            actions.onDelete(row);
          }}
          title="Delete"
          className="p-2 text-red-600 text-xs hover:bg-red-50 rounded dark:hover:bg-red-900/20 transition-colors"
        >
          <FaTrash className="w-4 h-4" />
        </button>
      </div>
    ),
  },
];

const filters: ColumnFilter[] = [
  {
    key: "status",
    name: "status",
    field: "status",
    label: "Status",
    type: "select",
    options: [
      { value: "active", label: "Active" },
      { value: "inactive", label: "Inactive" },
      { value: "pending", label: "Pending" },
      { value: "suspended", label: "Suspended" },
    ],
  },
  {
    key: "is_active",
    name: "is_active",
    field: "is_active",
    label: "Active Status",
    type: "select",
    options: [
      { value: "true", label: "Active" },
      { value: "false", label: "Inactive" },
    ],
  },
];

function EmployeeList() {
  const [searchDatabase, setSearchDatabase] = useState(false);

  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    const searchQuery = terms.join(",");
    await fetchEmployees({ search: searchQuery });
  }, []);

  return (
    <OrgEntityList
      modelKey="employee"
      title="Employees"
      fetchFn={fetchEmployees}
      deleteFn={deleteEmployee}
      columns={columns}
      filters={filters}
      storageKey="employee-list"
      exportFileName="employee_export"
      displayComponent={EmployeeDetail}
      enableDatabaseSearch={true}
      searchDatabase={searchDatabase}
      onSearchModeChange={setSearchDatabase}
      onDatabaseSearch={handleDatabaseSearch}
    />
  );
}

export default function EmployeeListPage() {
  return (
    <AdminGuard>
      <EmployeeList />
    </AdminGuard>
  );
}
