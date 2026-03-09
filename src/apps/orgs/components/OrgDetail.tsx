/**
 * OrgDetail - Base organization detail/edit component
 * Provides a reusable tabbed interface for viewing/editing org aspects
 * ADMIN ONLY - Full access to all scalar fields and JSON objects
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { FaSave, FaTimes, FaEdit, FaChevronLeft, FaPlus, FaTrash, FaUser, FaMapMarkerAlt, FaPhone, FaEnvelope, FaFileAlt, FaDatabase, FaChartBar, FaDollarSign, FaLink, FaCog, FaListAlt, FaQuestionCircle, FaSlidersH } from 'react-icons/fa';
import { showToast } from '@/store/slices/toastSlice';
import DetailShell from '@/components/common/DetailShell';
import ComponentCard from '@/components/common/ComponentCard';
import SimpleDetailHeader from '@/components/common/SimpleDetailHeader';
import SimpleDetailToolbar from '@/components/common/SimpleDetailToolbar';
import OrgFinancialsPanel from './OrgFinancialsPanel';
import type { Organization, OrgType, OrgStatus, OrgRelations, OrgFinancial, OrgMetrics } from '../types/orgTypes';
import orgApi from '../services/orgApi';
import { QAPanel } from '@/apps/common/components/panels';
import { ScalarCard, JsonCard, BaseModelCards } from '@/apps/common/components/detail';
import TransactionTabs from '@/components/common/TransactionTabs';
import ItemTabs from '@/components/common/ItemTabs';
import { withDevIdentifier } from '@/components/common/DevIdentifier';
import InternationalPhoneInput from '@/components/form/input/InternationalPhoneInput';

// --- Types ---
type AspectKey = 'contacts' | 'addresses' | 'phones' | 'emails' | 'docs' | 'domains' | 'connections' | 'data' | 'financial' | 'gl_accounts' | 'metrics' | 'qa' | 'relations' | 'refs' | 'prefs' | 'metadata';

interface TabConfig {
  key: AspectKey | 'info';
  label: string;
  icon: React.ReactNode;
}

export interface OrgDetailProps {
  orgType: OrgType;
  title: string;
  listPath?: string;
  additionalTabs?: TabConfig[];
  // Inline mode props (when used within OrgList)
  org?: Organization | null;
  mode?: 'view' | 'edit' | 'add';
  onClose?: () => void;
  onSaved?: () => void;
}

// --- Basic Information Panel (PERSISTENT above tabs) ---
const BasicInformationPanel: React.FC<{
  org: Organization;
  editing: boolean;
  onChange: (updates: Partial<Organization>) => void;
  columnCount?: 2 | 3;
}> = ({ org, editing, onChange, columnCount = 3 }) => {
  const gridCols = columnCount === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-2';
  
  return (
    <div className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 px-4 py-4">
      <div className={`grid grid-cols-1 md:grid-cols-2 ${gridCols} gap-4`}>
        {/* Display Name */}
        <div className="flex items-center gap-2">
          <span className="w-24 text-xs font-medium text-slate-500 dark:text-slate-400 shrink-0">Name</span>
          {editing ? (
            <input
              type="text"
              value={org.display_name || ''}
              onChange={(e) => onChange({ display_name: e.target.value })}
              className="flex-1 rounded border border-slate-300 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              placeholder="Display Name *"
            />
          ) : (
            <span className="text-sm font-medium text-slate-900 dark:text-white">{org.display_name || '—'}</span>
          )}
        </div>
        {/* Display ID */}
        <div className="flex items-center gap-2">
          <span className="w-24 text-xs font-medium text-slate-500 dark:text-slate-400 shrink-0">ID Code</span>
          {editing ? (
            <input
              type="text"
              value={org.display_id || ''}
              onChange={(e) => onChange({ display_id: e.target.value })}
              className="flex-1 rounded border border-slate-300 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              placeholder="Display ID"
            />
          ) : (
            <span className="text-sm text-slate-700 dark:text-slate-300">{org.display_id || '—'}</span>
          )}
        </div>
        {/* Company */}
        <div className="flex items-center gap-2">
          <span className="w-24 text-xs font-medium text-slate-500 dark:text-slate-400 shrink-0">Company</span>
          {editing ? (
            <input
              type="text"
              value={org.company || ''}
              onChange={(e) => onChange({ company: e.target.value })}
              className="flex-1 rounded border border-slate-300 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              placeholder="Company"
            />
          ) : (
            <span className="text-sm text-slate-700 dark:text-slate-300">{org.company || '—'}</span>
          )}
        </div>
        {/* Email */}
        <div className="flex items-center gap-2">
          <span className="w-24 text-xs font-medium text-slate-500 dark:text-slate-400 shrink-0">Email</span>
          {editing ? (
            <input
              type="email"
              value={org.email || ''}
              onChange={(e) => onChange({ email: e.target.value || null })}
              className="flex-1 rounded border border-slate-300 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              placeholder="Primary Email"
            />
          ) : (
            <span className="text-sm text-slate-700 dark:text-slate-300">{org.email || '—'}</span>
          )}
        </div>
        {/* Phone */}
        <div className="flex items-center gap-2">
          <span className="w-24 text-xs font-medium text-slate-500 dark:text-slate-400 shrink-0">Phone</span>
          {editing ? (
            <InternationalPhoneInput
              value={org.phone || ''}
              onChange={(value) => onChange({ phone: value || null })}
              placeholder="Primary Phone"
              className="flex-1"
            />
          ) : (
            <span className="text-sm text-slate-700 dark:text-slate-300">{org.phone || '—'}</span>
          )}
        </div>
        {/* Status & Active */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Status</span>
            {editing ? (
              <select
                value={org.status || 'lead'}
                onChange={(e) => onChange({ status: e.target.value as OrgStatus })}
                className="rounded border border-slate-300 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              >
                <option value="lead">Lead</option>
                <option value="prospect">Prospect</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="suspended">Suspended</option>
              </select>
            ) : (
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                org.status === 'active' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' :
                org.status === 'inactive' ? 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400' :
                'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
              }`}>
                {org.status || 'lead'}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {editing ? (
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={org.is_active ?? false}
                  onChange={(e) => onChange({ is_active: e.target.checked })}
                  className="rounded border-slate-300 text-blue-600"
                />
                <span className="text-xs text-slate-600 dark:text-slate-400">Active</span>
              </label>
            ) : (
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                org.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' : 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400'
              }`}>
                {org.is_active ? 'Active' : 'Inactive'}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// --- Tab Content Components ---

// Info Tab - All scalar fields in alphabetical order (Admin view)
const InfoTab: React.FC<{ org: Organization; editing: boolean; onChange: (updates: Partial<Organization>) => void }> = ({ org, editing, onChange }) => (
  <div className="space-y-6">
    {/* Primary Fields */}
    <div>
      <h4 className="mb-3 text-sm font-semibold text-slate-800 dark:text-slate-200">Primary Fields</h4>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* company */}
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">Company</label>
          <input
            type="text"
            value={org.company || ''}
            onChange={(e) => onChange({ company: e.target.value })}
            disabled={!editing}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-700"
          />
        </div>
        {/* attention */}
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">Attention</label>
          <input
            type="text"
            value={org.attention || ''}
            onChange={(e) => onChange({ attention: e.target.value })}
            disabled={!editing}
            placeholder="Attn: line for mailing"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-700"
          />
        </div>
        {/* contact_id */}
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">Contact ID</label>
          <input
            type="number"
            value={org.contact_id ?? ''}
            onChange={(e) => onChange({ contact_id: e.target.value ? parseInt(e.target.value, 10) : null })}
            disabled={!editing}
            placeholder="Primary contact ID"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-700"
          />
        </div>
        {/* display_id */}
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">Display ID</label>
          <input
            type="text"
            value={org.display_id || ''}
            onChange={(e) => onChange({ display_id: e.target.value })}
            disabled={!editing}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-700"
          />
        </div>
        {/* display_name */}
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">Display Name *</label>
          <input
            type="text"
            value={org.display_name || ''}
            onChange={(e) => onChange({ display_name: e.target.value })}
            disabled={!editing}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-700"
          />
        </div>
        {/* email (primary) */}
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">Email</label>
          <input
            type="email"
            value={org.email || ''}
            onChange={(e) => onChange({ email: e.target.value || null })}
            disabled={!editing}
            placeholder="Primary email"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-700"
          />
        </div>
        {/* id (read-only) */}
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">ID</label>
          <input
            type="text"
            value={org.id || ''}
            disabled
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm bg-slate-100 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-400"
          />
        </div>
        {/* is_active */}
        <div className="flex items-end gap-2 pb-2">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={org.is_active ?? true}
              onChange={(e) => onChange({ is_active: e.target.checked })}
              disabled={!editing}
              className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-slate-700 dark:text-slate-300">Is Active</span>
          </label>
        </div>
        {/* org_type */}
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">Org Type</label>
          <select
            value={org.org_type || ''}
            onChange={(e) => onChange({ org_type: e.target.value as OrgType })}
            disabled={!editing}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-700"
          >
            <option value="customer">Customer</option>
            <option value="vendor">Vendor</option>
            <option value="rep">Rep</option>
            <option value="employee">Employee</option>
            <option value="manufacturer">Manufacturer</option>
            <option value="other">Other</option>
          </select>
        </div>
        {/* phone (primary) */}
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">Phone</label>
          <InternationalPhoneInput
            value={org.phone || ''}
            onChange={(value) => onChange({ phone: value || null })}
            disabled={!editing}
            placeholder="Primary phone"
            className="mt-1"
          />
        </div>
        {/* price_level */}
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">Price Level</label>
          <input
            type="text"
            value={org.price_level || ''}
            onChange={(e) => onChange({ price_level: e.target.value || null })}
            disabled={!editing}
            placeholder="e.g. retail, wholesale"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-700"
          />
        </div>
        {/* status */}
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">Status</label>
          <select
            value={org.status || 'active'}
            onChange={(e) => onChange({ status: e.target.value as OrgStatus })}
            disabled={!editing}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-700"
          >
            <option value="active">Active</option>
            <option value="prospect">Prospect</option>
            <option value="inactive">Inactive</option>
            <option value="retired">Retired</option>
          </select>
        </div>
        {/* uuid (read-only) */}
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">UUID</label>
          <input
            type="text"
            value={org.uuid || ''}
            disabled
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 bg-slate-100 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-400 font-mono text-xs"
          />
        </div>
        {/* version (read-only) */}
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">Version</label>
          <input
            type="text"
            value={org.version || 1}
            disabled
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm bg-slate-100 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-400"
          />
        </div>
      </div>
    </div>

    {/* Notes Field */}
    <div>
      <h4 className="mb-3 text-sm font-semibold text-slate-800 dark:text-slate-200">Notes</h4>
      <textarea
        value={org.notes || ''}
        onChange={(e) => onChange({ notes: e.target.value })}
        disabled={!editing}
        rows={4}
        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-700"
        placeholder="Optional notes..."
      />
    </div>

    {/* Timestamps (read-only) */}
    <div>
      <h4 className="mb-3 text-sm font-semibold text-slate-800 dark:text-slate-200">Timestamps</h4>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">Created At</label>
          <input
            type="text"
            value={org.created_at || org.dt_created || ''}
            disabled
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 bg-slate-100 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-400 text-xs"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">Updated At</label>
          <input
            type="text"
            value={org.updated_at || org.dt_modified || ''}
            disabled
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 bg-slate-100 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-400 text-xs"
          />
        </div>
      </div>
    </div>
  </div>
);

