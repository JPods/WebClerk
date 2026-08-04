/* LastChecked: 2026-08-03 | WhereUsed: ContactDetail, CustomerDetail, VendorDetail | WhoCreated: Claude */
/**
 * CommPanel — replaces CommunicationsPanel (1,704 lines) with JSON-driven CommList/CommCard.
 *
 * Shows all four communication types for a parent entity.
 * Each type reads from its detail_layout Setting via CommCard.
 *
 * Usage:
 *   <CommPanel
 *     contactId={8}
 *     emails={refs.links.email}
 *     phones={refs.links.phone}
 *     addresses={refs.links.address}
 *     domains={refs.links.domain}
 *     onRefresh={reloadRecord}
 *   />
 */
import React, { useCallback } from 'react';
import { getRecords } from '@/api/wcapi';
import CommList from './CommList';

export interface CommPanelProps {
  contactId: number;
  emails?: any[];
  phones?: any[];
  addresses?: any[];
  domains?: any[];
  showTypes?: ('email' | 'phone' | 'address' | 'domain')[];
  onRefresh?: () => void;
}

const CommPanel: React.FC<CommPanelProps> = ({
  contactId,
  emails = [],
  phones = [],
  addresses = [],
  domains = [],
  showTypes,
  onRefresh,
}) => {
  const types: Array<{ model: 'email' | 'phone' | 'address' | 'domain'; records: any[] }> = [
    { model: 'email', records: emails },
    { model: 'phone', records: phones },
    { model: 'address', records: addresses },
    { model: 'domain', records: domains },
  ];

  const visibleTypes = showTypes
    ? types.filter(t => showTypes.includes(t.model))
    : types;

  return (
    <div className="p-3 space-y-1">
      {visibleTypes.map(t => (
        <CommList
          key={t.model}
          model={t.model}
          parentModel="contact"
          parentId={contactId}
          records={t.records}
          onRefresh={onRefresh}
        />
      ))}
    </div>
  );
};

export default CommPanel;
