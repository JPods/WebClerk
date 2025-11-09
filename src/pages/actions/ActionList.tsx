import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import ComponentCard from "../../components/common/ComponentCard";
import DataTable, { TableColumn } from 'react-data-table-component';
import { createTheme } from 'react-data-table-component';
import { useEffect, useMemo, useState } from "react";
import { Actions, Contacts, deleteAction } from "../../api/userProfile";
import { dynamicData } from "../../model/dynamicData";
import { FaEye, FaEdit, FaTrash, FaPlus } from 'react-icons/fa'; 
import { showToast } from "../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useTheme } from "../../context/ThemeContext";
import ActionAdd from "./ActionAdd";
import { get } from "react-hook-form";


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

export default function ActionList() {
  const { theme } = useTheme();
  const [data, setData] = useState<dynamicData[]>([]);
  const [selectedContact, setSelectedContact] = useState<dynamicData | null>(null);
  const [formMode, setFormMode] = useState<'add' | 'edit' | 'view' | null>(null);
  
  const dispatch = useDispatch();

  const getActionData = async () => {
    try {
      const res = await Actions();
      if (res.status === 200) {
        setData(res.data.data.results);
      }
    } catch (error) {
      console.error("Failed to fetch actions", error);
    }
  };

  useEffect(() => {
    getActionData();
  }, []);

  const handleView = (row: dynamicData) => {
    setSelectedContact(row);
    setFormMode('view');
  };

  const handleEdit = (row: dynamicData) => {
    setSelectedContact(row);
    setFormMode('edit');
  };

  const handleAdd = () => {
    setSelectedContact(null);
    setFormMode('add');
  };

  const handleDelete = async (row: dynamicData) => {
    if (window.confirm(`Delete contact ${row.name_first}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(showToast({ message: "Action deleted successfully", type: "success" }));
        getActionData(); // Refresh data
        if (selectedContact && selectedContact.id === row.id) {
          setFormMode(null);
          setSelectedContact(null);
        }
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete contact", type: "error" }));
      }
    }
  };

  const handleFormSaved = () => {
    getActionData();
    setFormMode(null);
    setSelectedContact(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedContact(null);
  };

  const columnOptions = useMemo(() => {
    const options = new Set<string>();
    data.forEach((item) => {
      const raw = item?.kanban_column ?? item?.column;
      if (typeof raw === "string") {
        const trimmed = raw.trim();
        if (trimmed) {
          options.add(trimmed);
        }
      }
    });
    return Array.from(options);
  }, [data]);

  const userColumns: TableColumn<dynamicData>[] = [
  { name: 'ID', selector: row => row.id, sortable: true },
   { name: 'Title', selector: row => row.action_en || row.action || '-', sortable: true },
      { name: 'Priority', selector: row => row.priority, sortable: true },
      { name: 'Difficulty', selector: row => row.difficulty, sortable: true },
      { name: 'Status', selector: row => row.status, sortable: true },
      { name: 'Quality', selector: row => row.quality, sortable: true },
      { name: 'Hours', selector: row => row.hours, sortable: true },
      { name: 'Percent', selector: row => `${row.percent}%`, sortable: true },
   { name: 'Due Date', selector: row => row.dt_due ? new Date(row.dt_due).toLocaleString() : '-', sortable: true },
   { name: 'Completed On', selector: row => row.dt_completed ? new Date(row.dt_completed).toLocaleString() : '-', sortable: true },
   { name: 'Last Updated', selector: row => row.dt_updated ? new Date(row.dt_updated).toLocaleString() : '-', sortable: true },
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
      <PageBreadcrumb pageTitle="Action Management" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-2" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button 
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600"
              >
                <FaPlus />
                Add Action
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
          <div className="lg:col-span-1">
            <ActionAdd
              inline
              modeProp={formMode}
              dataProp={selectedContact}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
              columnOptions={columnOptions}
            />
          </div>
        )}
      </div>
    </>
  );
}