// Generic aspect list editor - simplified for basic array data
const AspectListTab: React.FC<{
  items: unknown[];
  editing: boolean;
  onChange: (items: unknown[]) => void;
  fields: Array<{ key: string; label: string; type?: 'text' | 'checkbox' | 'select'; options?: string[] }>;
  maxItems: number;
}> = ({ items = [], editing, onChange, fields, maxItems }) => {
  const itemArray = Array.isArray(items) ? items : [];
  
  const addItem = () => {
    if (itemArray.length < maxItems) {
      const newItem: Record<string, unknown> = { id: null };
      fields.forEach(f => {
        if (f.key.includes('.')) {
          // Handle nested keys like 'address.line1'
          const [parent, child] = f.key.split('.');
          if (!newItem[parent]) newItem[parent] = {};
          (newItem[parent] as Record<string, unknown>)[child] = f.type === 'checkbox' ? false : '';
        } else {
          newItem[f.key] = f.type === 'checkbox' ? false : '';
        }
      });
      onChange([...itemArray, newItem]);
    }
  };

  const updateItem = (index: number, key: string, value: unknown) => {
    const updated = [...itemArray];
    const current = updated[index] as Record<string, unknown>;
    
    if (key.includes('.')) {
      // Handle nested keys like 'address.line1'
      const [parent, child] = key.split('.');
      const parentObj = (current[parent] || {}) as Record<string, unknown>;
      updated[index] = { ...current, [parent]: { ...parentObj, [child]: value } };
    } else {
      updated[index] = { ...current, [key]: value };
    }
    onChange(updated);
  };

  const removeItem = (index: number) => {
    onChange(itemArray.filter((_, i) => i !== index));
  };

  const getItemValue = (item: unknown, key: string): unknown => {
    if (item && typeof item === 'object') {
      if (key.includes('.')) {
        // Handle nested keys like 'address.line1'
        const [parent, child] = key.split('.');
        const parentObj = (item as Record<string, unknown>)[parent];
        if (parentObj && typeof parentObj === 'object') {
          return (parentObj as Record<string, unknown>)[child];
        }
        return '';
      }
      return (item as Record<string, unknown>)[key];
    }
    return '';
  };

  return (
    <div className="space-y-4">
      {itemArray.map((item, idx) => (
        <div key={idx} className="relative rounded-lg border border-slate-200 p-4 dark:border-slate-700">
          {editing && (
            <button
              onClick={() => removeItem(idx)}
              className="absolute right-2 top-2 text-red-500 hover:text-red-700"
            >
              <FaTrash size={12} />
            </button>
          )}
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {fields.map(field => (
              <div key={field.key}>
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">{field.label}</label>
                {field.type === 'checkbox' ? (
                  <input
                    type="checkbox"
                    checked={!!getItemValue(item, field.key)}
                    onChange={(e) => updateItem(idx, field.key, e.target.checked)}
                    disabled={!editing}
                    className="mt-1 rounded border-slate-300"
                  />
                ) : field.type === 'select' && field.options ? (
                  <select
                    value={String(getItemValue(item, field.key) || '')}
                    onChange={(e) => updateItem(idx, field.key, e.target.value)}
                    disabled={!editing}
                    className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm disabled:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:disabled:bg-slate-700"
                  >
                    {field.options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                  </select>
                ) : (
                  <input
                    type="text"
                    value={String(getItemValue(item, field.key) || '')}
                    onChange={(e) => updateItem(idx, field.key, e.target.value)}
                    disabled={!editing}
                    className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm disabled:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:disabled:bg-slate-700"
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
      {editing && itemArray.length < maxItems && (
        <button
          onClick={addItem}
          className="inline-flex items-center gap-2 rounded-lg border border-dashed border-slate-300 px-4 py-2 text-sm text-slate-600 hover:border-blue-500 hover:text-blue-600 dark:border-slate-600 dark:text-slate-400"
        >
          <FaPlus size={10} /> Add Item ({itemArray.length}/{maxItems})
        </button>
      )}
      {itemArray.length === 0 && !editing && (
        <p className="text-sm text-slate-500 dark:text-slate-400">No items</p>
      )}
    </div>
  );
};

// JSON Object Editor - For editing arbitrary JSON objects (Admin only)
const JsonObjectEditor: React.FC<{
  data: Record<string, unknown> | unknown;
  editing: boolean;
  onChange: (data: Record<string, unknown>) => void;
  label: string;
}> = ({ data, editing, onChange, label }) => {
  const [jsonText, setJsonText] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      setJsonText(JSON.stringify(data || {}, null, 2));
      setError(null);
    } catch {
      setJsonText('{}');
    }
  }, [data]);

  const handleTextChange = (text: string) => {
    setJsonText(text);
    try {
      const parsed = JSON.parse(text);
      setError(null);
      onChange(parsed);
    } catch (e) {
      setError('Invalid JSON');
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300">{label}</h4>
        {error && <span className="text-xs text-red-500">{error}</span>}
      </div>
      <textarea
        value={jsonText}
        onChange={(e) => handleTextChange(e.target.value)}
        disabled={!editing}
        rows={8}
        className={`w-full rounded-lg border px-3 py-2 font-mono text-xs focus:ring-1 disabled:bg-slate-100 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-700 ${
          error ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : 'border-slate-300 focus:border-blue-500 focus:ring-blue-500 dark:border-slate-600'
        }`}
      />
    </div>
  );
};

// Relations Tab - Structured editor for parents/children/linked_ids
const RelationsTab: React.FC<{
  relations: OrgRelations | undefined;
  editing: boolean;
  onChange: (relations: OrgRelations) => void;
}> = ({ relations, editing, onChange }) => {
  const data = relations || { parents: [], children: [], linked_ids: [] };

  const updateArray = (key: keyof OrgRelations, value: string) => {
    const ids = value.split(',').map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n));
    onChange({ ...data, [key]: ids });
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">Parent IDs (comma-separated)</label>
        <input
          type="text"
          value={data.parents?.join(', ') || ''}
          onChange={(e) => updateArray('parents', e.target.value)}
          disabled={!editing}
          placeholder="e.g., 101, 102, 103"
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-700"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">Children IDs (comma-separated)</label>
        <input
          type="text"
          value={data.children?.join(', ') || ''}
          onChange={(e) => updateArray('children', e.target.value)}
          disabled={!editing}
          placeholder="e.g., 201, 202"
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-700"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">Linked IDs (comma-separated)</label>
        <input
          type="text"
          value={data.linked_ids?.join(', ') || ''}
          onChange={(e) => updateArray('linked_ids', e.target.value)}
          disabled={!editing}
          placeholder="e.g., 301, 302"
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-700"
        />
      </div>
    </div>
  );
};

// Metrics Tab - Structured editor for counts and periods
const MetricsTab: React.FC<{
  metrics: OrgMetrics | undefined;
  editing: boolean;
  onChange: (metrics: OrgMetrics) => void;
}> = ({ metrics, editing, onChange }) => {
  const data = metrics || { counts: {}, periods: {} };

  return (
    <div className="space-y-6">
      <JsonObjectEditor
        data={data.counts || {}}
        editing={editing}
        onChange={(counts) => onChange({ ...data, counts: counts as OrgMetrics['counts'] })}
        label="Counts (key-value pairs)"
      />
      <JsonObjectEditor
        data={data.periods || {}}
        editing={editing}
        onChange={(periods) => onChange({ ...data, periods: periods as OrgMetrics['periods'] })}
        label="Periods (nested key-value pairs)"
      />
    </div>
  );
};

// --- Main Component ---
const OrgDetail: React.FC<OrgDetailProps> = ({
  orgType,
  title,
  listPath,
  additionalTabs = [],
  // Inline props
  org: inlineOrg,
  mode: inlineMode,
  onClose,
  onSaved,
}) => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();

  // Determine if in standalone or inline mode
  const isInline = inlineOrg !== undefined || onClose !== undefined;
  const paramMode = searchParams.get('mode') as 'edit' | null;

  // State
  const [org, setOrg] = useState<Organization | null>(isInline ? (inlineOrg ?? null) : null);
  const [loading, setLoading] = useState(!isInline && !!id);
  const [saving, setSaving] = useState(false);
  // Detail pages always open in edit mode — switch to read-only only when needed.
  const [editing, setEditing] = useState(inlineMode === 'edit' || inlineMode === 'add' || paramMode === 'edit' || (!inlineMode && !!id));
  const [activeTab, setActiveTab] = useState<string>('info');

  // Fetch data (standalone mode)
  const fetchOrg = useCallback(async () => {
    if (!id || isInline) return;
    setLoading(true);
    try {
      const data = await orgApi.get(Number(id), orgType);
      setOrg(data);
    } catch (error) {
      dispatch(showToast({ message: 'Failed to load record', type: 'error' }));
      if (listPath) navigate(listPath);
    } finally {
      setLoading(false);
    }
  }, [id, isInline, dispatch, navigate, listPath, orgType]);

  useEffect(() => {
    if (isInline) {
      setOrg(inlineOrg ?? null);
      setEditing(inlineMode === 'edit' || inlineMode === 'add');
    } else {
      fetchOrg();
    }
  }, [fetchOrg, isInline, inlineOrg, inlineMode]);

  // Create empty org for add mode
  useEffect(() => {
    if ((inlineMode === 'add' || (!id && !isInline)) && !org) {
      const emptyOrg: Organization = {
        id: 0,
        uuid: '',
        display_name: '',
        company: '',
        status: 'active',
        is_active: true,
        org_type: orgType,
        contacts: [],
        addresses: [],
        domains: [],
        phones: [],
        emails: [],
        relations: { parents: [], children: [], linked_ids: [] },
        financial: {},
        docs: [],
        connections: {},
        data: {},
        metrics: { counts: {}, periods: {} },
        gl_accounts: {},
        dt_created: new Date().toISOString(),
        dt_modified: new Date().toISOString(),
        version: 1,
      };
      setOrg(emptyOrg);
      setEditing(true);
    }
  }, [inlineMode, id, isInline, org, orgType]);

  // Handlers
  const handleChange = (updates: Partial<Organization>) => {
    if (org) setOrg({ ...org, ...updates });
  };

  const handleSave = async () => {
    if (!org) return;
    if (!org.display_name?.trim()) {
      dispatch(showToast({ message: 'Display name is required', type: 'error' }));
      return;
    }

    setSaving(true);
    try {
      if (org.id && org.id > 0) {
        await orgApi.update({ ...org, id: org.id });
        dispatch(showToast({ message: 'Saved successfully', type: 'success' }));
      } else {
        await orgApi.create({ ...org, org_type: orgType });
        dispatch(showToast({ message: 'Created successfully', type: 'success' }));
      }
      if (onSaved) {
        onSaved();
      } else {
        setEditing(false);
        if (listPath) navigate(listPath);
      }
    } catch (error) {
      dispatch(showToast({ message: 'Failed to save', type: 'error' }));
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (onClose) {
      onClose();
    } else if (listPath) {
      navigate(listPath);
    } else {
      setEditing(false);
      fetchOrg();
    }
  };

  // Tab configuration - Full admin access to all aspects
  const defaultTabs: TabConfig[] = [
    { key: 'addresses', label: 'Addresses', icon: <FaMapMarkerAlt size={14} /> },
    { key: 'connections', label: 'Connections', icon: <FaLink size={14} /> },
    { key: 'contacts', label: 'Contacts', icon: <FaUser size={14} /> },
    { key: 'data', label: 'Data', icon: <FaDatabase size={14} /> },
    { key: 'docs', label: 'Docs', icon: <FaFileAlt size={14} /> },
    { key: 'domains', label: 'Domains', icon: <FaLink size={14} /> },
    { key: 'emails', label: 'Emails', icon: <FaEnvelope size={14} /> },
    { key: 'financial', label: 'Financial', icon: <FaDollarSign size={14} /> },
    { key: 'gl_accounts', label: 'GL Accts', icon: <FaDollarSign size={14} /> },
    { key: 'info', label: 'All Fields', icon: <FaListAlt size={14} /> },
    { key: 'metadata', label: 'Metadata', icon: <FaFileAlt size={14} /> },
    { key: 'metrics', label: 'Metrics', icon: <FaChartBar size={14} /> },
    { key: 'phones', label: 'Phones', icon: <FaPhone size={14} /> },
    { key: 'prefs', label: 'Prefs', icon: <FaSlidersH size={14} /> },
    { key: 'qa', label: 'Q&A', icon: <FaQuestionCircle size={14} /> },
    { key: 'refs', label: 'Refs', icon: <FaLink size={14} /> },
    { key: 'relations', label: 'Relations', icon: <FaLink size={14} /> },
  ];

  const tabs = [...defaultTabs, ...additionalTabs];

  // Field configs for aspect tabs
  const contactFields = [
    { key: 'name', label: 'Name' },
    { key: 'role', label: 'Role' },
    { key: 'title', label: 'Title' },
    { key: 'department', label: 'Department' },
  ];

  const locationFields = [
    { key: 'type', label: 'Type', type: 'select' as const, options: ['Billing', 'Shipping', 'Main', 'Office', 'Warehouse', 'Other'] },
    { key: 'address.line1', label: 'Address Line 1' },
    { key: 'address.line2', label: 'Address Line 2' },
    { key: 'address.city', label: 'City' },
    { key: 'address.state', label: 'State' },
    { key: 'address.postal', label: 'Postal' },
    { key: 'address.country', label: 'Country' },
  ];

  const phoneFields = [
    { key: 'number', label: 'Number' },
    { key: 'type', label: 'Type', type: 'select' as const, options: ['Work', 'Mobile', 'Fax', 'Home', 'Other'] },
    { key: 'primary', label: 'Primary', type: 'checkbox' as const },
  ];

  const emailFields = [
    { key: 'email', label: 'Email' },
    { key: 'type', label: 'Type', type: 'select' as const, options: ['Work', 'Personal', 'Billing', 'Support', 'Other'] },
    { key: 'primary', label: 'Primary', type: 'checkbox' as const },
  ];

  const docFields = [
    { key: 'name', label: 'Name' },
    { key: 'kind', label: 'Type' },
    { key: 'size', label: 'Size (bytes)' },
  ];

  const domainFields = [
    { key: 'domain', label: 'Domain' },
    { key: 'verified', label: 'Verified', type: 'checkbox' as const },
  ];

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  if (!org) return null;

  const renderTabContent = () => {
    switch (activeTab) {
      case 'info':
        return <InfoTab org={org} editing={editing} onChange={handleChange} />;
      case 'contacts':
        return (
          <AspectListTab
            items={org.contacts || []}
            editing={editing}
            onChange={(items) => handleChange({ contacts: items as Organization['contacts'] })}
            fields={contactFields}
            maxItems={15}
          />
        );
      case 'addresses':
        return (
          <AspectListTab
            items={org.addresses || []}
            editing={editing}
            onChange={(items) => handleChange({ addresses: items as Organization['addresses'] })}
            fields={locationFields}
            maxItems={10}
          />
        );
      case 'phones':
        return (
          <AspectListTab
            items={org.phones || []}
            editing={editing}
            onChange={(items) => handleChange({ phones: items as Organization['phones'] })}
            fields={phoneFields}
            maxItems={10}
          />
        );
      case 'emails':
        return (
          <AspectListTab
            items={org.emails || []}
            editing={editing}
            onChange={(items) => handleChange({ emails: items as Organization['emails'] })}
            fields={emailFields}
            maxItems={10}
          />
        );
      case 'docs':
        return (
          <AspectListTab
            items={org.docs || []}
            editing={editing}
            onChange={(items) => handleChange({ docs: items as Organization['docs'] })}
            fields={docFields}
            maxItems={25}
          />
        );
      case 'domains':
        return (
          <AspectListTab
            items={org.domains || []}
            editing={editing}
            onChange={(items) => handleChange({ domains: items as Organization['domains'] })}
            fields={domainFields}
            maxItems={10}
          />
        );
      case 'relations':
        return (
          <RelationsTab
            relations={org.relations}
            editing={editing}
            onChange={(relations) => handleChange({ relations })}
          />
        );
      case 'financial':
        return (
          <OrgFinancialsPanel
            financial={org.financial}
            orgType={org.org_type}
            editing={editing}
            onChange={(financial) => handleChange({ financial })}
            defaultCollapsed={false}
          />
        );
      case 'metrics':
        return (
          <MetricsTab
            metrics={org.metrics}
            editing={editing}
            onChange={(metrics) => handleChange({ metrics })}
          />
        );
      case 'connections':
        return (
          <JsonObjectEditor
            data={org.connections || {}}
            editing={editing}
            onChange={(connections) => handleChange({ connections: connections as Organization['connections'] })}
            label="Connections (external system IDs)"
          />
        );
      case 'data':
        return (
          <JsonObjectEditor
            data={org.data || {}}
            editing={editing}
            onChange={(data) => handleChange({ data })}
            label="Custom Data (arbitrary JSON)"
          />
        );
      case 'gl_accounts':
        return (
          <JsonObjectEditor
            data={org.gl_accounts || {}}
            editing={editing}
            onChange={(gl_accounts) => handleChange({ gl_accounts })}
            label="GL Accounts (account mappings)"
          />
        );
      case 'refs':
        return (
          <JsonObjectEditor
            data={org.refs || {}}
            editing={editing}
            onChange={(refs) => handleChange({ refs })}
            label="References (external references)"
          />
        );
      case 'prefs':
        return (
          <JsonObjectEditor
            data={org.prefs || {}}
            editing={editing}
            onChange={(prefs) => handleChange({ prefs })}
            label="Preferences (user preferences)"
          />
        );
      case 'metadata':
        return (
          <JsonObjectEditor
            data={org.metadata || {}}
            editing={editing}
            onChange={(metadata) => handleChange({ metadata })}
            label="Metadata (system metadata)"
          />
        );
      case 'qa':
        return (
          <QAPanel
            entityType={orgType as any}
            entityId={Number(org.id ?? 0)}
            data={org.data}
          />
        );
      default:
        return null;
    }
  };

  // Inline mode rendering
  if (isInline) {
    return (
      <DetailShell
        title={title}
        mode={inlineMode === 'add' ? 'add' : editing ? 'edit' : 'view'}
        inline
        hideBreadcrumb
        onCancelInline={onClose}
        showInlineHeader={false}
        card={false}
      >
        <SimpleDetailHeader
          entityName={title}
          id={org.id}
          mode={inlineMode === 'add' ? 'add' : editing ? 'edit' : 'view'}
        />
        <SimpleDetailToolbar
          mode={inlineMode === 'add' ? 'add' : editing ? 'edit' : 'view'}
          isSaving={saving}
          onEdit={() => setEditing(true)}
          onCancel={handleCancel}
          onSave={handleSave}
        />
        <BasicInformationPanel
          org={org}
          editing={editing}
          onChange={handleChange}
          columnCount={2}
        />
        {/* ── Scalar & JSONB cards (view mode) ──────────────── */}
        {!editing && org && (
          <div className="space-y-4 px-2 py-2">
            <ScalarCard
              title="Organization Details"
              fields={[
                { label: "display_name", value: org.display_name },
                { label: "org_type", value: org.org_type },
                { label: "email", value: (org as any).email },
                { label: "email_id", value: (org as any).email_id },
                { label: "attention", value: (org as any).attention },
                { label: "phone", value: (org as any).phone },
                { label: "phone_id", value: (org as any).phone_id },
                { label: "address_full", value: (org as any).address_full },
                { label: "address_id", value: (org as any).address_id },
                { label: "domain", value: (org as any).domain },
                { label: "domain_id", value: (org as any).domain_id },
                { label: "price_level", value: (org as any).price_level },
                { label: "terms", value: (org as any).terms },
                { label: "status", value: org.status },
                { label: "contact_id", value: (org as any).contact_id },
              ]}
              columns={2}
            />
            <JsonCard title="Financial" fieldName="financial" data={org.financial as Record<string, unknown>} columns={2} />
            <JsonCard title="Connections" fieldName="connections" data={org.connections as Record<string, unknown>} columns={2} />
            <JsonCard title="Data" fieldName="data" data={org.data as Record<string, unknown>} columns={2} />
            <JsonCard title="Metrics" fieldName="metrics" data={org.metrics as Record<string, unknown>} columns={2} />
            <JsonCard title="GL Accounts" fieldName="gl_accounts" data={org.gl_accounts as Record<string, unknown>} columns={2} />
            <JsonCard title="Relations" fieldName="relations" data={org.relations as Record<string, unknown>} columns={2} />
            <BaseModelCards data={org as any} />
          </div>
        )}
        <ComponentCard>
          {/* Tabs */}
          <div className="mb-4 flex flex-wrap gap-1 border-b border-slate-200 dark:border-slate-700">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-3 py-2 text-sm font-medium ${
                  activeTab === tab.key
                    ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'
                }`}
              >
                {tab.icon}
                <span className="hidden sm:inline">{tab.label}</span>
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="min-h-50">{renderTabContent()}</div>
        </ComponentCard>
        {(orgType === 'customer' || orgType === 'vendor') && org.id && (
          <>
            <div>
              <TransactionTabs orgType={orgType} orgId={org.id} />
            </div>
            <div>
              <ItemTabs orgType={orgType} orgId={org.id} />
            </div>
          </>
        )}
      </DetailShell>
    );
  }

  // Standalone mode rendering
  return (
    <DetailShell
      title={title}
      mode={editing ? 'edit' : 'view'}
      breadcrumbTitle={org.display_name || 'New'}
      card={false}
    >
      <SimpleDetailHeader
        entityName={title}
        id={org.id}
        mode={editing ? 'edit' : 'view'}
      />
      <SimpleDetailToolbar
        mode={editing ? 'edit' : 'view'}
        isSaving={saving}
        onEdit={() => setEditing(true)}
        onCancel={handleCancel}
        onSave={handleSave}
      />
      <BasicInformationPanel
        org={org}
        editing={editing}
        onChange={handleChange}
        columnCount={3}
      />
      {/* ── Scalar & JSONB cards (view mode) ──────────────── */}
      {!editing && org && (
        <div className="space-y-4 px-4 py-2">
          <ScalarCard
            title="Organization Details"
            fields={[
              { label: "display_name", value: org.display_name },
              { label: "org_type", value: org.org_type },
              { label: "email", value: (org as any).email },
              { label: "email_id", value: (org as any).email_id },
              { label: "attention", value: (org as any).attention },
              { label: "phone", value: (org as any).phone },
              { label: "phone_id", value: (org as any).phone_id },
              { label: "address_full", value: (org as any).address_full },
              { label: "address_id", value: (org as any).address_id },
              { label: "domain", value: (org as any).domain },
              { label: "domain_id", value: (org as any).domain_id },
              { label: "price_level", value: (org as any).price_level },
              { label: "terms", value: (org as any).terms },
              { label: "status", value: org.status },
              { label: "contact_id", value: (org as any).contact_id },
            ]}
            columns={3}
          />
          <JsonCard title="Financial" fieldName="financial" data={org.financial as Record<string, unknown>} columns={2} />
          <JsonCard title="Connections" fieldName="connections" data={org.connections as Record<string, unknown>} columns={2} />
          <JsonCard title="Data" fieldName="data" data={org.data as Record<string, unknown>} columns={2} />
          <JsonCard title="Metrics" fieldName="metrics" data={org.metrics as Record<string, unknown>} columns={2} />
          <JsonCard title="GL Accounts" fieldName="gl_accounts" data={org.gl_accounts as Record<string, unknown>} columns={2} />
          <JsonCard title="Relations" fieldName="relations" data={org.relations as Record<string, unknown>} columns={2} />
          <BaseModelCards data={org as any} />
        </div>
      )}
      <ComponentCard>
        {/* Tabs */}
        <div className="mb-6 flex flex-wrap gap-2 border-b border-slate-200 dark:border-slate-700">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="min-h-75">{renderTabContent()}</div>
      </ComponentCard>
      {(orgType === 'customer' || orgType === 'vendor') && org.id && (
        <>
          <div>
            <TransactionTabs orgType={orgType} orgId={org.id} />
          </div>
          <div>
            <ItemTabs orgType={orgType} orgId={org.id} />
          </div>
        </>
      )}
    </DetailShell>
  );
};

export default withDevIdentifier(OrgDetail, 'OrgDetail');