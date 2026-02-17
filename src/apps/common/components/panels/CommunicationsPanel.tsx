/**
 * CommunicationsPanel - Manage emails, phones, addresses, and domains linked to an entity
 *
 * This panel makes its own API calls to create/update/delete records via wcapi.
 * On successful API response (200), it calls onChange to update the parent's local state.
 *
 * Data sources:
 * - refs.links.email: [{id, email, name, type, is_primary}]
 * - refs.links.phone: [{id, number, format, name}]
 * - refs.links.address: [{id, address1, city, state, zip, country, full}]
 * - refs.links.domain: [{id, domain, name, is_primary}]
 *
 * Role-based access:
 * - View: All roles (default)
 * - Edit: User+ roles (default)
 */
import React, { useState } from "react";
import { createPortal } from "react-dom";
import {
  FaEnvelope,
  FaPhone,
  FaMapMarkerAlt,
  FaChevronDown,
  FaChevronUp,
  FaPlus,
  FaEdit,
  FaTrash,
  FaStar,
  FaRegStar,
  FaExternalLinkAlt,
  FaGlobe,
  FaSpinner,
} from "react-icons/fa";
import { usePermissions } from "./usePermissions";
import type {
  BasePanelProps,
  EmailLink,
  PhoneLink,
  AddressLink,
  DomainLink,
} from "./types";

// WCAPI for save/delete operations
import { saveRecord } from "../../../../api/wcapi";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CommunicationsData {
  emails?: EmailLink[];
  phones?: PhoneLink[];
  addresses?: AddressLink[];
  domains?: DomainLink[];
}

interface CommunicationsPanelProps
  extends Omit<BasePanelProps<CommunicationsData>, "data"> {
  /** Communications data */
  data?: CommunicationsData;
  /** Contact ID to link new records to */
  contactId?: number;
  /** Show only specific types */
  showTypes?: ("email" | "phone" | "address" | "domain")[];
  /** Primary record IDs from the parent contact record */
  primaryEmailId?: number | null;
  primaryPhoneId?: number | null;
  primaryAddressId?: number | null;
  primaryDomainId?: number | null;
  /** Callback when a record is set as primary – receives the type and the record id */
  onSetPrimaryItem?: (
    type: "email" | "phone" | "address" | "domain",
    id: number,
  ) => void;
}

// ---------------------------------------------------------------------------
// Sub-components for each type
// ---------------------------------------------------------------------------

interface EmailItemProps {
  email: EmailLink;
  canEdit: boolean;
  onSetPrimary?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
}

const EmailItem: React.FC<EmailItemProps> = ({
  email,
  canEdit,
  onSetPrimary,
  onEdit,
  onDelete,
}) => {
  // Try multiple field names: email, value, address
  const emailValue = email.email || email.value || email.address || "";

  return (
    <div className="flex items-center gap-2 py-1.5 group hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded px-2 -mx-2">
      <FaEnvelope size={12} className="text-slate-400 shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <a
            href={`mailto:${emailValue}`}
            className="text-sm text-blue-600 hover:underline truncate"
          >
            {emailValue}
          </a>
          {email.is_primary && (
            <FaStar size={10} className="text-amber-400" title="Primary" />
          )}
        </div>
        {(email.name || email.type) && (
          <p className="text-xs text-slate-400">
            {[email.name, email.type].filter(Boolean).join(" • ")}
          </p>
        )}
      </div>
      {canEdit && (
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {!email.is_primary && onSetPrimary && (
            <button
              onClick={onSetPrimary}
              className="p-1 text-slate-400 hover:text-amber-500"
              title="Set primary"
            >
              <FaRegStar size={10} />
            </button>
          )}
          {onEdit && (
            <button
              onClick={onEdit}
              className="p-1 text-slate-400 hover:text-blue-500"
              title="Edit"
            >
              <FaEdit size={10} />
            </button>
          )}
          {onDelete && (
            <button
              onClick={onDelete}
              className="p-1 text-slate-400 hover:text-red-500"
              title="Delete"
            >
              <FaTrash size={10} />
            </button>
          )}
        </div>
      )}
    </div>
  );
};

