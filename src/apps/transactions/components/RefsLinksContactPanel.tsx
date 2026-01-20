/**
 * RefsLinksContactPanel - Display contacts grouped by purpose as text blocks
 * Each purpose (billto, shipto, attention, etc.) gets its own section
 */
import React from 'react';
import { FaUser, FaEnvelope, FaPhone, FaBuilding, FaPlus, FaTimes } from 'react-icons/fa';
import type { ContactDenorm, ContactPurpose } from '../types/transactionTypes';
import { getContactDisplayName, formatPurpose, groupContactsByPurpose } from '../types/transactionTypes';

interface RefsLinksContactPanelProps {
  contacts: ContactDenorm[];
  isEditing?: boolean;
  onAdd?: (purpose: ContactPurpose) => void;
  onRemove?: (contactId: number) => void;
  onEdit?: (contact: ContactDenorm) => void;
}

// Standard purposes in display order
const STANDARD_PURPOSES: ContactPurpose[] = ['billto', 'shipto', 'attention', 'approver', 'buyer', 'cc', 'notify'];

const ContactBlock: React.FC<{
  contact: ContactDenorm;
  isEditing?: boolean;
  onRemove?: () => void;
  onEdit?: () => void;
}> = ({ contact, isEditing, onRemove, onEdit }) => {
  const displayName = getContactDisplayName(contact);
  
  return (
    <div className="relative group">
      {isEditing && onRemove && (
        <button
          onClick={onRemove}
          className="absolute -right-2 -top-2 hidden group-hover:flex items-center justify-center w-5 h-5 rounded-full bg-red-500 text-white text-xs hover:bg-red-600"
          title="Remove contact"
        >
          <FaTimes size={10} />
        </button>
      )}
      <div 
        className={`text-sm ${isEditing && onEdit ? 'cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800 rounded p-1 -m-1' : ''}`}
        onClick={isEditing && onEdit ? onEdit : undefined}
      >
        <div className="font-medium text-slate-800 dark:text-slate-200 flex items-center gap-2">
          <FaUser size={12} className="text-slate-400" />
          {displayName}
          {contact.role && (
            <span className="text-xs text-slate-500 dark:text-slate-400">({contact.role})</span>
          )}
        </div>
        {contact.company && (
          <div className="text-slate-600 dark:text-slate-400 flex items-center gap-2 ml-5">
            <FaBuilding size={10} className="text-slate-400" />
            {contact.company}
            {contact.title && <span className="text-slate-500">· {contact.title}</span>}
          </div>
        )}
        <div className="flex flex-wrap gap-4 ml-5 mt-1 text-slate-500 dark:text-slate-400">
          {contact.email && (
            <span className="flex items-center gap-1">
              <FaEnvelope size={10} />
              <a href={`mailto:${contact.email}`} className="hover:text-blue-500">{contact.email}</a>
            </span>
          )}
          {contact.phone && (
            <span className="flex items-center gap-1">
              <FaPhone size={10} />
              <a href={`tel:${contact.phone}`} className="hover:text-blue-500">{contact.phone}</a>
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

const PurposeSection: React.FC<{
  purpose: string;
  contacts: ContactDenorm[];
  isEditing?: boolean;
  onAdd?: () => void;
  onRemove?: (contactId: number) => void;
  onEdit?: (contact: ContactDenorm) => void;
}> = ({ purpose, contacts, isEditing, onAdd, onRemove, onEdit }) => {
  return (
    <div className="border-b border-slate-200 dark:border-slate-700 pb-4 last:border-0 last:pb-0">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide">
          {formatPurpose(purpose)}
        </h4>
        {isEditing && onAdd && (
          <button
            onClick={onAdd}
            className="text-xs text-blue-500 hover:text-blue-600 flex items-center gap-1"
          >
            <FaPlus size={10} /> Add
          </button>
        )}
      </div>
      <div className="space-y-3">
        {contacts.length > 0 ? (
          contacts.map((contact) => (
            <ContactBlock
              key={contact.id}
              contact={contact}
              isEditing={isEditing}
              onRemove={onRemove ? () => onRemove(contact.id) : undefined}
              onEdit={onEdit ? () => onEdit(contact) : undefined}
            />
          ))
        ) : (
          <p className="text-sm text-slate-400 dark:text-slate-500 italic">No contact assigned</p>
        )}
      </div>
    </div>
  );
};

const RefsLinksContactPanel: React.FC<RefsLinksContactPanelProps> = ({
  contacts = [],
  isEditing = false,
  onAdd,
  onRemove,
  onEdit,
}) => {
  const grouped = groupContactsByPurpose(contacts);
  
  // Get all unique purposes, with standard ones first
  const allPurposes = new Set([
    ...STANDARD_PURPOSES.filter(p => grouped[p]?.length > 0 || isEditing),
    ...Object.keys(grouped).filter(p => !STANDARD_PURPOSES.includes(p as ContactPurpose)),
  ]);

  if (allPurposes.size === 0 && !isEditing) {
    return (
      <div className="text-sm text-slate-500 dark:text-slate-400 italic">
        No contacts linked to this transaction
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {Array.from(allPurposes).map((purpose) => (
        <PurposeSection
          key={purpose}
          purpose={purpose}
          contacts={grouped[purpose] || []}
          isEditing={isEditing}
          onAdd={onAdd ? () => onAdd(purpose as ContactPurpose) : undefined}
          onRemove={onRemove}
          onEdit={onEdit}
        />
      ))}
    </div>
  );
};

export default RefsLinksContactPanel;
