/**
 * HelpMenu — context-aware help button.
 *
 * Click: opens Help Dashboard in its own window for the current page context.
 * Cmd+Option+Shift+click on any field label: opens help for that specific field.
 *
 * Detects current context from URL path automatically.
 */
import React, { useCallback } from 'react';
import { useLocation } from 'react-router-dom';

interface HelpMenuProps {
  className?: string;
}

function getContextFromPath(path: string): { model: string; context: string; label: string } {
  const p = path.toLowerCase();
  if (p.includes('/admin-wb')) { const m = p.match(/model=([a-z_]+)/); return m ? { model: m[1], context: m[1], label: m[1] } : { model: 'system', context: 'databrowser', label: 'DataBrowser' }; }
  if (p.includes('/alice-dashboard')) return { model: 'system', context: 'alice', label: 'Alice' };
  if (p.includes('/dashboard')) return { model: 'system', context: 'dashboard', label: 'Dashboard' };
  if (p.includes('/invoice')) return { model: 'invoice', context: 'invoice', label: 'Invoices' };
  if (p.includes('/order')) return { model: 'order', context: 'order', label: 'Orders' };
  if (p.includes('/proposal')) return { model: 'proposal', context: 'proposal', label: 'Proposals' };
  if (p.includes('/purchase')) return { model: 'purchase', context: 'purchase', label: 'Purchases' };
  if (p.includes('/workorder') || p.includes('/work-order')) return { model: 'work_order', context: 'workorder', label: 'Work Orders' };
  if (p.includes('/payment')) return { model: 'payment', context: 'payment', label: 'Payments' };
  if (p.includes('/customer')) return { model: 'customer', context: 'customer', label: 'Customers' };
  if (p.includes('/vendor')) return { model: 'vendor', context: 'vendor', label: 'Vendors' };
  if (p.includes('/employee')) return { model: 'employee', context: 'employee', label: 'Employees' };
  if (p.includes('/contact')) return { model: 'contact', context: 'contact', label: 'Contacts' };
  if (p.includes('/item')) return { model: 'item', context: 'item', label: 'Items' };
  if (p.includes('/help')) return { model: 'system', context: 'help', label: 'Help' };
  return { model: 'system', context: 'general', label: 'General' };
}

/** Open help for a specific field — call from Cmd+Option+Shift+click on labels */
export function openFieldHelp(model: string, fieldName: string) {
  window.open(`/help?context=${model}&model=${model}&field=${fieldName}`, 'wc_help', 'width=800,height=900,scrollbars=yes,resizable=yes');
}

export default function HelpMenu({ className }: HelpMenuProps) {
  const location = useLocation();
  const ctx = getContextFromPath(location.pathname + location.search);

  const openHelp = useCallback(() => {
    window.open(`/help?context=${ctx.context}&model=${ctx.model}`, 'wc_help', 'width=800,height=900,scrollbars=yes,resizable=yes');
  }, [ctx]);

  return (
    <button onClick={openHelp} title={`Help: ${ctx.label}`}
      className={`px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 transition shadow-sm ${className || ''}`}>
      ? Help
    </button>
  );
}
