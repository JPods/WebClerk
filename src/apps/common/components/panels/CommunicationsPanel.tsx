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
import { saveRecord, deleteRecord } from "../../../../api/wcapi";
import { withDevIdentifier } from "@/components/common/DevIdentifier";

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

  /*
  Code here to get email by id

  */

  return (
    <div className="flex items-center gap-2 py-1.5 group hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded px-2 -mx-2">
      <FaEnvelope size={12} className="text-slate-400 shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-muted text-xs">{`(#${email.id})`}</span>
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
              type="button"
            >
              <FaRegStar size={10} />
            </button>
          )}
          {onEdit && (
            <button
              onClick={onEdit}
              className="p-1 text-slate-400 hover:text-blue-500"
              title="Edit"
              type="button"
            >
              <FaEdit size={10} />
            </button>
          )}
          {onDelete && (
            <button
              onClick={onDelete}
              className="p-1 text-slate-400 hover:text-red-500"
              title="Delete"
              type="button"
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
  const countryCode = phone.country_code || "";
  // Format: +CC (XXX) XXX-XXXX
  const formattedNumber = formatPhoneNumber(phoneNumber);
  const phoneDisplay = countryCode
    ? `${countryCode} ${formattedNumber}`
    : formattedNumber;

  return (
    <div className="flex items-center gap-2 py-1.5 group hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded px-2 -mx-2">
      <FaPhone size={12} className="text-slate-400 shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-muted text-xs">{`(#${phone.id})`}</span>
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
              type="button"
            >
              <FaRegStar size={10} />
            </button>
          )}
          {onEdit && (
            <button
              onClick={onEdit}
              className="p-1 text-slate-400 hover:text-blue-500"
              title="Edit"
              type="button"
            >
              <FaEdit size={10} />
            </button>
          )}
          {onDelete && (
            <button
              onClick={onDelete}
              className="p-1 text-slate-400 hover:text-red-500"
              title="Delete"
              type="button"
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
  const address_type = address.address_type;
  return (
    <div className="flex items-start gap-2 py-1.5 group hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded px-2 -mx-2">
      <FaMapMarkerAlt size={12} className="text-slate-400 shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-muted text-xs">{`(#${address.id})`}</span>
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
        {address_type && String(address_type).trim() ? (
          <p className="text-xs text-slate-400">
            {String(address_type).trim()}
          </p>
        ) : null}
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
                type="button"
              >
                <FaRegStar size={10} />
              </button>
            )}
            {onEdit && (
              <button
                onClick={onEdit}
                className="p-1 text-slate-400 hover:text-blue-500"
                title="Edit"
                type="button"
              >
                <FaEdit size={10} />
              </button>
            )}
            {onDelete && (
              <button
                onClick={onDelete}
                className="p-1 text-slate-400 hover:text-red-500"
                title="Delete"
                type="button"
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
          <span className="text-muted text-xs">{`(#${domain.id})`}</span>
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
              type="button"
            >
              <FaRegStar size={10} />
            </button>
          )}
          {onEdit && (
            <button
              onClick={onEdit}
              className="p-1 text-slate-400 hover:text-blue-500"
              title="Edit"
              type="button"
            >
              <FaEdit size={10} />
            </button>
          )}
          {onDelete && (
            <button
              onClick={onDelete}
              className="p-1 text-slate-400 hover:text-red-500"
              title="Delete"
              type="button"
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

/**
 * Format phone number as (123) 456-7890 international style
 * Strips non-digits, then formats with parentheses
 */
const formatPhoneNumber = (value: string): string => {
  const digits = value.replace(/\D/g, "").slice(0, 10);
  if (digits.length === 0) return "";
  if (digits.length <= 3) return `(${digits}`;
  if (digits.length <= 6) return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
  return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
};

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
                  Country Code
                </label>
                <input
                  type="text"
                  value={(formData.country_code as string) || ""}
                  onChange={(e) =>
                    setFormData({ ...formData, country_code: e.target.value })
                  }
                  placeholder="+1"
                  className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                  Number
                </label>
                <input
                  type="tel"
                  value={(formData.number as string) || ""}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      number: formatPhoneNumber(e.target.value),
                    })
                  }
                  placeholder="(123) 456-7890"
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
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                    address_type
                  </label>
                  <input
                    type="text"
                    value={(formData.address_type as string) || ""}
                    onChange={(e) =>
                      setFormData({ ...formData, address_type: e.target.value })
                    }
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
      // Get the item to delete
      let items: any[] = [];
      if (type === "email") {
        items = emails;
      } else if (type === "phone") {
        items = phones;
      } else if (type === "address") {
        items = addresses;
      } else if (type === "domain") {
        items = domains;
      }

      const itemToDelete = items[index];
      if (!itemToDelete?.id) {
        console.warn("[CommunicationsPanel] Item has no ID, cannot delete");
        return;
      }

      // ── Phase 1: Delete the record from the communication model ──
      console.log(
        `[CommunicationsPanel] Phase 1: Delete ${type} record ID ${itemToDelete.id}`,
      );
      await deleteRecord(type, itemToDelete.id);
      console.log(
        `[CommunicationsPanel] Phase 2: ${type} record deleted successfully`,
      );

      // ── Phase 2: Remove from contact's refs.links ──
      console.log(`[CommunicationsPanel] Phase 3: Updating contact refs.links`);
      const updatedArray = items.filter((_, i) => i !== index);

      // Build update payload with clean structure
      const updatePayload = {
        id: contactId,
        refs: {
          links: {
            [type]: updatedArray,
          },
        },
      };

      console.log(
        `[CommunicationsPanel] Phase 4: Saving contact refs.links update`,
        {
          type,
          itemsRemaining: updatedArray.length,
        },
      );
      await saveRecord("contact", updatePayload);
      console.log(
        `[CommunicationsPanel] Phase 5: Contact refs.links updated successfully`,
      );

      // ── Phase 3: Update local state ──
      const newData = { ...data };
      if (type === "email") newData.emails = updatedArray;
      else if (type === "phone") newData.phones = updatedArray;
      else if (type === "address") newData.addresses = updatedArray;
      else if (type === "domain") newData.domains = updatedArray;

      onChange(newData);
      console.log(`[CommunicationsPanel] Phase 6: Local state updated`);
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

      // Save to contact's communications JSON and refs.links.email
      await saveRecord("contact", {
        id: contactId,
        mode: "update",
        communications: {
          mode: "update",
          value: {
            emails: newEmails,
          },
        },
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
      // Save to contact's communications JSON and refs.links.phone
      await saveRecord("contact", {
        id: contactId,
        mode: "update",
        communications: {
          mode: "update",
          value: {
            phones: phones,
          },
        },
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
      // Save to contact's communications JSON and refs.links.address
      await saveRecord("contact", {
        id: contactId,
        mode: "update",
        communications: {
          mode: "update",
          value: {
            addresses: addresses,
          },
        },
        refs: {
          mode: "update",
          value: {
            links: {
              address: addresses,
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

      // Save to contact's communications JSON and refs.links.domain
      await saveRecord("contact", {
        id: contactId,
        mode: "update",
        communications: {
          mode: "update",
          value: {
            domains: newDomains,
          },
        },
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

      console.log("[CommunicationsPanel] handleSave Phase 1: Item from form:", {
        type,
        isEditMode: !!item.id && item.id > 0,
        item,
      });

      // ── Phase 1: Create or update the communication record (email/phone/address/domain) ──
      let newItem = { ...item };
      let savedId: number;

      if (index !== undefined && newItem.id && newItem.id > 0) {
        // EDIT MODE: Update existing record
        console.log("[CommunicationsPanel] Phase 2a: Update existing record");
        const payload: Record<string, any> = {
          id: newItem.id,
          contact_id: contactId,
        };
        if (type === "email") {
          payload.email = String(newItem.email || "")
            .trim()
            .toLowerCase();
          payload.name = String(newItem.name || "").trim();
          payload.is_primary = !!(newItem as EmailLink).is_primary;
          payload.is_verified = !!(newItem as EmailLink).is_verified;
        } else if (type === "phone") {
          payload.number = String(newItem.number || "").trim();
          payload.name = String(newItem.name || "").trim();
          payload.country_code = String(
            (newItem as PhoneLink).country_code || "",
          ).trim();
          payload.format = String((newItem as PhoneLink).format || "").trim();
        } else if (type === "address") {
          payload.address1 = String(newItem.address1 || "").trim();
          payload.address2 = String(
            (newItem as AddressLink).address2 || "",
          ).trim();
          payload.city = String((newItem as AddressLink).city || "").trim();
          payload.state = String((newItem as AddressLink).state || "").trim();
          payload.zip = String((newItem as AddressLink).zip || "").trim();
          payload.country = String(
            (newItem as AddressLink).country || "",
          ).trim();
          payload.address_type = String(
            (newItem as AddressLink).address_type || "",
          ).trim();
        } else if (type === "domain") {
          payload.path = String(newItem.domain || "")
            .trim()
            .toLowerCase();
          payload.domain = payload.path;
          payload.type = String(
            (newItem as DomainLink).name || "website",
          ).trim();
        }

        const updateResult: any = await saveRecord(type, payload);
        const record = updateResult?.record ?? updateResult;
        savedId = Number(record?.id ?? updateResult?.id);
        newItem = record || { ...newItem, id: savedId };
      } else {
        // CREATE MODE: Create new record
        console.log("[CommunicationsPanel] Phase 2b: Create new record");
        const payload: Record<string, any> = { contact_id: contactId };

        if (type === "email") {
          payload.email = String(newItem.email || "")
            .trim()
            .toLowerCase();
          payload.name = String(newItem.name || "").trim();
          payload.is_primary = !!(newItem as EmailLink).is_primary;
          payload.is_verified = !!(newItem as EmailLink).is_verified;
        } else if (type === "phone") {
          payload.number = String(newItem.number || "").trim();
          payload.name = String(newItem.name || "").trim();
          payload.country_code = String(
            (newItem as PhoneLink).country_code || "",
          ).trim();
          payload.format = String((newItem as PhoneLink).format || "").trim();
        } else if (type === "address") {
          payload.address1 = String(newItem.address1 || "").trim();
          payload.address2 = String(
            (newItem as AddressLink).address2 || "",
          ).trim();
          payload.city = String((newItem as AddressLink).city || "").trim();
          payload.state = String((newItem as AddressLink).state || "").trim();
          payload.zip = String((newItem as AddressLink).zip || "").trim();
          payload.country = String(
            (newItem as AddressLink).country || "",
          ).trim();
          payload.address_type = String(
            (newItem as AddressLink).address_type || "",
          ).trim();
        } else if (type === "domain") {
          payload.path = String(newItem.domain || "")
            .trim()
            .toLowerCase();
          payload.domain = payload.path;
          payload.type = String(
            (newItem as DomainLink).name || "website",
          ).trim();
        }

        const createResult: any = await saveRecord(type, payload);
        const record = createResult?.record ?? createResult;
        savedId = Number(record?.id ?? createResult?.id);

        if (!Number.isFinite(savedId) || savedId <= 0) {
          throw new Error(
            `Failed to create ${type} record. Backend returned: ${JSON.stringify(
              {
                savedId,
                record,
                createResult,
              },
            )}`,
          );
        }

        newItem = {
          ...(record || newItem),
          id: savedId,
        };
      }

      console.log("[CommunicationsPanel] Phase 3: Successfully saved record:", {
        type,
        savedId,
        newItem,
      });

      // ── Phase 2: Build the updated refs.links array with the real record ──
      let updatedArray: any[];

      if (type === "email") {
        updatedArray = [...emails];
        const newEmail: EmailLink = {
          id: savedId,
          email: String(newItem.email || "")
            .trim()
            .toLowerCase(),
          name: String(newItem.name || "").trim(),
          type: String((newItem as any).type || "").trim(),
          is_primary: !!(newItem as EmailLink).is_primary,
          is_verified: !!(newItem as EmailLink).is_verified,
        };
        if (index !== undefined) {
          updatedArray[index] = newEmail;
        } else {
          updatedArray.push(newEmail);
        }
        // Ensure only one email is primary
        if (newEmail.is_primary) {
          const primaryIndex =
            index !== undefined ? index : updatedArray.length - 1;
          updatedArray = updatedArray.map((e, i) => ({
            ...e,
            is_primary: i === primaryIndex,
          }));
        }
      } else if (type === "phone") {
        updatedArray = [...phones];
        const newPhone: PhoneLink = {
          id: savedId,
          number: String(newItem.number || "").trim(),
          name: String(newItem.name || "").trim(),
          country_code: String(
            (newItem as PhoneLink).country_code || "",
          ).trim(),
          format: String((newItem as PhoneLink).format || "").trim(),
        };
        if (index !== undefined) {
          updatedArray[index] = newPhone;
        } else {
          updatedArray.push(newPhone);
        }
      } else if (type === "address") {
        updatedArray = [...addresses];
        const addr1 = String(newItem.address1 || "").trim();
        const addr2 = String((newItem as AddressLink).address2 || "").trim();
        const city = String((newItem as AddressLink).city || "").trim();
        const state = String((newItem as AddressLink).state || "").trim();
        const zip = String((newItem as AddressLink).zip || "").trim();
        const country = String((newItem as AddressLink).country || "").trim();
        const address_type = String(
          (newItem as AddressLink).address_type || "",
        ).trim();

        const fullAddress = [
          addr1,
          [city, state, zip].filter(Boolean).join(", "),
          country,
        ]
          .filter(Boolean)
          .join(", ");

        const newAddress: AddressLink = {
          id: savedId,
          address1: addr1,
          address2: addr2,
          city,
          state,
          zip,
          country,
          full: fullAddress,
          name: String((newItem as any).name || "").trim(),
          address_type: address_type,
        };
        if (index !== undefined) {
          updatedArray[index] = newAddress;
        } else {
          updatedArray.push(newAddress);
        }
      } else if (type === "domain") {
        updatedArray = [...domains];
        const newDomain: DomainLink = {
          id: savedId,
          domain: String(newItem.domain || newItem.path || "")
            .trim()
            .toLowerCase(),
          path: String(newItem.path || newItem.domain || "")
            .trim()
            .toLowerCase(),
          name: String((newItem as DomainLink).name || "").trim(),
          is_primary: !!(newItem as DomainLink).is_primary,
        };
        if (index !== undefined) {
          updatedArray[index] = newDomain;
        } else {
          updatedArray.push(newDomain);
        }
        // Ensure only one domain is primary
        if (newDomain.is_primary) {
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

      console.log("[CommunicationsPanel] Phase 4: Updated refs.links array:", {
        type,
        count: updatedArray.length,
        updatedArray,
      });

      // ── Phase 3: Update contact's refs.links and communications arrays ──
      const linksKey = type;

      const result = await saveRecord("contact", {
        id: contactId,
        mode: "update",
        communications: {
          mode: "update",
          value: {
            [linksKey]: updatedArray,
          },
        },
        refs: {
          mode: "update",
          value: {
            links: {
              [linksKey]: updatedArray,
            },
          },
        },
      });
      console.log(
        "[CommunicationsPanel] Phase 5: Successfully updated contact.refs.links:",
        {
          type,
          result,
        },
      );

      // ── Phase 4: Update local state ──
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

      console.log(
        "[CommunicationsPanel] Phase 6: Complete - record saved with real ID:",
        {
          type,
          recordId: savedId,
        },
      );
    } catch (err) {
      console.error(`[CommunicationsPanel] Failed to save ${type}:`, err);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div
      className={`bg-white overflow-y-auto max-h-[360px] dark:bg-slate-800 rounded-lg border border-teal-200 dark:border-teal-800 ${className}`}
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
                      type="button"
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
                      type="button"
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
                      type="button"
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
                      type="button"
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
                      key={`${domain.id ?? domain.domain ?? "domain"}-${idx}`}
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

export default withDevIdentifier(
  CommunicationsPanel,
  "CommunicationsPanel",
  "teal",
);
