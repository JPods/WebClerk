/* LastChecked: 2026-08-03 | WhereUsed: CommunicationsPanel, ContactDetail | WhoCreated: Claude */
/**
 * CommList — renders a list of communication records for a parent entity.
 * Each record is a CommCard. Supports add, edit, delete.
 *
 * Usage:
 *   <CommList model="phone" parentModel="contact" parentId={8} records={phones} onRefresh={reload} />
 */
import React, { useState } from 'react';
import CommCard from './CommCard';

export interface CommListProps {
  model: 'email' | 'phone' | 'address' | 'domain';
  parentModel: string;
  parentId: number;
  records: any[];
  onRefresh?: () => void;
}

const ICONS: Record<string, string> = { email: '✉', phone: '☎', address: '📍', domain: '🌐' };

const CommList: React.FC<CommListProps> = ({ model, parentModel, parentId, records, onRefresh }) => {
  const [adding, setAdding] = useState(false);

  return (
    <div className="mb-3">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[10px] font-bold text-slate-500 uppercase">{ICONS[model]} {model}s</span>
        <span className="text-[9px] text-slate-400">({records.length})</span>
        <span className="flex-1" />
        <button onClick={() => setAdding(true)}
          className="text-[9px] text-green-600 hover:text-green-800 font-medium px-1">+ add</button>
      </div>
      <div className="space-y-1">
        {records.map((rec: any) => (
          <CommCard
            key={rec.id}
            model={model}
            data={rec}
            onSave={() => onRefresh?.()}
            onDelete={() => onRefresh?.()}
          />
        ))}
        {adding && (
          <CommCard
            model={model}
            data={{ contact: parentId }}
            isNew
            onSave={() => { setAdding(false); onRefresh?.(); }}
            onCancel={() => setAdding(false)}
          />
        )}
        {!records.length && !adding && (
          <div className="text-[10px] text-slate-400 italic py-1">No {model}s</div>
        )}
      </div>
    </div>
  );
};

export default CommList;
