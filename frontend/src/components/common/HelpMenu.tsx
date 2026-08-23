/**
 * HelpMenu — context-aware help as a select list.
 *
 * Matches TopBar aesthetic — compact select, same styling as Font/View/Theme.
 * Options: Help (opens help window), Paste (opens GetHelp dialog), Alice hints badge.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import GetHelpDialog from './GetHelpDialog';
import { useAlice } from '@/context/AliceContext';

function getContextFromPath(path: string): { model: string; context: string; label: string } {
  const p = path.toLowerCase();
  if (p.includes('/db/')) { const m = p.split('/db/')[1]?.split(/[/?]/)[0]; return m ? { model: m, context: m, label: m } : { model: 'system', context: 'databrowser', label: 'databrowser' }; }
  if (p.includes('/admin-wb') || p.includes('/databrowser')) { const m = p.match(/model=([a-z_]+)/); return m ? { model: m[1], context: m[1], label: m[1] } : { model: 'system', context: 'databrowser', label: 'databrowser' }; }
  if (p.includes('/alice')) return { model: 'system', context: 'alice', label: 'Alice' };
  if (p.includes('/dashboard')) return { model: 'system', context: 'dashboard', label: 'Dashboard' };
  if (p.includes('/kanban')) return { model: 'system', context: 'kanban', label: 'Kanban' };
  if (p.includes('/gantt')) return { model: 'system', context: 'gantt', label: 'Gantt' };
  if (p.includes('/invoice')) return { model: 'invoice', context: 'invoice', label: 'Invoices' };
  if (p.includes('/order')) return { model: 'order', context: 'order', label: 'Orders' };
  if (p.includes('/proposal')) return { model: 'proposal', context: 'proposal', label: 'Proposals' };
  if (p.includes('/purchase')) return { model: 'purchase', context: 'purchase', label: 'Purchases' };
  if (p.includes('/payment')) return { model: 'payment', context: 'payment', label: 'Payments' };
  if (p.includes('/customer')) return { model: 'customer', context: 'customer', label: 'Customers' };
  if (p.includes('/contact')) return { model: 'contact', context: 'contact', label: 'Contacts' };
  if (p.includes('/item')) return { model: 'item', context: 'item', label: 'Items' };
  return { model: 'system', context: 'general', label: 'General' };
}

/** Open help for a specific field — call from Cmd+Option+Shift+click on labels */
export function openFieldHelp(model: string, fieldName: string) {
  window.open(`/help?context=${model}&model=${model}&field=${fieldName}`, 'wc_help', 'width=800,height=900,scrollbars=yes,resizable=yes');
}

interface HelpMenuProps {
  className?: string;
}

export default function HelpMenu({ className }: HelpMenuProps) {
  const location = useLocation();
  const ctx = getContextFromPath(location.pathname + location.search);
  const [showGetHelp, setShowGetHelp] = useState(false);
  const alice = useAlice();
  const hintCount = alice.hints.length;

  const openHelp = useCallback(() => {
    window.open(`/help?context=${ctx.context}&model=${ctx.model}`, 'wc_help', 'width=800,height=900,scrollbars=yes,resizable=yes');
  }, [ctx]);

  // Cmd+/ or Cmd+? → open Get Help dialog
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === '/' || e.key === '?')) {
        e.preventDefault();
        setShowGetHelp(true);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  return (
    <>
      <select
        className={`w-[52px] rounded border border-slate-200 bg-white px-1 py-0.5 text-[10px] text-slate-600 cursor-pointer ${className || ''}`}
        value=""
        onChange={(e) => {
          const v = e.target.value;
          if (v === 'help') openHelp();
          else if (v === 'paste') setShowGetHelp(true);
          e.target.value = '';
        }}
        title={`Help: ${ctx.label} · Shift+hover any zone, click nametag to copy, Cmd+/ to paste into Help`}
      >
        <option value="">Help{hintCount > 0 ? ` (${hintCount})` : ''}</option>
        <option value="help">{ctx.label}</option>
        <option value="paste">Paste (Cmd+/)</option>
      </select>
      <GetHelpDialog open={showGetHelp} onClose={() => setShowGetHelp(false)} />
    </>
  );
}
