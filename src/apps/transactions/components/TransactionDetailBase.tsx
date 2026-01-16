/**
 * TransactionDetail - Base component for all transaction detail pages
 * Provides common tabbed layout with standard sections
 * Extended by InvoiceDetail, OrderDetail, etc.
 */
import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  FaArrowLeft, 
  FaEdit, 
  FaSave, 
  FaTimes,
  FaFileInvoice,
  FaBoxes,
  FaAddressCard,
  FaComments,
  FaDollarSign,
  FaLink,
  FaCog,
  FaHistory,
  FaEllipsisH
} from 'react-icons/fa';
import { PageHeader } from '../../../components/ui/PageHeader';

// Import shared components
import RefsLinksContactPanel from './RefsLinksContactPanel';
import RefsLinksTable from './RefsLinksTable';
import CommentsPanel from './CommentsPanel';
import ActionsCard from './ActionsCard';
import MetadataPanel from './MetadataPanel';
import FinancialsCard from './FinancialsCard';
import FlowDiagram from './FlowDiagram';
import JsonFieldEditor from './JsonFieldEditor';
import JsonEnvelopesPanel from './JsonEnvelopesPanel';

// Import types
import type { 
  Transaction, 
  TransactionLine,
  TransactionRefs,
  TransactionMetadata,
  TransactionComments,
  TransactionActions,
  TransactionTotals,
  TransactionCost,
  TransactionSell,
  TransactionFlow,
  TransactionSource,
  TransactionFinance,
  TransactionPrefs,
} from '../types/transactionTypes';

// Tab definition
export interface TransactionTab {
  id: string;
  label: string;
  icon: React.ReactNode;
  badge?: string | number;
  adminOnly?: boolean;
}

// Props for the base component
interface TransactionDetailBaseProps {
  /** Transaction type (invoice, order, etc.) */
  transactionType: string;
  
  /** Display label for the transaction type */
  typeLabel: string;
  
  /** API model name for fetching */
  modelName: string;
  
  /** Custom tabs to add before standard tabs */
  customTabsBefore?: TransactionTab[];
  
  /** Custom tabs to add after standard tabs */
  customTabsAfter?: TransactionTab[];
  
  /** Render function for custom tab content */
  renderCustomTab?: (tabId: string, data: Transaction, isEditing: boolean) => React.ReactNode;
  
  /** Render function for the header section */
  renderHeader?: (data: Transaction, isEditing: boolean) => React.ReactNode;
  
  /** Render function for lines section (if not using default) */
  renderLines?: (lines: TransactionLine[], isEditing: boolean) => React.ReactNode;
  
  /** Whether user is admin (affects visible tabs/fields) */
  isAdmin?: boolean;
  
  /** Whether the transaction is editable in current state */
  canEdit?: (data: Transaction) => boolean;
  
  /** Custom fetch function if not using standard API */
  fetchData?: (id: string) => Promise<Transaction>;
  
  /** Custom save function if not using standard API */
  saveData?: (data: Transaction) => Promise<Transaction>;
}

