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

  // assigned_to is a roster: [{id, name, …}], first entry responsible.
  const roster = Array.isArray(nextAction.assigned_to) ? nextAction.assigned_to : [];
  const assignedNames = roster.map((p: { name?: string }) => p?.name).filter(Boolean).join(', ');

  return (
    <div className="mt-2 pt-2 border-t db-border-color">
      <div
        className="db-font-xs font-medium db-text-muted cursor-pointer"
        onClick={() => {
          const actionId = nextAction.id;
          if (actionId) window.open(`/action?id=${actionId}`, '_blank');
        }}
        title="Click to open action record"
      >Next Action</div>
      <div className="text-xs db-text">
        {actionText ? `${actionText} — ${nextAction.status || 'pending'}` : '—'}
      </div>
      {assignedNames && (
        <div className="db-font-xs db-text-muted mt-0.5">{assignedNames}</div>
      )}
    </div>
  );
};

// Self-register
registerFooterComponent('action_summary', ActionSummaryFooter);

export default ActionSummaryFooter;
