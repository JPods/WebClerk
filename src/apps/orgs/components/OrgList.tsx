/**
 * OrgList - Base organization list component
 * Provides a reusable DataTable for all org types
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { TableColumn } from 'react-data-table-component';
import { FaEye, FaEdit, FaTrash, FaPlus, FaCheck, FaTimes, FaSearch } from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import AdvancedDataTable from '@/components/common/AdvancedDataTable';
import { showToast } from '@/store/slices/toastSlice';
import PageBreadcrumb from '@/components/common/PageBreadCrumb';
import ComponentCard from '@/components/common/ComponentCard';
import type { Organization, OrgType, OrgListParams } from '../types/orgTypes';
import orgApi from '../services/orgApi';

// --- Props Interface ---
export interface OrgListProps {
  orgType: OrgType;
  title: string;
  detailPath?: string; // e.g., '/org/employee'
  additionalColumns?: TableColumn<Organization>[];
  onRowClick?: (row: Organization) => void;
  showInlineDetail?: boolean;
  DetailComponent?: React.ComponentType<{ org: Organization; mode: 'view' | 'edit' | 'add'; onClose: () => void; onSaved: () => void }>;
}

// --- Component ---
const OrgList: React.FC<OrgListProps> = ({
  orgType,
  title,
  detailPath,
  additionalColumns = [],
  onRowClick,
  showInlineDetail = true,
  DetailComponent,
}) => {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  // State
  const [data, setData] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
  const [formMode, setFormMode] = useState<'view' | 'edit' | 'add' | null>(null);
  const [totalRows, setTotalRows] = useState(0);
  const [perPage, setPerPage] = useState(25);
  const [currentPage, setCurrentPage] = useState(1);

  // Fetch data
  const fetchData = useCallback(async (params: OrgListParams = {}) => {
    setLoading(true);
    try {
      const response = await orgApi.list({
        org_type: orgType,
        limit: perPage,
        offset: (currentPage - 1) * perPage,
        search: searchTerm || undefined,
        ...params,
      });
      setData(response.results || []);
      setTotalRows(response.total || response.count || 0);
    } catch (error) {
      console.error('Failed to fetch organizations:', error);
      dispatch(showToast({ message: `Failed to load ${title}`, type: 'error' }));
    } finally {
      setLoading(false);
    }
  }, [orgType, perPage, currentPage, searchTerm, dispatch, title]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Filtered data (client-side search fallback)
  const filteredData = useMemo(() => {
    if (!searchTerm) return data;
    const term = searchTerm.toLowerCase();
    return data.filter(org => 
      org.display_name?.toLowerCase().includes(term) ||
      org.status?.toLowerCase().includes(term)
    );
  }, [data, searchTerm]);

  // Handlers
  const handleView = (row: Organization) => {
    if (onRowClick) {
      onRowClick(row);
    } else if (showInlineDetail && DetailComponent) {
      setSelectedOrg(row);
      setFormMode('view');
    } else if (detailPath) {
      navigate(`${detailPath}/${row.id}`);
    }
  };

  const handleEdit = async (row: Organization) => {
    try {
      const fullOrg = await orgApi.get(row.id, orgType);
      if (showInlineDetail && DetailComponent) {
        setSelectedOrg(fullOrg);
        setFormMode('edit');
      } else if (detailPath) {
        navigate(`${detailPath}/${row.id}?mode=edit`);
      }
    } catch {
      setSelectedOrg(row);
      setFormMode('edit');
    }
  };

  const handleAdd = () => {
    setSelectedOrg(null);
    setFormMode('add');
  };

  const handleDelete = async (row: Organization) => {
    if (!window.confirm(`Delete ${row.display_name}? This action cannot be undone.`)) {
      return;
    }
    try {
      await orgApi.delete(row.id, orgType);
      dispatch(showToast({ message: `${row.display_name} deleted successfully`, type: 'success' }));
      fetchData();
      if (selectedOrg?.id === row.id) {
        setSelectedOrg(null);
        setFormMode(null);
      }
    } catch (error) {
      dispatch(showToast({ message: 'Failed to delete record', type: 'error' }));
    }
  };

  const handleCloseDetail = () => {
    setSelectedOrg(null);
    setFormMode(null);
  };

  const handleSaved = () => {
    fetchData();
    handleCloseDetail();
  };

  // Table columns
  const baseColumns: TableColumn<Organization>[] = [
    {
      name: 'ID',
      selector: (row: Organization) => row.id,
      sortable: true,
      width: '80px',
    },
    {
      name: 'Name',
      selector: (row: Organization) => row.display_name,
      sortable: true,
      grow: 2,
      cell: (row: Organization) => (
        <span className="font-medium text-slate-900 dark:text-white">
          {row.display_name || '(Unnamed)'}
        </span>
      ),
    },
    {
      name: 'Status',
      selector: (row: Organization) => row.status || '',
      sortable: true,
      width: '120px',
      cell: (row: Organization) => (
        <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
          row.status === 'active' 
            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
            : row.status === 'prospect'
            ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
            : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
        }`}>
          {row.status || 'N/A'}
        </span>
      ),
    },
    {
      name: 'Active',
      selector: (row: Organization) => row.is_active,
      sortable: true,
      width: '90px',
      cell: (row: Organization) => (
        row.is_active 
          ? <FaCheck className="text-green-500" />
          : <FaTimes className="text-red-400" />
      ),
    },
    {
      name: 'Contacts',
      selector: (row: Organization) => row.contacts?.length || 0,
      sortable: true,
      width: '100px',
      cell: (row: Organization) => (
        <span className="text-slate-600 dark:text-slate-300">
          {row.contacts?.length || 0}
        </span>
      ),
    },
    {
      name: 'Locations',
      selector: (row: Organization) => row.locations?.length || 0,
      sortable: true,
      width: '100px',
      cell: (row: Organization) => (
        <span className="text-slate-600 dark:text-slate-300">
          {row.locations?.length || 0}
        </span>
      ),
    },
  ];

  const actionColumn: TableColumn<Organization> = {
    name: 'Actions',
    width: '140px',
    cell: (row: Organization) => (
      <div className="flex items-center gap-2">
        <button
          onClick={() => handleView(row)}
          className="rounded p-1.5 text-blue-600 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/20"
          title="View"
        >
          <FaEye size={14} />
        </button>
        <button
          onClick={() => handleEdit(row)}
          className="rounded p-1.5 text-amber-600 hover:bg-amber-50 dark:text-amber-400 dark:hover:bg-amber-900/20"
          title="Edit"
        >
          <FaEdit size={14} />
        </button>
        <button
          onClick={() => handleDelete(row)}
          className="rounded p-1.5 text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
          title="Delete"
        >
          <FaTrash size={14} />
        </button>
      </div>
    ),
  };

  const columns = [...baseColumns, ...additionalColumns, actionColumn];

  return (
    <div className="flex flex-col gap-6 lg:flex-row">
      {/* Main List */}
      <div className={`flex-1 ${showInlineDetail && formMode ? 'lg:w-1/2' : 'w-full'}`}>
        <PageBreadcrumb pageTitle={title} />
        
        <ComponentCard title={title}>
          {/* Toolbar */}
          <div className="mb-4 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            {/* Search */}
            <div className="relative flex-1 sm:max-w-xs">
              <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
              <input
                type="text"
                placeholder={`Search ${title.toLowerCase()}...`}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-4 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              />
            </div>
            
            {/* Add Button */}
            <button
              onClick={handleAdd}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              <FaPlus size={12} />
              Add {title.replace(/s$/, '')}
            </button>
          </div>

          {/* Table */}
          <AdvancedDataTable
            columns={columns}
            data={filteredData}
            loading={loading}
            storageKey="org_list"
            onRowActivate={handleView}
          />
        </ComponentCard>
      </div>

      {/* Inline Detail Panel */}
      {showInlineDetail && formMode && DetailComponent && (
        <div className="w-full lg:w-1/2">
          <DetailComponent
            org={selectedOrg!}
            mode={formMode}
            onClose={handleCloseDetail}
            onSaved={handleSaved}
          />
        </div>
      )}
    </div>
  );
};

export default OrgList;
