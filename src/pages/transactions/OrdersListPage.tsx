import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import ComponentCard from "../../components/common/ComponentCard";
import DataTable, { TableColumn } from 'react-data-table-component';
import { createTheme } from 'react-data-table-component';
import { useEffect, useState } from "react";
import { Contacts, deleteAction } from "../../api/userProfile";
import { dynamicData } from "../../model/dynamicData";
import { FaEye, FaEdit, FaTrash, FaPlus } from 'react-icons/fa'; 
import { showToast } from "../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useTheme } from "../../context/ThemeContext";
import { OrderDetailPage } from "../wrapperPage";

import { getOrdersData } from "../../api/orderDetails";


// Create the dark theme only once
createTheme('tailwindDark', {
  text: {
    primary: '#d1d5db',
    secondary: '#9ca3af',
  },
  background: {
    default: '#111827',
  },
  context: {
    background: '#1f2937',
    text: '#d1d5db',
  },
  divider: {
    default: '#374151',
  },
  button: {
    default: '#1f2937',
    hover: '#374151',
    focus: '#6b7280',
    disabled: '#4b5563',
  },
  sortFocus: {
    default: '#d1d5db',
  },
  highlightOnHover: {
    default: '#1e293b',
    text: '#d1d5db',
  },
  striped: {
    default: '#1f2937',
    text: '#d1d5db',
  },
});

export default function OrdersListPage() {
  const { theme } = useTheme();
  const [data, setData] = useState<dynamicData[]>([]);
  const [selectedOrder, setSelectedOrder] = useState<dynamicData | null>(null);
  const [formMode, setFormMode] = useState<'add' | 'edit' | 'view' | null>(null);
  
  const dispatch = useDispatch();

  const fetchOrderData = async () => {
    try {
      const res = await getOrdersData();
      if (res.status === 200) {
        setData(res.data.data.results);
      }
    } catch (error) {
      console.error("Failed to fetch contacts", error);
    }
  };

  useEffect(() => {
    fetchOrderData();
  }, []);

  const handleView = (row: dynamicData) => {
    setSelectedOrder(row);
    setFormMode('view');
  };

  const handleEdit = async (row: dynamicData) => {
     const res = await Contacts(row.id);
      if (res.status === 200) 
        setSelectedOrder(res.data.data.record);
      else
        setSelectedOrder(row);
    setFormMode('edit');
  };

  const handleAdd = () => {
    setSelectedOrder(null);
    setFormMode('add');
  };

  const handleDelete = async (row: dynamicData) => {
    if (window.confirm(`Delete order ${row.name_first}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(showToast({ message: "Order deleted successfully", type: "success" }));
        fetchOrderData(); // Refresh data
        if (selectedOrder && selectedOrder.id === row.id) {
          setFormMode(null);
          setSelectedOrder(null);
        }
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete order", type: "error" }));
      }
    }
  };

  const handleFormSaved = () => {
    fetchOrderData();
    setFormMode(null);
    setSelectedOrder(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedOrder(null);
  };

  const userColumns: TableColumn<dynamicData>[] = [
    { name: 'First Name', selector: (row) => row.name_first, sortable: true },
    { name: 'Last Name', selector: (row) => row.name_last, sortable: true },
    { name: 'Company', selector: (row) => row.company, sortable: true },
    {
      name: 'Action',
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
      <PageBreadcrumb pageTitle="Order Details" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button 
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600"
              >
                <FaPlus />
                Add Orders
              </button>
            </div>
            <div className="overflow-x-auto bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-400 rounded-md">
              <DataTable
                columns={userColumns}
                data={data}
                pagination
                theme={theme === 'dark' ? 'tailwindDark' : 'default'}
                highlightOnHover
                pointerOnHover
                onRowClicked={(row) => handleView(row)}
              />
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <OrderDetailPage
              inline
              modeProp={formMode}
              dataProp={selectedOrder}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
