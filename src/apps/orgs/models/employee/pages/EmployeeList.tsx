/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * EmployeeList - Employee listing page using AdvancedDataTable
 * Admin-only access
 */
import OrgEntityList from "@/apps/orgs/components/OrgEntityList";
import { fetchEmployees, deleteEmployee } from "../services/employeeApi";
import EmployeeDetail from "./EmployeeDetail";
import { AdminGuard } from "@/components/auth/AdminGuard";

import type { ColumnFilter } from "@/components/common/ButtonToolbar";
import { FaEye, FaEdit, FaTrash } from "react-icons/fa";
import { useState, useCallback } from "react";

const getInitials = (value: unknown) => {
  const name = String(value ?? "").trim();
  if (!name) return "?";
  const parts = name.split(/\s+/).filter(Boolean);
  const first = parts[0]?.[0] ?? "";
  const last = (parts.length > 1 ? parts[parts.length - 1]?.[0] : "") ?? "";
  return (first + last).toUpperCase() || "?";
};

const normalizeStatus = (row: any): string => {
  const raw = (row?.status ?? "").toString().trim().toLowerCase();
  if (raw) return raw;
  if (typeof row?.is_active === "boolean") return row.is_active ? "active" : "inactive";
  return "unknown";
};

const statusBadgeClass = (status: string) => {
  switch (status) {
    case "active":
      return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
    case "prospect":
    case "pending":
      return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
    case "inactive":
    case "retired":
      return "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200";
    case "suspended":
      return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
    default:
      return "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200";
  }
};

const columns = (actions: {
  onView: (row: any) => void;
  onEdit: (row: any) => void;
  onDelete: (row: any) => void;
}): any[] => [
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
        {row.employee_id || row.id}
      </div>
    ),
  },
  {
    name: "Name",
    selector: (row: any) => row.display_name || row.name || "--",
    sortable: true,
    cell: (row: any) => (
      <div className="flex items-center gap-3 min-w-0">
        <div className="h-8 w-8 shrink-0 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center text-xs font-semibold text-slate-700 dark:text-slate-200">
          {getInitials(row.display_name || row.name)}
        </div>
        <div className="min-w-0">
          <div className="font-medium text-gray-900 dark:text-white truncate">
            {row.display_name || row.name || "--"}
          </div>
          <div className="text-xs text-slate-500 dark:text-slate-400 truncate">
            {row.department || row.title || row.role || row.position || ""}
          </div>
        </div>
      </div>
    ),
  },
  {
    name: "Status",
    selector: (row: any) => normalizeStatus(row),
    sortable: true,
    width: "120px",
    cell: (row: any) => (
      (() => {
        const status = normalizeStatus(row);
        const label = status ? status.charAt(0).toUpperCase() + status.slice(1) : "Unknown";
        return (
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusBadgeClass(status)}`}>
            {label}
          </span>
        );
      })()
    ),
  },
  {
    name: "Email",
    selector: (row: any) => row.email || "--",
    sortable: true,
    cell: (row: any) => {
      const email = row.email?.toString().trim();
      if (!email) return <span className="text-slate-400">--</span>;
      return (
        <a
          href={`mailto:${email}`}
          onClick={(e) => e.stopPropagation()}
          className="text-blue-600 dark:text-blue-400 hover:underline truncate"
          title={email}
        >
          {email}
        </a>
      );
    },
  },
  {
    name: "Phone",
    selector: (row: any) => row.phone || "--",
    sortable: true,
    cell: (row: any) => {
      const phone = row.phone?.toString().trim();
      if (!phone) return <span className="text-slate-400">--</span>;
      return (
        <a
          href={`tel:${phone}`}
          onClick={(e) => e.stopPropagation()}
          className="text-slate-700 dark:text-slate-200 hover:underline"
          title={phone}
        >
          {phone}
        </a>
      );
    },
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
          aria-label="View employee"
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
          aria-label="Edit employee"
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
          aria-label="Delete employee"
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
      { value: "prospect", label: "Prospect" },
      { value: "inactive", label: "Inactive" },
      { value: "pending", label: "Pending" },
      { value: "suspended", label: "Suspended" },
      { value: "retired", label: "Retired" },
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
