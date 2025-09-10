import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import ComponentCard from "../../components/common/ComponentCard";
import DataTable, { TableColumn } from 'react-data-table-component';
import { createTheme } from 'react-data-table-component';
import { useEffect, useState } from "react";
import { Contacts, deleteAction, Domains } from "../../api/userProfile";
import { dynamicData } from "../../model/dynamicData";
import { FaEye, FaEdit, FaTrash, FaPlus } from 'react-icons/fa'; 
import { showToast } from "../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useTheme } from "../../context/ThemeContext";
import ContactAdd from "./DomainAdd";
import DomainAdd from "./DomainAdd";

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

export default function DomainList() {
  const { theme } = useTheme();
  const [data, setData] = useState<dynamicData[]>([]);
  const [selectedContact, setSelectedContact] = useState<dynamicData | null>(null);
  const [formMode, setFormMode] = useState<'add' | 'edit' | 'view' | null>(null);
  
  const dispatch = useDispatch();

  const getDomainData = async () => {
    try {
      const res = await Domains();
      if (res.status === 200) {
        setData(res.data.data.results);
      }
    } catch (error) {
      console.error("Failed to fetch domains", error);
    }
  };

  useEffect(() => {
    getDomainData();
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
        dispatch(showToast({ message: "Domain deleted successfully", type: "success" }));
        getDomainData(); // Refresh data
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
    getDomainData();
    setFormMode(null);
    setSelectedContact(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedContact(null);
  };

  const userColumns: TableColumn<dynamicData>[] = [
    { id: 'health_rating', name: 'Health Rating', selector: (row) => row.health_rating, sortable: true },
    { id: 'path', name: 'Path', selector: (row) => row.path, sortable: true },
    { id: 'type', name: 'Type', selector: (row) => row.type, sortable: true },
    { id: 'comment', name: 'Comment', selector: (row) => row.comment, sortable: true },
    { id: 'status', name: 'Status', selector: (row) => row.status, sortable: true },
    { id: 'security_level', name: 'Security Level', selector: (row) => row.security_level, sortable: true },
    { id: 'sequence', name: 'Sequence', selector: (row) => row.sequence, sortable: true },
    { id: 'count_accessed', name: 'Count Accessed', selector: (row) => row.count_accessed, sortable: true },
    {
      id: 'action',
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
      <PageBreadcrumb pageTitle="Domain Management" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-2" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button 
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600"
              >
                <FaPlus />
                Add Domain
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
            <DomainAdd
              inline
              modeProp={formMode}
              dataProp={selectedContact}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