interface PhoneItemProps {
  phone: PhoneLink;
  canEdit: boolean;
  isPrimary?: boolean;
  onSetPrimary?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
}

const PhoneItem: React.FC<PhoneItemProps> = ({
  phone,
  canEdit,
  isPrimary,
  onSetPrimary,
  onEdit,
  onDelete,
}) => {
  // Try multiple field names: number, value, format
  const phoneNumber = phone.number || (phone as any).value || "";
  const phoneDisplay = phone.format || phoneNumber;

  return (
    <div className="flex items-center gap-2 py-1.5 group hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded px-2 -mx-2">
      <FaPhone size={12} className="text-slate-400 shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <a
            href={`tel:${phoneNumber}`}
            className="text-sm text-blue-600 hover:underline"
          >
            {phoneDisplay}
          </a>
          {isPrimary && (
            <FaStar size={10} className="text-amber-400" title="Primary" />
          )}
        </div>
        {phone.name && <p className="text-xs text-slate-400">{phone.name}</p>}
      </div>
      {canEdit && (
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {!isPrimary && onSetPrimary && (
            <button
              onClick={onSetPrimary}
              className="p-1 text-slate-400 hover:text-amber-500"
              title="Set primary"
            >
              <FaRegStar size={10} />
            </button>
          )}
          {onEdit && (
            <button
              onClick={onEdit}
              className="p-1 text-slate-400 hover:text-blue-500"
              title="Edit"
            >
              <FaEdit size={10} />
            </button>
          )}
          {onDelete && (
            <button
              onClick={onDelete}
              className="p-1 text-slate-400 hover:text-red-500"
              title="Delete"
            >
              <FaTrash size={10} />
            </button>
          )}
        </div>
      )}
    </div>
  );
};

interface AddressItemProps {
  address: AddressLink;
  canEdit: boolean;
  isPrimary?: boolean;
  onSetPrimary?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
}

