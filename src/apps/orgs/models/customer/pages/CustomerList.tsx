import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter } from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { fetchCustomers, deleteCustomer } from "../services/customerApi";
import { FaCheck, FaTimes } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { PageRoutes } from "../../../../../routes/Routes";
import { useWindowManager } from "../../../../../context/WindowManagerContext";
import { dynamicData } from "../../../../../model/dynamicData";
import CustomerDisplay from "./CustomerDisplay";

export default function CustomerList() {
  const dispatch = useDispatch();
  const { ensureWindow, activateWindow } = useWindowManager();
  const [data, setData] = useState<dynamicData[]>([]);
  const [selectedCustomers, setSelectedCustomers] = useState<dynamicData[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<dynamicData | null>(null);
  const [loading, setLoading] = useState(false);

  const getCustomerData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchCustomers();
      const results = res.data.data.results || [];
      setData(results);
    } catch (error) {
      console.error("Failed to fetch customers", error);
      dispatch(showToast({ message: "Failed to fetch customers", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getCustomerData();
  }, [getCustomerData]);

  const handleRowDoubleClick = useCallback((row: dynamicData) => {
    const id = row.id;
    const display = row.display_name || row.name || `Customer ${id}`;
    const path = `${PageRoutes.customerDetail}/${id}`;
    ensureWindow(path, display, { maximized: false });
    activateWindow(path);
  }, [ensureWindow, activateWindow]);

  const handleEdit = useCallback((row: dynamicData) => {
    const id = row.id;
    const display = row.display_name || row.name || `Customer ${id}`;
    const path = `${PageRoutes.customerEdit}/${id}`;
    ensureWindow(path, `Edit ${display}`, { maximized: false });
    activateWindow(path);
  }, [ensureWindow, activateWindow]);

  const handleAdd = () => {
    const path = PageRoutes.customerAdd;
    ensureWindow(path, "Add Customer", { maximized: false });
    activateWindow(path);
  };

  const handleBulkDelete = useCallback(async (rows?: dynamicData[]) => {
    const targetRows = rows && rows.length ? rows : selectedCustomers;
    if (!targetRows.length) return;
    if (!window.confirm(`Delete ${targetRows.length} customer(s)?`)) return;

    try {
      await Promise.all(targetRows.map((c) => deleteCustomer(c.id)));
      dispatch(showToast({ message: `${targetRows.length} customer(s) deleted`, type: "success" }));
      getCustomerData();
      setSelectedCustomers([]);
    } catch {
      dispatch(showToast({ message: "Failed to delete some customers", type: "error" }));
    }
  }, [selectedCustomers, dispatch, getCustomerData]);

  const handleImportFile = (file: File) => {
    dispatch(showToast({ message: `Import not implemented. Selected: ${file.name}`, type: "info" }));
  };

  const handlePrint = () => {
    window.print();
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
    { id: "id", name: "ID", selector: (row: dynamicData) => row.id, sortable: true, width: "80px" },
    { id: "display_name", name: "Display Name", selector: (row: dynamicData) => row.display_name || "--", sortable: true, width: "25%" },
    { id: "org_type", name: "Org Type", selector: (row: dynamicData) => row.org_type || "--", sortable: true, width: "12%" },
    { id: "status", name: "Status", selector: (row: dynamicData) => row.status || "--", sortable: true, width: "15%" },
    {
      id: "is_active",
      name: "Active",
      selector: (row: dynamicData) => (row.is_active ? "yes" : "no"),
      cell: (row: dynamicData) => (
        row.is_active 
          ? <FaCheck className="text-green-600" /> 
          : <FaTimes className="text-yellow-600" />
      ),
      sortable: true,
      width: "10%",
    },
    { id: "version", name: "Version", selector: (row: dynamicData) => row.version || "--", sortable: true, width: "10%" },
  ], []);

  return (
    <>
      <PageBreadcrumb pageTitle="Customer" />
      <div className="grid grid-cols-1 gap-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div>
            <ComponentCard>
              <AdvancedDataTable
                data={data}
              columns={columns}
              title="Customers"
              loading={loading}
              filters={filters}
              storageKey="customer-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedCustomers}
                onVisibleRowsChange={(rows) => {
                const ids = rows
                  .map((row: dynamicData) => row.id)
                  .filter((id: number) => Number.isFinite(id));
                localStorage.setItem("customer-list-order", JSON.stringify(ids));
              }}
              onEditSelected={handleEdit}
              exportFileName="customers_export"
                  onRowActivate={handleEdit}
                  onRowDoubleClicked={handleRowDoubleClick}
                  onRowClicked={(row) => setSelectedCustomer(row)}
              onAdd={handleAdd}
              onDeleteSelected={handleBulkDelete}
              onImportFile={handleImportFile}
              onPrint={handlePrint}
              noDataMessage="No customers found"
            />
          </ComponentCard>
            </div>

            <div>
              <ComponentCard>
                {selectedCustomer ? (
                  // Show inline customer detail for single-click selection
                  // CustomerDisplay expects props matching CustomerAddProps
                  <CustomerDisplay inline={true} dataProp={selectedCustomer} />
                ) : (
                  <div className="p-6 text-sm text-gray-500">Click a customer on the left to see details here.</div>
                )}
              </ComponentCard>
            </div>
          </div>
        </div>
    </>
  );
}
