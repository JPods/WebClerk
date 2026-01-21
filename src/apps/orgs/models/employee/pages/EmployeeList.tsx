/**
 * EmployeeList - Employee listing page using AdvancedDataTable
 * Admin-only access
 */
import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { fetchEmployees, deleteEmployee } from "../services/employeeApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { AdminGuard } from "@/components/auth/AdminGuard";
import EmployeeDetail from "./EmployeeDetail";

function EmployeeList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedEmployee, setSelectedEmployee] = useState<any | null>(null);
  const [selectedItems, setSelectedItems] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const getData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchEmployees();
      if (res.status === 200) {
        setData(res.data?.items || res.data?.data?.results || []);
      } else {
        dispatch(showToast({ message: "Failed to fetch employees", type: "error" }));
      }
    } catch (error) {
      dispatch(showToast({ message: "Failed to fetch employees", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => { getData(); }, [getData]);

  const handleView = useCallback((row: any) => { setSelectedEmployee(row); setFormMode("view"); }, []);
  const handleEdit = useCallback((row: any) => { setSelectedEmployee(row); setFormMode("edit"); }, []);
  const handleAdd = () => { setSelectedEmployee(null); setFormMode("add"); };
  const handleFormSaved = () => { getData(); setFormMode(null); setSelectedEmployee(null); };
  const handleFormCancel = () => { setFormMode(null); setSelectedEmployee(null); };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete employee ${row.display_name || row.name || row.id}?`)) return;
    try {
      await deleteEmployee(row.id);
      dispatch(showToast({ message: "Employee deleted successfully", type: "success" }));
      getData();
    } catch { dispatch(showToast({ message: "Failed to delete employee", type: "error" })); }
  }, [dispatch, getData]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedItems.length || !window.confirm(`Delete ${selectedItems.length} employee(s)?`)) return;
    try {
      await Promise.all(selectedItems.map((item) => deleteEmployee(item.id)));
      dispatch(showToast({ message: `${selectedItems.length} employee(s) deleted`, type: "success" }));
      getData(); setSelectedItems([]);
    } catch { dispatch(showToast({ message: "Failed to delete some employees", type: "error" })); }
  }, [selectedItems, dispatch, getData]);

  const columns: TableColumn<any>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "display_name", name: "Name", selector: (row) => row.display_name || row.name || "--", sortable: true },
    { id: "status", name: "Status", selector: (row) => row.status || "--", sortable: true, width: "120px" },
    { id: "is_active", name: "Active", selector: (row) => row.is_active ? "Yes" : "No", sortable: true, width: "100px" },
    { id: "email", name: "Email", selector: (row) => row.email || "--", sortable: true },
    {
      id: "actions",
      name: "Actions",
      cell: (row) => (
        <div className="flex gap-2">
          <button onClick={() => handleView(row)} title="View"><FaEye className="text-blue-600 hover:scale-110 transition" /></button>
          <button onClick={() => handleEdit(row)} title="Edit"><FaEdit className="text-green-600 hover:scale-110 transition" /></button>
          <button onClick={() => handleDelete(row)} title="Delete"><FaTrash className="text-red-600 hover:scale-110 transition" /></button>
        </div>
      ),
      ignoreRowClick: true, allowOverflow: true, button: true, width: "100px",
    },
  ], [handleDelete, handleEdit, handleView]);

  return (
    <>
      <PageBreadcrumb pageTitle="Employee List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="Employees"
              loading={loading}
              storageKey="employee-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedItems}
              exportFileName="employee_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search employees..."
              noDataMessage="No employees found"
              customActions={
                <div className="flex gap-2">
                  {selectedItems.length > 0 && (
                    <button onClick={handleBulkDelete} className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors">
                      <FaTrash className="w-4 h-4" /> Delete ({selectedItems.length})
                    </button>
                  )}
                  <button onClick={handleAdd} className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors">
                    <FaPlus className="w-4 h-4" /> Add Employee
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <EmployeeDetail 
              org={selectedEmployee || { id: 0 }} 
              mode={formMode} 
              onClose={handleFormCancel} 
              onSaved={handleFormSaved} 
            />
          </div>
        )}
      </div>
    </>
  );
}

// Export with AdminGuard wrapper for route protection
export default function EmployeeListPage() {
  return (
    <AdminGuard>
      <EmployeeList />
    </AdminGuard>
  );
}