const AddressItem: React.FC<AddressItemProps> = ({
  address,
  canEdit,
  isPrimary,
  onSetPrimary,
  onEdit,
  onDelete,
}) => {
  const fullAddress =
    address.full ||
    [
      address.address1,
      [address.city, address.state, address.zip].filter(Boolean).join(", "),
      address.country,
    ]
      .filter(Boolean)
      .join(", ");

  const mapsUrl = `https://maps.google.com/?q=${encodeURIComponent(
    fullAddress,
  )}`;

  return (
    <div className="flex items-start gap-2 py-1.5 group hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded px-2 -mx-2">
      <FaMapMarkerAlt size={12} className="text-slate-400 shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm text-slate-700 dark:text-slate-300">
            {address.address1}
          </p>
          {isPrimary && (
            <FaStar
              size={10}
              className="text-amber-400 shrink-0"
              title="Primary"
            />
          )}
        </div>
        <p className="text-xs text-slate-500">
          {[address.city, address.state, address.zip]
            .filter(Boolean)
            .join(", ")}
        </p>
        {address.country && address.country !== "US" && (
          <p className="text-xs text-slate-400">{address.country}</p>
        )}
      </div>
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <a
          href={mapsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="p-1 text-slate-400 hover:text-blue-500"
          title="Open in Maps"
        >
          <FaExternalLinkAlt size={10} />
        </a>
        {canEdit && (
          <>
            {!isPrimary && onSetPrimary && (
              <button
                onClick={onSetPrimary}
                className="p-1 text-slate-400 hover:text-amber-500"
                title="Set primary"
              >
                <FaRegStar size={10} />
              </button>
            )}
            {onEdit && (
              <button
                onClick={onEdit}
                className="p-1 text-slate-400 hover:text-blue-500"
                title="Edit"
              >
                <FaEdit size={10} />
              </button>
            )}
            {onDelete && (
              <button
                onClick={onDelete}
                className="p-1 text-slate-400 hover:text-red-500"
                title="Delete"
              >
                <FaTrash size={10} />
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Domain Item
// ---------------------------------------------------------------------------
interface DomainItemProps {
  domain: DomainLink;
  canEdit: boolean;
  onSetPrimary?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
}

const DomainItem: React.FC<DomainItemProps> = ({
  domain,
  canEdit,
  onSetPrimary,
  onEdit,
  onDelete,
}) => {
  // Try multiple field names: domain, value
  const domainValue = domain.domain || (domain as any).value || "";

  return (
    <div className="flex items-center gap-2 py-1.5 group hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded px-2 -mx-2">
      <FaGlobe size={12} className="text-slate-400 shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <a
            href={`https://${domainValue}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-600 hover:underline truncate"
          >
            {domainValue}
          </a>
          {domain.is_primary && (
            <FaStar size={10} className="text-amber-400" title="Primary" />
          )}
          {domain.verified && <span className="text-xs text-green-500">✓</span>}
        </div>
        {domain.name && <p className="text-xs text-slate-400">{domain.name}</p>}
      </div>
      {canEdit && (
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {!domain.is_primary && onSetPrimary && (
            <button
              onClick={onSetPrimary}
              className="p-1 text-slate-400 hover:text-amber-500"
              title="Set primary"
            >
              <FaRegStar size={10} />
            </button>
          )}
          {onEdit && (
            <button
              onClick={onEdit}
              className="p-1 text-slate-400 hover:text-blue-500"
              title="Edit"
            >
              <FaEdit size={10} />
            </button>
          )}
          {onDelete && (
            <button
              onClick={onDelete}
              className="p-1 text-slate-400 hover:text-red-500"
              title="Delete"
            >
              <FaTrash size={10} />
            </button>
          )}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Add/Edit Modals
// ---------------------------------------------------------------------------

interface AddEditModalProps {
  isOpen: boolean;
  type: "email" | "phone" | "address" | "domain";
  data?: EmailLink | PhoneLink | AddressLink | DomainLink;
  onClose: () => void;
  onSave: (data: EmailLink | PhoneLink | AddressLink | DomainLink) => void;
  isSaving?: boolean;
  contactId?: number; // Debug: show which contact we're linking to
}

const AddEditModal: React.FC<AddEditModalProps> = ({
  isOpen,
  type,
  data,
  onClose,
  onSave,
  isSaving = false,
  contactId,
}) => {
  const [formData, setFormData] = useState<Record<string, string | boolean>>(
    {},
  );

  React.useEffect(() => {
    if (data) {
      // Normalize field names from backend to form field names
      const normalized: Record<string, string | boolean> = {
        ...data,
      } as Record<string, string | boolean>;
      if (type === "email") {
        // Backend may use "value" or "address" instead of "email"
        normalized.email =
          (data as any).email ||
          (data as any).value ||
          (data as any).address ||
          "";
      } else if (type === "phone") {
        // Backend may use "value" instead of "number"
        normalized.number = (data as any).number || (data as any).value || "";
      } else if (type === "domain") {
        // Backend may use "value" instead of "domain"
        normalized.domain = (data as any).domain || (data as any).value || "";
      }
      setFormData(normalized);
    } else {
      setFormData({});
    }
  }, [data, isOpen, type]);

  if (!isOpen) return null;

  // Handle click on overlay to prevent propagation
  const handleOverlayClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onClose();
  };

  const handleModalClick = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent clicks inside modal from closing it
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    e.stopPropagation(); // Prevent bubbling to parent form
    // Don't include Date.now() as id - let the backend assign it
    const payload = data?.id ? { id: data.id, ...formData } : { ...formData };
    onSave(payload as EmailLink | PhoneLink | AddressLink | DomainLink);
    // Note: onClose is called by handleSave on success
  };

  // Use portal to render modal outside the parent form
  return createPortal(
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={handleOverlayClick}
    >
      <div
        className="bg-white dark:bg-slate-800 rounded-lg p-4 w-80 max-w-full mx-4"
        onClick={handleModalClick}
      >
        <h3 className="text-sm font-semibold mb-2 text-slate-700 dark:text-slate-200 capitalize">
          {data ? "Edit" : "Add"} {type}
        </h3>
        <p className="text-xs text-slate-500 mb-4">
          Contact ID:{" "}
          <strong className="text-blue-600">{contactId ?? "NOT SET"}</strong>
        </p>

        <form onSubmit={handleSubmit} className="space-y-3">
          {type === "email" && (
            <>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                  Email
                </label>
                <input
                  type="email"
                  value={(formData.email as string) || ""}
                  onChange={(e) =>
                    setFormData({ ...formData, email: e.target.value })
                  }
                  className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  required
                />
              </div>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                  Label
                </label>
                <input
                  type="text"
                  value={(formData.name as string) || ""}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  placeholder="Work, Personal, etc."
                  className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={(formData.is_primary as boolean) || false}
                  onChange={(e) =>
                    setFormData({ ...formData, is_primary: e.target.checked })
                  }
                />
                Primary email
              </label>
            </>
          )}

          {type === "phone" && (
            <>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                  Number
                </label>
                <input
                  type="tel"
                  value={(formData.number as string) || ""}
                  onChange={(e) =>
                    setFormData({ ...formData, number: e.target.value })
                  }
                  className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  required
                />
              </div>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                  Label
                </label>
                <input
                  type="text"
                  value={(formData.name as string) || ""}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  placeholder="Mobile, Office, etc."
                  className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                />
              </div>
            </>
          )}

          {type === "address" && (
            <>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                  Street Address
                </label>
                <input
                  type="text"
                  value={(formData.address1 as string) || ""}
                  onChange={(e) =>
                    setFormData({ ...formData, address1: e.target.value })
                  }
                  className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                    City
                  </label>
                  <input
                    type="text"
                    value={(formData.city as string) || ""}
                    onChange={(e) =>
                      setFormData({ ...formData, city: e.target.value })
                    }
                    className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                    State
                  </label>
                  <input
                    type="text"
                    value={(formData.state as string) || ""}
                    onChange={(e) =>
                      setFormData({ ...formData, state: e.target.value })
                    }
                    className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                    Zip
                  </label>
                  <input
                    type="text"
                    value={(formData.zip as string) || ""}
                    onChange={(e) =>
                      setFormData({ ...formData, zip: e.target.value })
                    }
                    className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                    Country
                  </label>
                  <input
                    type="text"
                    value={(formData.country as string) || ""}
                    onChange={(e) =>
                      setFormData({ ...formData, country: e.target.value })
                    }
                    placeholder="US"
                    className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  />
                </div>
              </div>
            </>
          )}

          {type === "domain" && (
            <>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                  Domain
                </label>
                <input
                  type="text"
                  value={(formData.domain as string) || ""}
                  onChange={(e) =>
                    setFormData({ ...formData, domain: e.target.value })
                  }
                  placeholder="example.com"
                  className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  required
                />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={(formData.is_primary as boolean) || false}
                  onChange={(e) =>
                    setFormData({ ...formData, is_primary: e.target.checked })
                  }
                />
                Primary domain
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={(formData.verified as boolean) || false}
                  onChange={(e) =>
                    setFormData({ ...formData, verified: e.target.checked })
                  }
                />
                Verified
              </label>
            </>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSaving}
              className="px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700 rounded disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="px-3 py-1.5 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 flex items-center gap-1.5"
            >
              {isSaving && <FaSpinner className="animate-spin" size={12} />}
              {isSaving ? "Saving..." : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body,
  );
};

// ---------------------------------------------------------------------------
// Main CommunicationsPanel Component
// ---------------------------------------------------------------------------

const CommunicationsPanel: React.FC<CommunicationsPanelProps> = ({
  entityType: _entityType,
  entityId: _entityId,
  data = {},
  contactId,
  onChange,
  readOnly = false,
  viewRoles,
  editRoles,
  className = "",
  compact = false,
  title = "Communications Info",
  defaultCollapsed = false,
  showTypes = ["email", "phone", "address", "domain"],
  primaryEmailId: _primaryEmailId,
  primaryPhoneId,
  primaryAddressId,
  primaryDomainId: _primaryDomainId,
  onSetPrimaryItem,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [isSaving, setIsSaving] = useState(false);
  const [modalState, setModalState] = useState<{
    isOpen: boolean;
    type: "email" | "phone" | "address" | "domain";
    data?: EmailLink | PhoneLink | AddressLink | DomainLink;
    index?: number;
  }>({ isOpen: false, type: "email" });

  // Check permissions
  const { canView, canEdit: permCanEdit } = usePermissions({
    panelType: "communications",
    viewRoles,
    editRoles,
    forceReadOnly: readOnly,
  });

  const canEdit = permCanEdit && !!onChange;

  if (!canView) return null;

  const emails = data.emails || [];
  const phones = data.phones || [];
  const addresses = data.addresses || [];
  const domains = data.domains || [];

  const totalItems =
    emails.length + phones.length + addresses.length + domains.length;

  // Handlers
  const handleAdd = (type: "email" | "phone" | "address" | "domain") => {
    setModalState({ isOpen: true, type, data: undefined });
  };

  const handleEdit = (
    type: "email" | "phone" | "address" | "domain",
    item: EmailLink | PhoneLink | AddressLink | DomainLink,
    index: number,
  ) => {
    setModalState({ isOpen: true, type, data: item, index });
  };

  const handleDelete = async (
    type: "email" | "phone" | "address" | "domain",
    index: number,
  ) => {
    if (!onChange || !contactId) return;

    const ok = window.confirm(`Delete this ${type}? This cannot be undone.`);
    if (!ok) return;

    setIsSaving(true);
    try {
      // Build the updated array without the deleted item
      let updatedArray: any[];
      if (type === "email") {
        updatedArray = emails.filter((_, i) => i !== index);
      } else if (type === "phone") {
        updatedArray = phones.filter((_, i) => i !== index);
      } else if (type === "address") {
        updatedArray = addresses.filter((_, i) => i !== index);
      } else if (type === "domain") {
        updatedArray = domains.filter((_, i) => i !== index);
      } else {
        return;
      }

      // Map link type to refs.links key
      const linksKey = type;

      // Save to contact's refs.links.{type} via /wcapi/save/
      await saveRecord("contact", {
        id: contactId,
        mode: "update",
        refs: {
          mode: "update",
          value: {
            links: {
              [linksKey]: updatedArray,
            },
          },
        },
      });

      // Update local state
      const newData = { ...data };
      if (type === "email") newData.emails = updatedArray;
      else if (type === "phone") newData.phones = updatedArray;
      else if (type === "address") newData.addresses = updatedArray;
      else if (type === "domain") newData.domains = updatedArray;
      onChange(newData);
    } catch (err) {
      console.error(`Failed to delete ${type}:`, err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleSetPrimary = async (index: number) => {
    if (!onChange || !contactId) return;
    const emailToUpdate = emails[index];

    setIsSaving(true);
    try {
      // Update all emails - mark selected as primary, others as not primary
      const newEmails = emails.map((e, i) => ({
        ...e,
        is_primary: i === index,
      }));

      // Save to contact's refs.links.email
      await saveRecord("contact", {
        id: contactId,
        mode: "update",
        refs: {
          mode: "update",
          value: {
            links: {
              email: newEmails,
            },
          },
        },
      });

      onChange({ ...data, emails: newEmails });
      // Notify parent to update contact.email_id
      if (onSetPrimaryItem && emailToUpdate.id) {
        onSetPrimaryItem("email", emailToUpdate.id);
      }
    } catch (err) {
      console.error("Failed to set primary email:", err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleSetPhonePrimary = async (index: number) => {
    if (!onChange || !contactId) return;
    const phoneToUpdate = phones[index];

    setIsSaving(true);
    try {
      // Save to contact's refs.links.phone
      await saveRecord("contact", {
        id: contactId,
        mode: "update",
        refs: {
          mode: "update",
          value: {
            links: {
              phone: phones,
            },
          },
        },
      });

      onChange({ ...data, phones: phones });
      // Notify parent to update contact.phone_id
      if (onSetPrimaryItem && phoneToUpdate.id) {
        onSetPrimaryItem("phone", phoneToUpdate.id);
      }
    } catch (err) {
      console.error("Failed to set primary phone:", err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleSetAddressPrimary = async (index: number) => {
    if (!onChange || !contactId) return;
    const addressToUpdate = addresses[index];

    setIsSaving(true);
    try {
      // Save to contact's refs.links.address
      await saveRecord("contact", {
        id: contactId,
        mode: "update",
        refs: {
          mode: "update",
          value: {
            links: {
              location: addresses,
            },
          },
        },
      });

      onChange({ ...data, addresses: addresses });
      // Notify parent to update contact.address_id
      if (onSetPrimaryItem && addressToUpdate.id) {
        onSetPrimaryItem("address", addressToUpdate.id);
      }
    } catch (err) {
      console.error("Failed to set primary address:", err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleSetDomainPrimary = async (index: number) => {
    if (!onChange || !contactId) return;
    const domainToUpdate = domains[index];

    setIsSaving(true);
    try {
      // Update all domains - mark selected as primary, others as not primary
      const newDomains = domains.map((d, i) => ({
        ...d,
        is_primary: i === index,
      }));

      // Save to contact's refs.links.domain
      await saveRecord("contact", {
        id: contactId,
        mode: "update",
        refs: {
          mode: "update",
          value: {
            links: {
              domain: newDomains,
            },
          },
        },
      });

      onChange({ ...data, domains: newDomains });
      // Notify parent to update contact.domain_id
      if (onSetPrimaryItem && domainToUpdate.id) {
        onSetPrimaryItem("domain", domainToUpdate.id);
      }
    } catch (err) {
      console.error("Failed to set primary domain:", err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleSave = async (
    item: EmailLink | PhoneLink | AddressLink | DomainLink,
  ) => {
    if (!onChange) return;
    const { type, index } = modalState;

    setIsSaving(true);
    try {
      if (!contactId) {
        console.warn("[CommunicationsPanel] No contactId provided!");
        return;
      }

      // Build the updated refs.links.{type} array
      // For edit: replace the item at index; for add: append new item
      let updatedArray: any[];
      const newItem = { ...item };
      // Ensure item has an id (use negative temp id for new items, backend will assign real id)
      if (!newItem.id) {
        newItem.id = -Date.now(); // Temp id for new items
      }

      if (type === "email") {
        updatedArray = [...emails];
        if (index !== undefined) updatedArray[index] = newItem as EmailLink;
        else updatedArray.push(newItem as EmailLink);
        // Ensure only one email is primary - clear others when this one is set as primary
        if ((newItem as EmailLink).is_primary) {
          const primaryIndex =
            index !== undefined ? index : updatedArray.length - 1;
          updatedArray = updatedArray.map((e, i) => ({
            ...e,
            is_primary: i === primaryIndex,
          }));
        }
      } else if (type === "phone") {
        updatedArray = [...phones];
        if (index !== undefined) updatedArray[index] = newItem as PhoneLink;
        else updatedArray.push(newItem as PhoneLink);
      } else if (type === "address") {
        updatedArray = [...addresses];
        if (index !== undefined) updatedArray[index] = newItem as AddressLink;
        else updatedArray.push(newItem as AddressLink);
      } else if (type === "domain") {
        updatedArray = [...domains];
        if (index !== undefined) updatedArray[index] = newItem as DomainLink;
        else updatedArray.push(newItem as DomainLink);
        // Ensure only one domain is primary - clear others when this one is set as primary
        if ((newItem as DomainLink).is_primary) {
          const primaryIndex =
            index !== undefined ? index : updatedArray.length - 1;
          updatedArray = updatedArray.map((d, i) => ({
            ...d,
            is_primary: i === primaryIndex,
          }));
        }
      } else {
        return;
      }

      // Map link type to refs.links key
      const linksKey = type;

      console.log("[CommunicationsPanel] handleSave:", {
        type,
        linksKey,
        contactId,
        updatedArray: JSON.stringify(updatedArray),
      });

      // Save to contact's refs.links.{type} - send refs field with nested structure
      const result = await saveRecord("contact", {
        id: contactId,
        mode: "update",
        refs: {
          mode: "update",
          value: {
            links: {
              [linksKey]: updatedArray,
            },
          },
        },
      });
      console.log("[CommunicationsPanel] saveRecord result:", result);

      // Update local state with the array we already built
      const newData = { ...data };
      if (type === "email") {
        newData.emails = updatedArray as EmailLink[];
      } else if (type === "phone") {
        newData.phones = updatedArray as PhoneLink[];
      } else if (type === "address") {
        newData.addresses = updatedArray as AddressLink[];
      } else if (type === "domain") {
        newData.domains = updatedArray as DomainLink[];
      }

      onChange(newData);
      setModalState({ ...modalState, isOpen: false });
    } catch (err) {
      console.error(`Failed to save ${type}:`, err);
      // Could show toast here
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div
      className={`bg-white dark:bg-slate-800 rounded-lg border border-teal-200 dark:border-teal-800 ${className}`}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-teal-50 dark:bg-teal-900/20 border-b border-teal-200 dark:border-teal-800 cursor-pointer rounded-t-lg"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaEnvelope className="text-teal-500" size={14} />
          <h3 className="text-sm font-semibold text-teal-700 dark:text-teal-300">
            {title}
          </h3>
          {totalItems > 0 && (
            <span className="px-1.5 py-0.5 text-xs bg-teal-100 dark:bg-teal-900 text-teal-600 dark:text-teal-300 rounded-full">
              {totalItems}
            </span>
          )}
          {isSaving && (
            <span className="ml-2 inline-flex items-center gap-1 text-xs text-teal-700 dark:text-teal-300">
              <FaSpinner className="animate-spin" size={11} />
              Saving...
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isCollapsed ? (
            <FaChevronDown size={12} />
          ) : (
            <FaChevronUp size={12} />
          )}
        </div>
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className={compact ? "p-2" : "p-4"}>
          {totalItems === 0 && (
            <div className="mb-3 rounded border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900/30 dark:text-slate-300">
              No contact information yet.
            </div>
          )}

          <div className="space-y-4">
            {/* Emails */}
            {showTypes.includes("email") && (
              <div>
                <div className="flex items-center justify-between mb-1">
                  <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Email
                    {emails.length > 0 && (
                      <span className="ml-2 text-[11px] text-slate-400">
                        ({emails.length})
                      </span>
                    )}
                  </h4>
                  {canEdit && (
                    <button
                      onClick={() => handleAdd("email")}
                      className="p-1 text-teal-600 hover:bg-teal-50 dark:hover:bg-teal-900/20 rounded"
                      aria-label="Add email"
                      title="Add email"
                    >
                      <FaPlus size={10} />
                    </button>
                  )}
                </div>
                {emails.length === 0 ? (
                  <div className="rounded border border-dashed border-slate-200 dark:border-slate-700 px-3 py-2 text-xs text-slate-500 dark:text-slate-400">
                    No emails
                  </div>
                ) : (
                  emails.map((email, idx) => (
                    <EmailItem
                      key={email.id || idx}
                      email={email}
                      canEdit={canEdit}
                      onSetPrimary={() => handleSetPrimary(idx)}
                      onEdit={() => handleEdit("email", email, idx)}
                      onDelete={() => handleDelete("email", idx)}
                    />
                  ))
                )}
              </div>
            )}

            {/* Phones */}
            {showTypes.includes("phone") && (
              <div>
                <div className="flex items-center justify-between mb-1">
                  <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Phone
                    {phones.length > 0 && (
                      <span className="ml-2 text-[11px] text-slate-400">
                        ({phones.length})
                      </span>
                    )}
                  </h4>
                  {canEdit && (
                    <button
                      onClick={() => handleAdd("phone")}
                      className="p-1 text-teal-600 hover:bg-teal-50 dark:hover:bg-teal-900/20 rounded"
                      aria-label="Add phone"
                      title="Add phone"
                    >
                      <FaPlus size={10} />
                    </button>
                  )}
                </div>
                {phones.length === 0 ? (
                  <div className="rounded border border-dashed border-slate-200 dark:border-slate-700 px-3 py-2 text-xs text-slate-500 dark:text-slate-400">
                    No phones
                  </div>
                ) : (
                  phones.map((phone, idx) => (
                    <PhoneItem
                      key={phone.id || idx}
                      phone={phone}
                      canEdit={canEdit}
                      isPrimary={
                        !!primaryPhoneId && phone.id === primaryPhoneId
                      }
                      onSetPrimary={() => handleSetPhonePrimary(idx)}
                      onEdit={() => handleEdit("phone", phone, idx)}
                      onDelete={() => handleDelete("phone", idx)}
                    />
                  ))
                )}
              </div>
            )}

            {/* Addresses */}
            {showTypes.includes("address") && (
              <div>
                <div className="flex items-center justify-between mb-1">
                  <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Address
                    {addresses.length > 0 && (
                      <span className="ml-2 text-[11px] text-slate-400">
                        ({addresses.length})
                      </span>
                    )}
                  </h4>
                  {canEdit && (
                    <button
                      onClick={() => handleAdd("address")}
                      className="p-1 text-teal-600 hover:bg-teal-50 dark:hover:bg-teal-900/20 rounded"
                      aria-label="Add address"
                      title="Add address"
                    >
                      <FaPlus size={10} />
                    </button>
                  )}
                </div>
                {addresses.length === 0 ? (
                  <div className="rounded border border-dashed border-slate-200 dark:border-slate-700 px-3 py-2 text-xs text-slate-500 dark:text-slate-400">
                    No addresses
                  </div>
                ) : (
                  addresses.map((addr, idx) => (
                    <AddressItem
                      key={addr.id || idx}
                      address={addr}
                      canEdit={canEdit}
                      isPrimary={
                        !!primaryAddressId && addr.id === primaryAddressId
                      }
                      onSetPrimary={() => handleSetAddressPrimary(idx)}
                      onEdit={() => handleEdit("address", addr, idx)}
                      onDelete={() => handleDelete("address", idx)}
                    />
                  ))
                )}
              </div>
            )}

            {/* Domains */}
            {showTypes.includes("domain") && (
              <div>
                <div className="flex items-center justify-between mb-1">
                  <h4 className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Domains
                    {domains.length > 0 && (
                      <span className="ml-2 text-[11px] text-slate-400">
                        ({domains.length})
                      </span>
                    )}
                  </h4>
                  {canEdit && (
                    <button
                      onClick={() => handleAdd("domain")}
                      className="p-1 text-teal-600 hover:bg-teal-50 dark:hover:bg-teal-900/20 rounded"
                      aria-label="Add domain"
                      title="Add domain"
                    >
                      <FaPlus size={10} />
                    </button>
                  )}
                </div>
                {domains.length === 0 ? (
                  <div className="rounded border border-dashed border-slate-200 dark:border-slate-700 px-3 py-2 text-xs text-slate-500 dark:text-slate-400">
                    No domains
                  </div>
                ) : (
                  domains.map((domain, idx) => (
                    <DomainItem
                      key={domain.domain || idx}
                      domain={domain}
                      canEdit={canEdit}
                      onSetPrimary={() => handleSetDomainPrimary(idx)}
                      onEdit={() => handleEdit("domain", domain, idx)}
                      onDelete={() => handleDelete("domain", idx)}
                    />
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modal */}
      <AddEditModal
        isOpen={modalState.isOpen}
        type={modalState.type}
        data={modalState.data}
        onClose={() => setModalState({ ...modalState, isOpen: false })}
        onSave={handleSave}
        isSaving={isSaving}
        contactId={contactId}
      />
    </div>
  );
};

export default CommunicationsPanel;
