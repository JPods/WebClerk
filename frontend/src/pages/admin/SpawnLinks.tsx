/* LastChecked: 2026-08-14 | WhereUsed: DataBrowser detail pane | WhoCreated: Bill+Claude */
import React from 'react';

// ---------------------------------------------------------------------------
// SpawnLinks — related-window buttons for complex records
// ---------------------------------------------------------------------------

export const SPAWN_CONFIG: Record<string, Array<{ label: string; target: string; filterKey: string }>> = {
  serial: [
    { label: 'History', target: 'serial_log', filterKey: 'serial_id' },
    { label: 'Q&A', target: 'question_answer', filterKey: 'refs__links__serial_id' },
    { label: 'Documents', target: 'document', filterKey: 'refs__links__serial_id' },
    { label: 'Actions', target: 'action', filterKey: 'refs__links__serial_id' },
    { label: 'Customer', target: 'contact', filterKey: 'id' },
    { label: 'Vendor', target: 'contact', filterKey: 'id' },
  ],
  item: [
    { label: 'Serials', target: 'serial', filterKey: 'item_id' },
    { label: 'XRefs', target: 'item_xref', filterKey: 'item_id' },
    { label: 'Org Items', target: 'org_item', filterKey: 'item_id' },
    { label: 'Documents', target: 'document', filterKey: 'refs__links__item_id' },
  ],
  invoice: [
    { label: 'Lines', target: 'invoice_line', filterKey: 'invoice_id' },
    { label: 'Payments', target: 'payment', filterKey: 'invoice_id' },
    { label: 'Customer', target: 'contact', filterKey: 'id' },
    { label: 'Documents', target: 'document', filterKey: 'refs__links__invoice_id' },
  ],
  order: [
    { label: 'Lines', target: 'order_line', filterKey: 'order_id' },
    { label: 'Customer', target: 'contact', filterKey: 'id' },
    { label: 'Documents', target: 'document', filterKey: 'refs__links__order_id' },
  ],
  contact: [
    { label: 'Orders', target: 'order', filterKey: 'customer_id' },
    { label: 'Invoices', target: 'invoice', filterKey: 'customer_id' },
    { label: 'Payments', target: 'payment', filterKey: 'invoice__customer_id' },
    { label: 'Serials', target: 'serial', filterKey: 'refs__links__customer_id' },
    { label: 'Actions', target: 'action', filterKey: 'refs__links__contact_id' },
    { label: 'Touches', target: 'touch', filterKey: 'contact_id' },
    { label: 'Documents', target: 'document', filterKey: 'refs__links__contact_id' },
  ],
  action: [
    { label: 'Touches', target: 'touch', filterKey: 'action_id' },
    { label: 'Documents', target: 'document', filterKey: 'refs__links__action_id' },
  ],
  customer: [
    { label: 'Contacts', target: 'contact', filterKey: 'customer_id' },
    { label: 'Orders', target: 'order', filterKey: 'customer_id' },
    { label: 'Invoices', target: 'invoice', filterKey: 'customer_id' },
    { label: 'Touches', target: 'touch', filterKey: 'org_id' },
  ],
  vendor: [
    { label: 'Contacts', target: 'contact', filterKey: 'vendor_id' },
    { label: 'Purchases', target: 'purchase', filterKey: 'vendor_id' },
    { label: 'Touches', target: 'touch', filterKey: 'org_id' },
  ],
};

export const SpawnLinks: React.FC<{ model: string; record: any; recordId: number }> = ({ model, record, recordId }) => {
  const links = SPAWN_CONFIG[model];
  if (!links || !links.length) return null;

  const openSpawn = (link: typeof links[0]) => {
    let filterValue = recordId;
    // For customer/vendor links, resolve the ID from refs
    if (link.label === 'Customer' && link.target === 'contact') {
      const refs = record.refs || {};
      filterValue = refs?.links?.customer_id || refs?.links?.contact?.[0] || recordId;
    } else if (link.label === 'Vendor' && link.target === 'contact') {
      const refs = record.refs || {};
      filterValue = refs?.links?.vendor_id || recordId;
    }
    window.open(`/${link.target}?${link.filterKey}=${filterValue}`, '_blank');
  };

  return (
    <div className="db-spawn-bar">
      <span className="db-spawn-label">Related:</span>
      {links.map((link) => (
        <button key={link.label} className="db-btn db-btn--small db-btn--ghost"
          onClick={() => openSpawn(link)}
          title={`Open ${link.label} in new databrowser window`}>
          {link.label} ↗
        </button>
      ))}
    </div>
  );
};

export default SpawnLinks;
