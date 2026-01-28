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

  // Support multiple emails, phones, domains, addresses
  type MultiContact = Omit<
    RefContact,
    "email" | "phone" | "domain" | "full"
  > & {
    email?: string[];
    phone?: string[];
    domain?: string[];
    full?: string[];
  };
  const toMulti = (c: RefContact | null): MultiContact => ({
    ...c,
    email: c?.email ? [c.email] : [""],
    phone: c?.phone ? [c.phone] : [""],
    domain: c?.domain ? [c.domain] : [""],
    full: c?.full ? [c.full] : [""],
  });
  const fromMulti = (m: MultiContact): RefContact => ({
    ...m,
    email: m.email?.filter(Boolean).join(", "),
    phone: m.phone?.filter(Boolean).join(", "),
    domain: m.domain?.filter(Boolean).join(", "),
    full: m.full?.filter(Boolean).join("\n"),
  });
  const [formData, setFormData] = useState<MultiContact>(toMulti(contact));
  React.useEffect(() => {
    setFormData(toMulti(contact));
  }, [contact]);

  if (!isOpen || !contact) return null;

  const handleChange = (
    field: keyof MultiContact,
    value: string | string[],
    idx?: number,
  ) => {
    if (["email", "phone", "domain", "full"].includes(field)) {
      setFormData((prev) => {
        const arr = Array.isArray(prev[field])
          ? [...(prev[field] as string[])]
          : [""];
        if (typeof idx === "number") {
          arr[idx] = value as string;
        }
        return { ...prev, [field]: arr };
      });
    } else {
      setFormData((prev) => ({ ...prev, [field]: value }));
    }
  };

  const handleAddField = (field: keyof MultiContact) => {
    setFormData((prev) => ({
      ...prev,
      [field]: [...(prev[field] as string[]), ""],
    }));
  };

  const handleRemoveField = (field: keyof MultiContact, idx: number) => {
    setFormData((prev) => {
      const arr = Array.isArray(prev[field])
        ? [...(prev[field] as string[])]
        : [];
      arr.splice(idx, 1);
      return { ...prev, [field]: arr.length ? arr : [""] };
    });
  };

  return (
    <div className="pointer-events-none fixed inset-0 z-[200000] flex items-stretch justify-end">
      <div className="pointer-events-auto ml-auto flex h-full w-full max-h-screen flex-col overflow-hidden border-l border-blue-200 dark:border-blue-800 bg-white dark:bg-slate-800 shadow-2xl no-scrollbar sm:w-[480px] lg:w-[33vw] lg:min-w-[360px]">
        <div className="flex items-start justify-between border-b border-blue-200 dark:border-blue-800 px-5 py-4">
          <div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
              Edit Contact
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800"
            aria-label="Close panel"
          >
            <svg
              className="h-5 w-5"
              viewBox="0 0 20 20"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M6 6l8 8M14 6l-8 8"
                stroke="currentColor"
                strokeWidth={1.6}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 pb-6 pt-4 space-y-4">
          <div>
            <div className="flex-1 items-center gap-1 mb-1">
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                Purpose
              </label>
              <select
                value={formData.purpose}
                onChange={(e) => handleChange("purpose", e.target.value)}
                className="w-full px-3 py-2 text-xs border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
              >
                <option value="">-- Select Purpose --</option>
                {STANDARD_PURPOSES.map((p) => (
                  <option key={p} value={p}>
                    {formatPurpose(p)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <div className="flex-1 items-center gap-1 mb-1">
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                Attention
              </label>
              <input
                type="text"
                value={formData.attention || ""}
                onChange={(e) => handleChange("attention", e.target.value)}
                placeholder="Contact name"
                className="w-full px-3 py-2 text-xs border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
              />
            </div>
          </div>

          {/* Multi Email */}
          <div>
            <div className="flex items-center gap-1 mb-1">
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                Email
              </label>
              <button
                type="button"
                onClick={() => handleAddField("email")}
                className="text-xs text-blue-500 hover:text-blue-600"
              >
                + Add Email
              </button>
            </div>
            {formData.email?.map((email, idx) => (
              <div key={idx} className="flex gap-1 mb-1">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => handleChange("email", e.target.value, idx)}
                  placeholder="email@example.com"
                  className="w-full px-3 py-2 text-xs border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
                {(formData.email?.length ?? 0) > 1 && (
                  <button
                    type="button"
                    onClick={() => handleRemoveField("email", idx)}
                    className="text-red-500 px-2"
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Multi Phone */}
          <div>
            <div className="flex items-center gap-1 mb-1">
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                Phone
              </label>
              <button
                type="button"
                onClick={() => handleAddField("phone")}
                className="text-xs text-blue-500 hover:text-blue-600"
              >
                + Add Phone
              </button>
            </div>
            {formData.phone?.map((phone, idx) => (
              <div key={idx} className="flex gap-1 mb-1">
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => handleChange("phone", e.target.value, idx)}
                  placeholder="123-456-7890"
                  className="w-full px-3 py-2 text-xs border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
                {(formData.phone?.length ?? 0) > 1 && (
                  <button
                    type="button"
                    onClick={() => handleRemoveField("phone", idx)}
                    className="text-red-500 px-2"
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Multi Domain */}
          <div>
            <div className="flex items-center gap-1 mb-1">
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                Domain
              </label>
              <button
                type="button"
                onClick={() => handleAddField("domain")}
                className="text-xs text-blue-500 hover:text-blue-600"
              >
                + Add Domain
              </button>
            </div>
            {formData.domain?.map((domain, idx) => (
              <div key={idx} className="flex gap-1 mb-1">
                <input
                  type="url"
                  value={domain}
                  onChange={(e) => handleChange("domain", e.target.value, idx)}
                  placeholder="www.example.com"
                  className="w-full px-3 py-2 text-xs border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
                {(formData.domain?.length ?? 0) > 1 && (
                  <button
                    type="button"
                    onClick={() => handleRemoveField("domain", idx)}
                    className="text-red-500 px-2"
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Multi Address */}
          <div>
            <div className="flex items-center gap-1 mb-1">
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                Address
              </label>
              <button
                type="button"
                onClick={() => handleAddField("full")}
                className="text-xs text-blue-500 hover:text-blue-600"
              >
                + Add Address
              </button>
            </div>
            {formData.full?.map((full, idx) => (
              <div key={idx} className="flex gap-1 mb-1">
                <textarea
                  value={full}
                  onChange={(e) => handleChange("full", e.target.value, idx)}
                  placeholder="Street address, city, state, zip"
                  rows={3}
                  className="w-full px-3 py-2 text-xs border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
                {(formData.full?.length ?? 0) > 1 && (
                  <button
                    type="button"
                    onClick={() => handleRemoveField("full", idx)}
                    className="text-red-500 px-2"
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
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
              onSave(fromMulti(formData));
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
          isEditing && onEdit ? "cursor-pointer" : ""
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
  // Removed onAdd from props
  onRemove?: (contactId: number) => void;
  onEdit?: (contact: RefContact) => void;
}> = ({ purpose, contacts, isEditing, onRemove, onEdit }) => {
  return (
    <div className="border-b border-slate-200 dark:border-slate-700 pb-0 last:border-0 last:pb-0 bg-success-50 cus-bg-purple-light">
      <div className="flex items-center justify-between bg-success-200">
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide p-2">
          {formatPurpose(purpose)}
        </h4>
        {/* Removed individual Add button */}
      </div>
      <div className="bg-success-50 hover:bg-success-100 dark:hover:bg-success-100 transition-colors  min-h-[140px]">
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
          <p className="text-sm text-center text-slate-400 dark:text-slate-500 italic py-4">
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
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [addContactPurpose, setAddContactPurpose] = useState<string>("");

  const grouped = groupContactsByPurpose(contacts);

  // Get all unique purposes, with standard ones first
  const allPurposes = new Set([
    ...STANDARD_PURPOSES.filter((p) => grouped[p]?.length > 0 || isEditing),
    ...Object.keys(grouped).filter((p) => !STANDARD_PURPOSES.includes(p)),
  ]);

  // Generate a new unique contact_id (simple max+1)
  const getNextContactId = () => {
    return (
      (contacts.length > 0
        ? Math.max(...contacts.map((c) => c.contact_id || 0))
        : 0) + 1
    );
  };

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

  // Add new contact logic
  const handleAddContact = (purpose?: string) => {
    setAddContactPurpose(purpose || "");
    setIsAddModalOpen(true);
  };

  const handleSaveNewContact = (newContact: RefContact) => {
    const contactWithId = {
      ...newContact,
      contact_id: getNextContactId(),
    };
    if (onChange) {
      onChange([...contacts, contactWithId]);
    }
    if (onAdd) {
      onAdd(contactWithId.purpose);
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
      {/* Edit Contact Modal */}
      <ContactEditModal
        contact={editingContact}
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setEditingContact(null);
        }}
        onSave={handleSaveContact}
      />

      {/* Add Contact Modal (blank form) */}
      <ContactEditModal
        contact={
          isAddModalOpen
            ? {
                contact_id: 0,
                purpose: addContactPurpose,
                attention: "",
                email: "",
                phone: "",
                full: "",
                domain: "",
              }
            : null
        }
        isOpen={isAddModalOpen}
        onClose={() => {
          setIsAddModalOpen(false);
          setAddContactPurpose("");
        }}
        onSave={(c) => {
          handleSaveNewContact(c);
          setIsAddModalOpen(false);
          setAddContactPurpose("");
        }}
      />

      {/* Add Contact Section */}
      {isEditing && (
        <div className="flex justify-end mb-1 px-2">
          <button
            type="button"
            className="px-3 py-2 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700 transition-colors"
            onClick={() => handleAddContact()}
          >
            + Add New Contact
          </button>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 p-2 bg-gray-100 ">
        {Array.from(allPurposes).map((purpose) =>
          grouped[purpose] && grouped[purpose].length > 0 ? (
            <PurposeSection
              key={purpose}
              purpose={purpose}
              contacts={grouped[purpose]}
              isEditing={isEditing}
              onRemove={isEditing ? handleRemoveContact : undefined}
              onEdit={isEditing ? handleEditContact : undefined}
            />
          ) : null,
        )}
      </div>
    </>
  );
};

export default RefsLinksContactPanel;
