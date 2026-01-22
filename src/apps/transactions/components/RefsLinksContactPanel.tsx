/**
 * RefsLinksContactPanel - Display contacts grouped by purpose with editing support
 * Syncs with refs.links.contact structure from API
 */
import React, { useState } from "react";
import {
  FaUser,
  FaEnvelope,
  FaPhone,
  FaBuilding,
  FaPlus,
  FaTimes,
  FaEdit,
} from "react-icons/fa";
import type { ContactPurpose } from "../types/transactionTypes";

// API contact structure from refs.links.contact
export interface RefContact {
  contact_id: number;
  purpose: ContactPurpose | string;
  attention?: string;
  email?: string;
  phone?: string;
  full?: string;
  domain?: string;
  address_id?: number;
  email_id?: number;
  phone_id?: number;
  domain_id?: number;
}

interface RefsLinksContactPanelProps {
  contacts: RefContact[];
  isEditing?: boolean;
  onAdd?: (purpose: ContactPurpose | string) => void;
  onRemove?: (contactId: number) => void;
  onEdit?: (contact: RefContact) => void;
  onChange?: (contacts: RefContact[]) => void;
}

// Standard purposes in display order
const STANDARD_PURPOSES = [
  "billto",
  "shipto",
  "attention",
  "approver",
  "buyer",
  "cc",
  "notify",
  "support",
  "rep",
  "sales",
];

// Helper to format purpose label
const formatPurpose = (purpose: string): string => {
  return purpose
    .replace(/_/g, " ")
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
};

// Helper to group contacts by purpose
const groupContactsByPurpose = (
  contacts: RefContact[],
): Record<string, RefContact[]> => {
  const grouped: Record<string, RefContact[]> = {};
  contacts.forEach((contact) => {
    const purpose = contact.purpose || "other";
    if (!grouped[purpose]) {
      grouped[purpose] = [];
    }
    grouped[purpose].push(contact);
  });
  return grouped;
};