const TransactionDetailBase: React.FC<TransactionDetailBaseProps> = ({
  transactionType,
  typeLabel,
  modelName,
  customTabsBefore = [],
  customTabsAfter = [],
  renderCustomTab,
  renderHeader,
  renderLines,
  isAdmin = false,
  canEdit = () => true,
  fetchData,
  saveData,
}) => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  // State
  const [data, setData] = useState<Transaction | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState<Transaction | null>(null);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('summary');

  // Fetch data
  useEffect(() => {
    const loadData = async () => {
      if (!id) return;
      
      setLoading(true);
      setError(null);
      
      try {
        let result: Transaction;
        
        if (fetchData) {
          result = await fetchData(id);
        } else {
          // Default fetch using standard API
          const response = await fetch(
            `/wcapi/get/?model_name=${modelName}&id=${id}`
          );
          if (!response.ok) {
            const text = await response.text();
            if (text.startsWith('<!DOCTYPE') || text.startsWith('<html')) {
              throw new Error(`Server returned HTML error page (${response.status}). Check if the backend is running.`);
            }
            throw new Error(`Failed to fetch ${typeLabel}: ${response.status}`);
          }
          const text = await response.text();
          if (text.startsWith('<!DOCTYPE') || text.startsWith('<html')) {
            throw new Error('Server returned HTML instead of JSON. Check backend API.');
          }
          const json = JSON.parse(text);
          result = json.data ?? json;
        }
        
        setData(result);
        setEditData(result);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load data');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [id, modelName, typeLabel, fetchData]);

  // Build tabs list - use stable reference for badge count
  const contactCount = data?.refs?.links?.contact?.length ?? 0;
  const tabs = useMemo(() => {
    const defaultTabs: TransactionTab[] = [
      { id: 'summary', label: 'Summary', icon: <FaFileInvoice size={14} /> },
      { id: 'lines', label: 'Lines', icon: <FaBoxes size={14} /> },
      { id: 'contacts', label: 'Contacts', icon: <FaAddressCard size={14} />, badge: contactCount || undefined },
      { id: 'comments', label: 'Comments', icon: <FaComments size={14} /> },
      { id: 'financials', label: 'Financials', icon: <FaDollarSign size={14} /> },
      { id: 'flow', label: 'Flow', icon: <FaLink size={14} /> },
    ];

    if (isAdmin) {
      defaultTabs.push(
        { id: 'metadata', label: 'Metadata', icon: <FaCog size={14} />, adminOnly: true },
        { id: 'refs', label: 'Refs', icon: <FaHistory size={14} />, adminOnly: true },
        { id: 'raw', label: 'Raw JSON', icon: <FaEllipsisH size={14} />, adminOnly: true }
      );
    }

    return [
      ...customTabsBefore,
      ...defaultTabs,
      ...customTabsAfter,
    ];
  }, [customTabsBefore, customTabsAfter, contactCount, isAdmin]);

  // Handle edit mode
  const handleEdit = () => {
    if (data && canEdit(data)) {
      setEditData({ ...data });
      setIsEditing(true);
    }
  };

  const handleCancel = () => {
    setEditData(data);
    setIsEditing(false);
  };

  const handleSave = async () => {
    if (!editData) return;
    
    setSaving(true);
    try {
      let result: Transaction;
      
      if (saveData) {
        result = await saveData(editData);
      } else {
        // Default save using standard API
        const response = await fetch(`/wcapi/save/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model_name: modelName,
            data: editData,
          }),
        });
        if (!response.ok) throw new Error(`Failed to save ${typeLabel}`);
        const json = await response.json();
        result = json.data ?? json;
      }
      
      setData(result);
      setEditData(result);
      setIsEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  // Handle field changes during edit
  const handleFieldChange = (field: keyof Transaction, value: unknown) => {
    if (editData) {
      setEditData({ ...editData, [field]: value });
    }
  };

  // Render loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  // Render error state
  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-red-500">
        <p className="text-lg font-medium">Error loading {typeLabel}</p>
        <p className="text-sm">{error ?? 'Not found'}</p>
        <button
          onClick={() => navigate(-1)}
          className="mt-4 px-4 py-2 text-sm text-blue-500 hover:underline"
        >
          Go Back
        </button>
      </div>
    );
  }

  const currentData = isEditing ? editData! : data;

  // Render tab content
  const renderTabContent = () => {
    // Check for custom tab first
    if (renderCustomTab) {
      const customContent = renderCustomTab(activeTab, currentData, isEditing);
      if (customContent) return customContent;
    }

    switch (activeTab) {
      case 'summary':
        return (
          <>
            {renderHeader ? renderHeader(currentData, isEditing) : (
              <DefaultSummary data={currentData} isEditing={isEditing} onChange={handleFieldChange} />
            )}
            {/* Admin/Developer JSON Envelopes Panel - shows on summary tab */}
            <JsonEnvelopesPanel
              data={currentData as unknown as Record<string, unknown>}
              isVisible={isAdmin}
              isEditing={isEditing}
            />
          </>
        );

      case 'lines':
        return renderLines ? renderLines(currentData.lines ?? [], isEditing) : (
          <DefaultLines lines={currentData.lines ?? []} isEditing={isEditing} />
        );

      case 'contacts':
        return (
          <RefsLinksContactPanel
            contacts={currentData.refs?.links?.contact ?? []}
            isEditing={isEditing}
          />
        );

      case 'comments':
        return (
          <CommentsPanel
            comments={currentData.comments ?? {}}
            isEditing={isEditing}
            onChange={(val) => handleFieldChange('comments', val)}
          />
        );

      case 'financials':
        return (
          <FinancialsCard
            totals={currentData.totals}
            cost={currentData.cost}
            sell={currentData.sell}
            currency={currentData.currency}
            isEditing={isEditing}
          />
        );

      case 'flow':
        return (
          <FlowDiagram
            flow={currentData.flow}
            source={currentData.source}
            currentId={currentData.id}
            currentType={transactionType}
            currentNumber={currentData.number}
          />
        );

      case 'metadata':
        return isAdmin ? (
          <MetadataPanel
            metadata={currentData.metadata}
            isEditing={isEditing}
            onChange={(val) => handleFieldChange('metadata', val)}
          />
        ) : null;

      case 'refs':
        return isAdmin ? (
          <div className="space-y-6">
            <JsonFieldEditor
              label="refs"
              value={currentData.refs ?? {}}
              readonly={!isEditing}
              onChange={(val) => handleFieldChange('refs', val)}
            />
          </div>
        ) : null;

      case 'raw':
        return isAdmin ? (
          <JsonFieldEditor
            label="Full Transaction JSON"
            value={currentData}
            readonly
            defaultExpanded
            maxHeight="600px"
          />
        ) : null;

      default:
        return <div className="text-slate-400 text-center py-8">Tab not found: {activeTab}</div>;
    }
  };

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
          >
            <FaArrowLeft />
          </button>
          <PageHeader
            title={`${typeLabel} ${currentData.number ?? `#${currentData.id}`}`}
            breadcrumbs={[
              { label: 'Transactions', href: '/transactions' },
              { label: typeLabel + 's', href: `/transactions/${transactionType}s` },
              { label: currentData.number ?? `#${currentData.id}` },
            ]}
          />
        </div>

        <div className="flex items-center gap-2">
          {isEditing ? (
            <>
              <button
                onClick={handleCancel}
                disabled={saving}
                className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors flex items-center gap-2"
              >
                <FaTimes size={14} />
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                <FaSave size={14} />
                {saving ? 'Saving...' : 'Save'}
              </button>
            </>
          ) : (
            canEdit(data) && (
              <button
                onClick={handleEdit}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors flex items-center gap-2"
              >
                <FaEdit size={14} />
                Edit
              </button>
            )
          )}
        </div>
      </div>

      {/* Status/Action Banner */}
      {currentData.action && (
        <div className="mb-6">
          <ActionsCard
            action={currentData.action}
            isEditing={isEditing}
            onChange={(val) => handleFieldChange('action', val)}
          />
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-slate-200 dark:border-slate-700 mb-6">
        <nav className="flex gap-1 overflow-x-auto">
          {tabs
            .filter(tab => !tab.adminOnly || isAdmin)
            .map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap
                  ${activeTab === tab.id
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 hover:border-slate-300 dark:hover:border-slate-600'
                  }
                `}
              >
                {tab.icon}
                {tab.label}
                {tab.badge !== undefined && tab.badge > 0 && (
                  <span className="px-1.5 py-0.5 text-xs bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-full">
                    {tab.badge}
                  </span>
                )}
              </button>
            ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="pb-8">
        {renderTabContent()}
      </div>
    </div>
  );
};

// Default Summary Component
const DefaultSummary: React.FC<{
  data: Transaction;
  isEditing: boolean;
  onChange: (field: keyof Transaction, value: unknown) => void;
}> = ({ data, isEditing, onChange }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
        <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Basic Info</h3>
        <dl className="space-y-3">
          <div className="flex justify-between">
            <dt className="text-slate-500 dark:text-slate-400">Number</dt>
            <dd className="font-medium text-slate-900 dark:text-white">{data.number ?? '--'}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-slate-500 dark:text-slate-400">Date</dt>
            <dd className="font-medium text-slate-900 dark:text-white">
              {data.dt ? new Date(data.dt).toLocaleDateString() : '--'}
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-slate-500 dark:text-slate-400">Status</dt>
            <dd className="font-medium text-slate-900 dark:text-white">{data.status ?? '--'}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-slate-500 dark:text-slate-400">Reference</dt>
            <dd className="font-medium text-slate-900 dark:text-white">{data.reference ?? '--'}</dd>
          </div>
        </dl>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
        <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Parties</h3>
        <dl className="space-y-3">
          <div className="flex justify-between">
            <dt className="text-slate-500 dark:text-slate-400">Customer</dt>
            <dd className="font-medium text-slate-900 dark:text-white">
              {data.refs?.links?.customer?.[0]?.name ?? data.customer_id ?? '--'}
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-slate-500 dark:text-slate-400">Vendor</dt>
            <dd className="font-medium text-slate-900 dark:text-white">
              {data.refs?.links?.vendor?.[0]?.name ?? data.vendor_id ?? '--'}
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-slate-500 dark:text-slate-400">Manufacturer</dt>
            <dd className="font-medium text-slate-900 dark:text-white">
              {data.refs?.links?.manufacturer?.[0]?.name ?? data.manufacturer_id ?? '--'}
            </dd>
          </div>
        </dl>
      </div>
    </div>
  );
};

// Default Lines Component
const DefaultLines: React.FC<{
  lines: TransactionLine[];
  isEditing: boolean;
}> = ({ lines, isEditing }) => {
  if (!lines.length) {
    return (
      <div className="text-center py-12 text-slate-400">
        <FaBoxes size={32} className="mx-auto mb-3 opacity-50" />
        <p>No line items</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="bg-slate-50 dark:bg-slate-900/50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">#</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Item</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Description</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Qty</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Price</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Total</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
          {lines.map((line, idx) => (
            <tr key={line.id ?? idx} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
              <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">{line.line_no ?? idx + 1}</td>
              <td className="px-4 py-3 text-sm font-medium text-slate-900 dark:text-white">
                {line.item_code ?? '--'}
              </td>
              <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300">
                {line.description ?? '--'}
              </td>
              <td className="px-4 py-3 text-sm text-right text-slate-900 dark:text-white">
                {line.qty ?? '--'}
              </td>
              <td className="px-4 py-3 text-sm text-right text-slate-900 dark:text-white">
                {line.price != null ? `$${line.price.toFixed(2)}` : '--'}
              </td>
              <td className="px-4 py-3 text-sm text-right font-medium text-slate-900 dark:text-white">
                {line.total != null ? `$${line.total.toFixed(2)}` : '--'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default TransactionDetailBase;
