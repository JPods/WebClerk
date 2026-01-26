/**
 * EmployeeList - Employee listing page using AdvancedDataTable
 * Admin-only access
 */
import OrgEntityList from "@/apps/orgs/components/OrgEntityList";
import { fetchEmployees, deleteEmployee } from "../services/employeeApi";
import EmployeeDetail from "./EmployeeDetail";
import { AdminGuard } from "@/components/auth/AdminGuard";

const columns = [
  { id: "id", name: "ID", selector: (row: any) => row.id, sortable: true, width: "80px" },
  { id: "display_name", name: "Name", selector: (row: any) => row.display_name || row.name || "--", sortable: true },
  { id: "status", name: "Status", selector: (row: any) => row.status || "--", sortable: true, width: "120px" },
  { id: "is_active", name: "Active", selector: (row: any) => row.is_active ? "Yes" : "No", sortable: true, width: "100px" },
  { id: "email", name: "Email", selector: (row: any) => row.email || "--", sortable: true },
];

function EmployeeList() {
  return (
    <OrgEntityList
      modelKey="employee"
      title="Employees"
      fetchFn={fetchEmployees}
      deleteFn={deleteEmployee}
      columns={columns}
      storageKey="employee-list"
      exportFileName="employee_export"
      displayComponent={EmployeeDetail}
      // Routes omitted; using inline + child edit windows where available
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