// Contact Edit Modal
const ContactEditModal: React.FC<{
  contact: RefContact | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (contact: RefContact) => void;
}> = ({ contact, isOpen, onClose, onSave }) => {
  // Always reset formData when a new contact is being edited (including same id with new data)
  const [formData, setFormData] = useState<RefContact>(
    contact || { contact_id: 0, purpose: "" },
  );
  React.useEffect(() => {
    setFormData(contact || { contact_id: 0, purpose: "" });
  }, [contact]);

  if (!isOpen || !contact) return null;

  const handleChange = (field: keyof RefContact, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-slate-800 rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
            Edit Contact
          </h3>
        </div>

        <div className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Purpose
            </label>
            <select
              value={formData.purpose}
              onChange={(e) => handleChange("purpose", e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
            >
              <option value="">-- Select Purpose --</option>
              {STANDARD_PURPOSES.map((p) => (
                <option key={p} value={p}>
                  {formatPurpose(p)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Attention / Name
            </label>
            <input
              type="text"
              value={formData.attention || ""}
              onChange={(e) => handleChange("attention", e.target.value)}
              placeholder="Contact name"
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Email
            </label>
            <input
              type="email"
              value={formData.email || ""}
              onChange={(e) => handleChange("email", e.target.value)}
              placeholder="email@example.com"
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Phone
            </label>
            <input
              type="tel"
              value={formData.phone || ""}
              onChange={(e) => handleChange("phone", e.target.value)}
              placeholder="123-456-7890"
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Domain
            </label>
            <input
              type="url"
              value={formData.domain || ""}
              onChange={(e) => handleChange("domain", e.target.value)}
              placeholder="www.example.com"
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Address
            </label>
            <textarea
              value={formData.full || ""}
              onChange={(e) => handleChange("full", e.target.value)}
              placeholder="Street address, city, state, zip"
              rows={3}
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
            />
          </div>
        </div>

        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              onSave(formData);
              onClose();
            }}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
};

const ContactBlock: React.FC<{
  contact: RefContact;
  isEditing?: boolean;
  onRemove?: () => void;
  onEdit?: () => void;
}> = ({ contact, isEditing, onRemove, onEdit }) => {
  const displayName = contact.attention || `Contact #${contact.contact_id}`;

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
        className={`text-sm p-2 rounded ${
          isEditing && onEdit
            ? "cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800"
            : ""
        }`}
        onClick={isEditing && onEdit ? onEdit : undefined}
      >
        <div className="font-medium text-slate-800 dark:text-slate-200 flex items-center gap-2 justify-between">
          <div className="flex items-center gap-2">
            <FaUser size={12} className="text-slate-400" />
            {displayName}
          </div>
          {isEditing && onEdit && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onEdit();
              }}
              className="p-1 text-slate-400 hover:text-blue-500 transition-colors"
              title="Edit contact"
            >
              <FaEdit size={12} />
            </button>
          )}
        </div>

        <div className="flex flex-wrap gap-4 ml-5 mt-2 text-slate-500 dark:text-slate-400">
          {contact.email && (
            <span className="flex items-center gap-1 text-xs">
              <FaEnvelope size={10} />
              <a
                href={`mailto:${contact.email}`}
                className="hover:text-blue-500"
              >
                {contact.email}
              </a>
            </span>
          )}
          {contact.phone && (
            <span className="flex items-center gap-1 text-xs">
              <FaPhone size={10} />
              <a href={`tel:${contact.phone}`} className="hover:text-blue-500">
                {contact.phone}
              </a>
            </span>
          )}
        </div>

        {contact.full && (
          <div className="mt-2 text-xs text-slate-600 dark:text-slate-400 ml-5 whitespace-pre-line">
            {contact.full}
          </div>
        )}

        {contact.domain && (
          <div className="mt-1 text-xs text-slate-600 dark:text-slate-400 ml-5">
            <a
              href={`https://${contact.domain}`}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-blue-500"
            >
              {contact.domain}
            </a>
          </div>
        )}
      </div>
    </div>
  );
};

const PurposeSection: React.FC<{
  purpose: string;
  contacts: RefContact[];
  isEditing?: boolean;
  onAdd?: () => void;
  onRemove?: (contactId: number) => void;
  onEdit?: (contact: RefContact) => void;
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
              key={`${contact.contact_id}-${contact.purpose}`}
              contact={contact}
              isEditing={isEditing}
              onRemove={
                onRemove ? () => onRemove(contact.contact_id) : undefined
              }
              onEdit={onEdit ? () => onEdit(contact) : undefined}
            />
          ))
        ) : (
          <p className="text-sm text-slate-400 dark:text-slate-500 italic">
            No contact assigned
          </p>
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
  onChange,
}) => {
  const [editingContact, setEditingContact] = useState<RefContact | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const grouped = groupContactsByPurpose(contacts);

  // Get all unique purposes, with standard ones first
  const allPurposes = new Set([
    ...STANDARD_PURPOSES.filter((p) => grouped[p]?.length > 0 || isEditing),
    ...Object.keys(grouped).filter((p) => !STANDARD_PURPOSES.includes(p)),
  ]);

  const handleEditContact = (contact: RefContact) => {
    setEditingContact(contact);
    setIsModalOpen(true);
  };

  const handleSaveContact = (updatedContact: RefContact) => {
    if (onChange) {
      const newContacts = contacts.map((c) =>
        c.contact_id === updatedContact.contact_id ? updatedContact : c,
      );
      onChange(newContacts);
    }
    if (onEdit) {
      onEdit(updatedContact);
    }
  };

  const handleRemoveContact = (contactId: number) => {
    if (onChange) {
      onChange(contacts.filter((c) => c.contact_id !== contactId));
    }
    if (onRemove) {
      onRemove(contactId);
    }
  };

  if (allPurposes.size === 0 && !isEditing) {
    return (
      <div className="text-sm text-slate-500 dark:text-slate-400 italic">
        No contacts linked to this transaction
      </div>
    );
  }

  return (
    <>
      <ContactEditModal
        contact={editingContact}
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setEditingContact(null);
        }}
        onSave={handleSaveContact}
      />

      <div className="space-y-4">
        {Array.from(allPurposes).map((purpose) => (
          <PurposeSection
            key={purpose}
            purpose={purpose}
            contacts={grouped[purpose] || []}
            isEditing={isEditing}
            onAdd={onAdd ? () => onAdd(purpose as ContactPurpose) : undefined}
            onRemove={isEditing ? handleRemoveContact : undefined}
            onEdit={isEditing ? handleEditContact : undefined}
          />
        ))}
      </div>
    </>
  );
};

export default RefsLinksContactPanel;
