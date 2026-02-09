/**
 * BasicInformationPanel - Compact read-only display of org basic information
 * 
 * Displays common OrgBase scalar fields in a horizontal layout.
 * Reusable across all org apps (customer, vendor, employee, rep, manufacturer).
 */
import React from 'react';
import { FaBuilding } from 'react-icons/fa';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface BasicInformationData {
  id?: number;
  display_name?: string;
  attention?: string | null;
  email?: string | null;
  phone?: string | null;
  price_level?: string | null;
  status?: string;
  org_type?: string;
  version?: number;
  is_active?: boolean;
}

interface BasicInformationPanelProps {
  /** Organization data */
  data: BasicInformationData;
  /** Number of columns (2 or 3) */
  columns?: 2 | 3;
  /** Show header with icon */
  showHeader?: boolean;
  /** Custom title */
  title?: string;
  /** Additional CSS classes */
  className?: string;
}

// ---------------------------------------------------------------------------
// Row Component - Horizontal label/value pair
// ---------------------------------------------------------------------------

interface RowProps {
  label: string;
  value: React.ReactNode;
}

const Row: React.FC<RowProps> = ({ label, value }) => (
  <div className="flex items-center gap-2">
    <dt className="w-20 shrink-0 text-right text-sm text-slate-500 dark:text-slate-400">{label}</dt>
    <dd className="font-medium text-sm text-slate-900 dark:text-slate-100">{value || '—'}</dd>
  </div>
);

// ---------------------------------------------------------------------------
// Status Badge Component
// ---------------------------------------------------------------------------

const ActiveBadge: React.FC<{ isActive: boolean }> = ({ isActive }) => (
  <span className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full ${
    isActive
      ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400'
      : 'bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400'
  }`}>
    {isActive ? 'Yes' : 'No'}
  </span>
);

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

const BasicInformationPanel: React.FC<BasicInformationPanelProps> = ({
  data,
  columns = 3,
  showHeader = true,
  title = 'Basic Information',
  className = '',
}) => {
  const gridCols = columns === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-2';

  return (
    <div className={`bg-slate-50 dark:bg-slate-800 rounded-lg p-4 ${className}`}>
      {showHeader && (
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-3 flex items-center gap-2">
          <FaBuilding size={16} />
          {title}
        </h3>
      )}
      <dl className={`grid grid-cols-1 ${gridCols} gap-x-6 gap-y-2 text-sm`}>
        <Row label="Company" value={data.display_name} />
        <Row label="Email" value={data.email} />
        <Row label="Attention" value={data.attention} />
        <Row label="Phone" value={data.phone} />
        <Row label="Price Level" value={data.price_level} />
        <Row label="Status" value={data.status ? <span className="capitalize">{data.status}</span> : null} />
        <Row label="Org Type" value={data.org_type ? <span className="capitalize">{data.org_type}</span> : null} />
        <Row label="Version" value={data.version?.toString()} />
        <Row label="Active" value={<ActiveBadge isActive={data.is_active ?? false} />} />
      </dl>
    </div>
  );
};

export default BasicInformationPanel;
