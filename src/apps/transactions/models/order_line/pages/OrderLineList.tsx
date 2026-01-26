import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchOrderLines } from "../services/orderLineApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import OrderLineDetail from "./OrderLineDetail";

export default function OrderLineList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedOrderLine, setSelectedOrderLine] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();

  const getOrderLineData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchOrderLines();
      if (res.status === 200) {
        setData(res.data.items);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch order lines", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch order lines", error);
      dispatch(showToast({ message: "Failed to fetch order lines", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getOrderLineData();
  }, [getOrderLineData]);

  const handleView = (row: any) => {
    setSelectedOrderLine(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedOrderLine(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedOrderLine(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getOrderLineData();
    setFormMode(null);
    setSelectedOrderLine(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedOrderLine(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete order line ${row.id}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(showToast({ message: "Order line deleted successfully", type: "success" }));
        getOrderLineData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete order line", type: "error" }));
      }
    }
  };

  const userColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "5%" },
    {
      name: "Order ID",
      selector: (row) => row.order_id || row.salesorder_id || "--",
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
      <PageBreadcrumb pageTitle="Order Line List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Order Line
              </button>
            </div>
            <div className="overflow-x-auto bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-400 rounded-md">
              <AdvancedDataTable
                columns={userColumns.map((col) => ({
                  ...col,
                  name: typeof col.name === "string" ? col.name.toUpperCase() : col.name,
                }))}
                data={data}
                storageKey="order_line_list"
                onRowActivate={handleEdit}
                loading={loading}
              />
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <OrderLineDetail
              inline
              modeProp={formMode}
              dataProp={selectedOrderLine}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}