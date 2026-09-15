/**
 * ActionSummaryFooter — card footer showing the next action for a record.
 *
 * Registered in cardRegistry as 'action_summary'.
 */
import React from 'react';
import { registerFooterComponent } from './cardRegistry';
import type { FooterComponentProps } from './cardRegistry';

const ActionSummaryFooter: React.FC<FooterComponentProps> = ({ data }) => {
  const nextAction = data?.actions?.items?.[0];
  if (!nextAction) return null;

  const actionText = typeof nextAction.action === 'object'
    ? nextAction.action?.en
    : nextAction.action;

  return (
    <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--db-border)' }}>
      <div
        style={{ fontSize: 10, fontWeight: 500, color: 'var(--db-text-muted)', cursor: 'pointer' }}
        onClick={() => {
          const actionId = nextAction.id;
          if (actionId) window.open(`/action?id=${actionId}`, '_blank');
        }}
        title="Click to open action record"
      >Next Action</div>
      <div style={{ fontSize: '0.75rem', color: 'var(--db-text)' }}>
        {actionText ? `${actionText} — ${nextAction.status || 'pending'}` : '—'}
      </div>
      {nextAction.assigned_to && (
        <div style={{ fontSize: 10, color: 'var(--db-text-muted)', marginTop: 2 }}>
          {nextAction.assigned_to}
        </div>
      )}
    </div>
  );
};

// Self-register
registerFooterComponent('action_summary', ActionSummaryFooter);

export default ActionSummaryFooter;
