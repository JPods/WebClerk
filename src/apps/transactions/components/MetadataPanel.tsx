/**
 * MetadataPanel - Admin-only collapsible metadata display
 * Shows history, health, access, flags, versioning
 */
import React, { useState } from 'react';
import { FaChevronDown, FaChevronRight, FaHistory, FaHeart, FaLock, FaFlag, FaCodeBranch, FaShieldAlt } from 'react-icons/fa';
import type { TransactionMetadata } from '../types/transactionTypes';
import { withDevIdentifier } from '@/components/common/DevIdentifier';

interface MetadataPanelProps {
  metadata: TransactionMetadata | undefined;
  isEditing?: boolean;
  onChange?: (metadata: TransactionMetadata) => void;
}

const Section: React.FC<{
  title: string;
  icon: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
}> = ({ title, icon, defaultOpen = false, children }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border-b border-slate-200 dark:border-slate-700 last:border-0">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-2 py-2 text-left text-sm font-medium text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white"
      >
        {isOpen ? <FaChevronDown size={10} /> : <FaChevronRight size={10} />}
        {icon}
        {title}
      </button>
      {isOpen && <div className="pl-6 pb-3">{children}</div>}
    </div>
  );
};

const KeyValue: React.FC<{ label: string; value: string | number | null | undefined }> = ({ label, value }) => (
  <div className="flex justify-between text-xs py-0.5">
    <span className="text-slate-500 dark:text-slate-400">{label}</span>
    <span className="text-slate-700 dark:text-slate-300 font-mono">{value ?? '--'}</span>
  </div>
);

const formatTimestamp = (ts?: number): string => {
  if (!ts) return '--';
  return new Date(ts).toLocaleString();
};

const HealthBar: React.FC<{ label: string; value?: number }> = ({ label, value }) => {
  const displayValue = value ?? 0;
  const color = displayValue >= 80 ? 'bg-green-500' : displayValue >= 50 ? 'bg-amber-500' : 'bg-red-500';
  
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-slate-500 dark:text-slate-400">{label}</span>
        <span className="text-slate-700 dark:text-slate-300">{displayValue}%</span>
      </div>
      <div className="h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${displayValue}%` }} />
      </div>
    </div>
  );
};

const MetadataPanel: React.FC<MetadataPanelProps> = ({
  metadata = {},
  isEditing = false,
  onChange,
}) => {
  const handleChange = (field: keyof TransactionMetadata, value: unknown) => {
    if (onChange) {
      onChange({ ...metadata, [field]: value });
    }
  };

  return (
    <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4 space-y-1">
      <div className="flex items-center gap-2 pb-2 border-b border-slate-200 dark:border-slate-700">
        <FaShieldAlt className="text-slate-400" size={14} />
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
          System Metadata
        </h4>
        <span className="text-xs text-slate-400 ml-auto">Admin Only</span>
      </div>

      {/* Basic Info */}
      <div className="py-2 space-y-1">
        <KeyValue label="Security" value={metadata.security} />
        <KeyValue label="Publish" value={metadata.publish} />
        <KeyValue label="Priority" value={metadata.priority} />
        <KeyValue label="Schema Version" value={metadata.version} />
      </div>

      {/* History Section */}
      <Section title="History" icon={<FaHistory size={12} className="text-slate-400" />}>
        <div className="space-y-1">
          <KeyValue label="Created" value={formatTimestamp(metadata.history?.created?.dt)} />
          <KeyValue label="Modified" value={formatTimestamp(metadata.history?.modified?.dt)} />
          <KeyValue label="Accessed" value={formatTimestamp(metadata.history?.accessed?.dt)} />
          <KeyValue label="Verified" value={formatTimestamp(metadata.history?.verified?.dt)} />
          <KeyValue label="Synced" value={formatTimestamp(metadata.history?.synced?.dt)} />
        </div>
      </Section>

      {/* Health Section */}
      <Section title="Health" icon={<FaHeart size={12} className="text-slate-400" />}>
        <div className="space-y-2">
          <HealthBar label="Overall Rating" value={metadata.health?.rating} />
          <HealthBar label="Completeness" value={metadata.health?.completeness} />
          <HealthBar label="Accuracy" value={metadata.health?.accuracy} />
          <HealthBar label="Freshness" value={metadata.health?.freshness} />
          <HealthBar label="Consistency" value={metadata.health?.consistency} />
        </div>
      </Section>

      {/* Access Section */}
      <Section title="Access Control" icon={<FaLock size={12} className="text-slate-400" />}>
        <div className="space-y-1 text-xs">
          <div>
            <span className="text-slate-500 dark:text-slate-400">View Access: </span>
            <span className="text-slate-700 dark:text-slate-300 font-mono">
              {metadata.access?.view?.length ? metadata.access.view.join(', ') : 'None'}
            </span>
          </div>
          <div>
            <span className="text-slate-500 dark:text-slate-400">Edit Access: </span>
            <span className="text-slate-700 dark:text-slate-300 font-mono">
              {metadata.access?.edit?.length ? metadata.access.edit.join(', ') : 'None'}
            </span>
          </div>
        </div>
      </Section>

      {/* Flags Section */}
      <Section title="Flags" icon={<FaFlag size={12} className="text-slate-400" />}>
        <div className="space-y-1">
          <KeyValue label="Keywords Pending" value={metadata.flags?.keywords_pending ? 'Yes' : 'No'} />
          <KeyValue label="Schema Rev" value={metadata.flags?.schema_rev} />
        </div>
      </Section>

      {/* Versioning Section */}
      <Section title="Versioning" icon={<FaCodeBranch size={12} className="text-slate-400" />}>
        <div className="space-y-1 text-xs">
          <div>
            <span className="text-slate-500 dark:text-slate-400">Changed Fields: </span>
            <span className="text-slate-700 dark:text-slate-300 font-mono">
              {metadata.versioning?.changed_fields?.length 
                ? metadata.versioning.changed_fields.join(', ') 
                : 'None'}
            </span>
          </div>
          <KeyValue 
            label="Keywords Refreshed" 
            value={formatTimestamp(metadata.versioning?.keywords_dt_refreshed)} 
          />
        </div>
      </Section>
    </div>
  );
};

export default withDevIdentifier(MetadataPanel, 'MetadataPanel', 'teal');