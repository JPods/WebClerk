/* LastChecked: 2026-08-03 | WhereUsed: ContactDetail | WhoCreated: Claude */
/**
 * OrgPanel — shows all org relationships for a contact.
 * Each org type gets its own section with OrgCards.
 *
 * Usage:
 *   <OrgPanel
 *     contactId={8}
 *     customer={refs.links.customer}
 *     vendor={refs.links.vendor}
 *     onRefresh={reload}
 *     onOpenOrg={(model, id) => openWindow(`/${model}/${id}`)}
 *   />
 */
import React from 'react';
import { useWindowManager } from '@/context/WindowManagerContext';
import OrgCard from './OrgCard';
import type { OrgModel } from './OrgCard';

export interface OrgPanelProps {
  contactId: number;
  customer?: any;    // single object or null
  vendor?: any;
  manufacturer?: any;
  employee?: any;
  rep?: any;
  onRefresh?: () => void;
}

const OrgPanel: React.FC<OrgPanelProps> = ({
  contactId, customer, vendor, manufacturer, employee, rep, onRefresh,
}) => {
  const windowManager = useWindowManager();

  const openOrg = (model: OrgModel, id: number) => {
    windowManager.ensureWindow(`/${model}/${id}`, `${model} #${id}`);
  };

  const orgs: Array<{ model: OrgModel; data: any; label: string }> = [
    ...(customer ? [{ model: 'customer' as OrgModel, data: customer, label: 'Customer' }] : []),
    ...(vendor ? [{ model: 'vendor' as OrgModel, data: vendor, label: 'Vendor' }] : []),
    ...(manufacturer ? [{ model: 'manufacturer' as OrgModel, data: manufacturer, label: 'Manufacturer' }] : []),
    ...(employee ? [{ model: 'employee' as OrgModel, data: employee, label: 'Employee' }] : []),
    ...(rep ? [{ model: 'rep' as OrgModel, data: rep, label: 'Rep' }] : []),
  ];

  return (
    <div className="p-3 space-y-2">
      {orgs.length === 0 && (
        <div className="text-[10px] text-slate-400 italic py-2">No organization links</div>
      )}
      {orgs.map(({ model, data }) => (
        <OrgCard
          key={model}
          model={model}
          data={data}
          compact
          onClick={(id) => openOrg(model, id)}
          onSave={() => onRefresh?.()}
          onDelete={() => onRefresh?.()}
        />
      ))}
    </div>
  );
};

export default OrgPanel;
