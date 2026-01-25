import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchSalesOrderLines } from "../services/salesOrderLineApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import SalesOrderLineDetail from "./SalesOrderLineDetail";

export default function SalesOrderLineList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedSalesOrderLine, setSelectedSalesOrderLine] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();

  const getSalesOrderLineData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchSalesOrderLines();
      if (res.status === 200) {
        setData(res.data.items);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch sales order lines", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch sales order lines", error);
      dispatch(showToast({ message: "Failed to fetch sales order lines", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getSalesOrderLineData();
  }, [getSalesOrderLineData]);

  const handleView = (row: any) => {
    setSelectedSalesOrderLine(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedSalesOrderLine(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedSalesOrderLine(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getSalesOrderLineData();
    setFormMode(null);
    setSelectedSalesOrderLine(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedSalesOrderLine(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete sales order line ${row.id}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(showToast({ message: "Sales order line deleted successfully", type: "success" }));
        getSalesOrderLineData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete sales order line", type: "error" }));
      }
    }
  };

  const userColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "5%" },
    {
      name: "Sales Order ID",
      selector: (row) => row.salesorder_id || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Item ID",
      selector: (row) => row.item_id || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Quantity",
      selector: (row) => row.quantity || "--",
      sortable: true,
      width: "10%",
    },
    {
      name: "Unit Price",
      selector: (row) => row.unit_price || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Line Total",
      selector: (row) => row.line_total || "--",
      sortable: true,
      width: "15%",
    },
    {
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
            <FaTrash className="text-red-600 hover:scale-110 transition" />
          </button>
        </div>
      ),
      ignoreRowClick: true,
      allowOverflow: true,
      button: true,
    },
  ];

  return (
    <>
      <PageBreadcrumb pageTitle="Sales Order Line List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Sales Order Line
              </button>
            </div>
            <div className="overflow-x-auto bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-400 rounded-md">
              <AdvancedDataTable
                columns={userColumns.map((col) => ({
                  ...col,
                  name: typeof col.name === "string" ? col.name.toUpperCase() : col.name,
                }))}
                data={data}
                storageKey="sales_order_line_list"
                onRowActivate={handleEdit}
                loading={loading}
              />
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <SalesOrderLineDetail
              inline
              modeProp={formMode}
              dataProp={selectedSalesOrderLine}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}