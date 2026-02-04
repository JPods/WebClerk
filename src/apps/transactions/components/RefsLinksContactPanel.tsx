/**
 * RefsLinksContactPanel - Display contacts grouped by purpose with editing support
 * Syncs with refs.links.contact structure from API
 */
import React, { useState, useEffect, useCallback } from "react";
import { useWindowManager } from "@/context/WindowManagerContext";
import {
  FaUser,
  FaEnvelope,
  FaPhone,
  FaTimes,
  FaEdit,
  FaGlobe,
  FaMapMarkerAlt,
  FaPlus,
  FaSave,
  FaTrash,
  FaChevronDown,
  FaChevronRight,
  FaSpinner,
  FaExternalLinkAlt,
} from "react-icons/fa";
import type { ContactPurpose } from "../types/transactionTypes";
import { fetchContacts } from "@/apps/core/models/contact/services/contactApi";
import {
  createEmail,
  updateEmail,
  deleteEmail,
} from "@/apps/communications/models/email/services/emailApi";
import {
  createPhone,
  updatePhone,
  deletePhone,
} from "@/apps/communications/models/phone/services/phoneApi";
import {
  createAddress,
  updateAddress,
  deleteAddress,
} from "@/apps/communications/models/address/services/addressApi";
import {
  createDomain,
  updateDomain,
  deleteDomain,
} from "@/apps/communications/models/domain/services/domainApi";

// ------------------------------------
// Communication Record Types
// ------------------------------------
interface EmailRecord {
  id: number;
  address: string;
  name?: string;
  type?: string;
  is_primary?: boolean;
  is_verified?: boolean;
}

interface PhoneRecord {
  id: number;
  number: string;
  name?: string;
  type?: string;
  is_primary?: boolean;
}

interface AddressRecord {
  id: number;
  name?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  country?: string;
  type?: string;
  full?: string;
}

interface DomainRecord {
  id: number;
  domain: string;
  name?: string;
  is_primary?: boolean;
}

// ------------------------------------
// Communication Table Component
// ------------------------------------
interface CommunicationTableProps<T> {
  title: string;
  icon: React.ReactNode;
  data: T[];
  columns: {
    key: keyof T | string;
    label: string;
    render?: (item: T) => React.ReactNode;
  }[];
  onAdd: () => void;
  onEdit: (item: T) => void;
  onDelete: (item: T) => void;
  onSave: (item: T) => void;
  editingItem: T | null;
  onEditChange: (field: keyof T, value: any) => void;
  onCancelEdit: () => void;
  disabled?: boolean;
}

function CommunicationTable<T extends { id: number }>({
  title,
  icon,
  data,
  columns,
  onAdd,
  onEdit,
  onDelete,
  onSave,
  editingItem,
  onEditChange,
  onCancelEdit,
  disabled = false,
}: CommunicationTableProps<T>) {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <div className="border rounded-lg dark:border-slate-700 overflow-hidden mb-4">
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-2 bg-slate-50 dark:bg-slate-800 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <FaChevronDown className="text-slate-400 w-3 h-3" />
          ) : (
            <FaChevronRight className="text-slate-400 w-3 h-3" />
          )}
          {icon}
          <span className="font-semibold text-sm text-slate-700 dark:text-slate-200">
            {title}
          </span>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            ({data.length})
          </span>
        </div>
        {!disabled && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onAdd();
            }}
            className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-white bg-blue-500 rounded hover:bg-blue-600"
          >
            <FaPlus className="w-2 h-2" /> Add
          </button>
        )}
      </div>

      {/* Table Content */}
      {isExpanded && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-slate-100 dark:bg-slate-700">
              <tr>
                {columns.map((col) => (
                  <th
                    key={String(col.key)}
                    className="px-2 py-1 text-left text-xs font-medium text-slate-600 dark:text-slate-300 uppercase"
                  >
                    {col.label}
                  </th>
                ))}
                {!disabled && (
                  <th className="px-2 py-1 text-right text-xs font-medium text-slate-600 dark:text-slate-300 uppercase w-20">
                    Actions
                  </th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {data.length === 0 ? (
                <tr>
                  <td
                    colSpan={columns.length + 1}
                    className="px-2 py-4 text-center text-slate-400 dark:text-slate-500"
                  >
                    No records found
                  </td>
                </tr>
              ) : (
                data.map((item) => (
                  <tr
                    key={item.id}
                    className="hover:bg-slate-50 dark:hover:bg-slate-800/50"
                  >
                    {editingItem && editingItem.id === item.id ? (
                      // Editing row
                      <>
                        {columns.map((col) => (
                          <td key={String(col.key)} className="px-2 py-1">
                            <input
                              type="text"
                              value={String(
                                (editingItem as any)[col.key] ?? "",
                              )}
                              onChange={(e) =>
                                onEditChange(col.key as keyof T, e.target.value)
                              }
                              className="w-full px-2 py-1 text-xs border rounded dark:bg-slate-700 dark:border-slate-600 dark:text-white"
                            />
                          </td>
                        ))}
                        <td className="px-2 py-1 text-right">
                          <div className="flex justify-end gap-1">
                            <button
                              type="button"
                              onClick={() => onSave(editingItem)}
                              className="p-1 text-green-600 hover:text-green-700"
                              title="Save"
                            >
                              <FaSave className="w-3 h-3" />
                            </button>
                            <button
                              type="button"
                              onClick={onCancelEdit}
                              className="p-1 text-slate-500 hover:text-slate-700"
                              title="Cancel"
                            >
                              ✕
                            </button>
                          </div>
                        </td>
                      </>
                    ) : (
                      // View row
                      <>
                        {columns.map((col) => (
                          <td
                            key={String(col.key)}
                            className="px-2 py-1 text-slate-700 dark:text-slate-300"
                          >
                            {col.render
                              ? col.render(item)
                              : String((item as any)[col.key] ?? "--")}
                          </td>
                        ))}
                        {!disabled && (
                          <td className="px-2 py-1 text-right">
                            <div className="flex justify-end gap-1">
                              <button
                                type="button"
                                onClick={() => onEdit(item)}
                                className="p-1 text-blue-600 hover:text-blue-700"
                                title="Edit"
                              >
                                <FaEdit className="w-3 h-3" />
                              </button>
                              <button
                                type="button"
                                onClick={() => onDelete(item)}
                                className="p-1 text-red-600 hover:text-red-700"
                                title="Delete"
                              >
                                <FaTrash className="w-3 h-3" />
                              </button>
                            </div>
                          </td>
                        )}
                      </>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// API contact structure from refs.links.contact
export interface RefContact {
  contact_id: number;
  purpose: ContactPurpose | string;
  attention?: string;
  email?: string;
  phone?: string;
  full?: string;
  domain?: string;
  address?: any; // Added to fix compile error
}

// Helper to normalize refs.links.contact API data to RefContact[]
export function normalizeRefsLinksContact(apiContacts: any[]): RefContact[] {
  if (!Array.isArray(apiContacts)) return [];
  return apiContacts.map((c, idx) => {
    // Accept both {contact, purpose} and {purpose, ...fields} shapes
    let base = c;
    let purpose = c.purpose || "";
    // If nested contact, flatten
    if (c.contact && typeof c.contact === "object") {
      base = c.contact;
      purpose = c.purpose || base.purpose || "";
    }
    // Helper to extract and join all address full fields (newline separated)
    const extractAddressFull = (field: any) => {
      if (Array.isArray(field)) {
        return field
          .map((item) => {
            if (
              typeof item === "object" &&
              item !== null &&
              typeof item.full === "string"
            ) {
              return item.full;
            }
            return "";
          })
          .filter(Boolean)
          .join("\n");
      }
      if (
        typeof field === "object" &&
        field !== null &&
        typeof field.full === "string"
      ) {
        return field.full;
      }
      return typeof field === "string" ? field : "";
    };
    const attention = base.attention || undefined;
    const addressFull = extractAddressFull(base.address);
    let contact_id = base.id;
    if (contact_id === undefined || contact_id === null || contact_id === "") {
      contact_id = idx + 1;
    }
    // Helper to normalize contact fields to array of {id, name, value}
    const normalizeContactField = (field: any) => {
      if (Array.isArray(field)) {
        return field.map((item: any, idx: number) => {
          if (typeof item === "object" && item !== null) {
            return {
              id: item.id ?? idx,
              name: item.name ?? "",
              value: item.value ?? "",
            };
          }
          return {
            id: idx,
            name: "",
            value: item ?? "",
          };
        });
      }
      if (typeof field === "object" && field !== null) {
        return [
          {
            id: field.id ?? 0,
            name: field.name ?? "",
            value: field.value ?? "",
          },
        ];
      }
      if (typeof field === "string") {
        // Split by comma for email/phone/domain
        return field.split(",").map((val, idx) => ({
          id: idx,
          name: "",
          value: val.trim(),
        }));
      }
      return [];
    };

    return {
      contact_id,
      purpose,
      attention,
      email: normalizeContactField(base.email),
      phone: normalizeContactField(base.phone),
      domain: normalizeContactField(base.domain),
      full: addressFull,
      address: base.address, // preserve original address array/object for modal editing
    };
  });
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

  // Store original objects for id/name preservation (at top level of component)
  const originalObjectsRef = React.useRef<{
    email?: any[];
    phone?: any[];
    domain?: any[];
  }>({});

  // Helper to split comma-separated values into arrays for editing
  const splitMulti = (val: string | undefined, sep: string) => {
    if (!val) return [""];
    if (Array.isArray(val)) {
      return val
        .map((v: any) => (typeof v === "object" && v.value ? v.value : v))
        .filter(Boolean);
    }
    return val
      .split(sep)
      .map((v) => v.trim())
      .filter(Boolean);
  };

  // Convert RefContact to MultiContact for editing (no hooks inside)
  const toMulti = (c: RefContact | null): MultiContact => {
    // Save original objects for id/name preservation
    originalObjectsRef.current.email = Array.isArray(c?.email)
      ? c.email
      : undefined;
    originalObjectsRef.current.phone = Array.isArray(c?.phone)
      ? c.phone
      : undefined;
    originalObjectsRef.current.domain = Array.isArray(c?.domain)
      ? c.domain
      : undefined;

    let addressArr: string[] = [""];
    if (c?.address) {
      if (Array.isArray(c.address)) {
        addressArr = c.address
          .map((item: any) =>
            item && typeof item === "object" && typeof item.full === "string"
              ? item.full
              : "",
          )
          .filter(Boolean);
      } else if (
        typeof c.address === "object" &&
        c.address !== null &&
        typeof c.address.full === "string"
      ) {
        addressArr = [c.address.full];
      } else if (typeof c.address === "string") {
        addressArr = [c.address];
      }
    }
    if (addressArr.length === 0) addressArr = [""];

    return {
      ...c,
      contact_id: c?.contact_id ?? 0,
      purpose: c?.purpose ?? "",
      email: Array.isArray(c?.email)
        ? c.email.map((e: any) =>
            typeof e === "object" && e.value ? e.value : e,
          )
        : c?.email
        ? splitMulti(c.email, ",")
        : [""],
      phone: Array.isArray(c?.phone)
        ? c.phone.map((p: any) =>
            typeof p === "object" && p.value ? p.value : p,
          )
        : c?.phone
        ? splitMulti(c.phone, ",")
        : [""],
      domain: Array.isArray(c?.domain)
        ? c.domain.map((d: any) =>
            typeof d === "object" && d.value ? d.value : d,
          )
        : c?.domain
        ? splitMulti(c.domain, ",")
        : [""],
      full: addressArr,
    };
  };

  // Convert MultiContact back to RefContact for saving
  const fromMulti = (m: MultiContact): RefContact => ({
    ...m,
    email:
      m.email?.map((val, idx) => {
        const orig = originalObjectsRef.current.email?.[idx];
        return {
          id: orig?.id ?? idx,
          name: orig?.name ?? "",
          value: val ?? "",
        };
      }) ?? [],
    phone:
      m.phone?.map((val, idx) => {
        const orig = originalObjectsRef.current.phone?.[idx];
        return {
          id: orig?.id ?? idx,
          name: orig?.name ?? "",
          value: val ?? "",
        };
      }) ?? [],
    domain:
      m.domain?.map((val, idx) => {
        const orig = originalObjectsRef.current.domain?.[idx];
        return {
          id: orig?.id ?? idx,
          name: orig?.name ?? "",
          value: val ?? "",
        };
      }) ?? [],
    full:
      Array.isArray(m.full) && m.full.length > 0
        ? m.full.filter(Boolean).join("")
        : m.full,
    address: m.address,
  });

  const [formData, setFormData] = useState<MultiContact>(toMulti(contact));

  // Communications state - fetched from contact model using contact_id
  const [loading, setLoading] = useState(false);
  const [emails, setEmails] = useState<EmailRecord[]>([]);
  const [phones, setPhones] = useState<PhoneRecord[]>([]);
  const [addresses, setAddresses] = useState<AddressRecord[]>([]);
  const [domains, setDomains] = useState<DomainRecord[]>([]);

  // Editing state for each communication type
  const [editingEmail, setEditingEmail] = useState<EmailRecord | null>(null);
  const [editingPhone, setEditingPhone] = useState<PhoneRecord | null>(null);
  const [editingAddress, setEditingAddress] = useState<AddressRecord | null>(
    null,
  );
  const [editingDomain, setEditingDomain] = useState<DomainRecord | null>(null);

  React.useEffect(() => {
    setFormData(toMulti(contact));
  }, [contact]);

  // Fetch full contact data when modal opens with a valid contact_id
  useEffect(() => {
    const fetchContactData = async () => {
      if (!isOpen || !contact?.contact_id || contact.contact_id <= 0) {
        // Reset communications if no valid contact_id
        setEmails([]);
        setPhones([]);
        setAddresses([]);
        setDomains([]);
        return;
      }

      setLoading(true);
      try {
        const response = await fetchContacts(contact.contact_id);
        const data = response?.data;

        if (data && data.refs?.links) {
          // Load communication records from refs.links
          setEmails(
            (data.refs.links.email ?? []).map((e: any) => ({
              id: e.id ?? 0,
              address: e.address ?? e.email ?? "",
              name: e.name ?? "",
              type: e.type ?? "",
              is_primary: e.is_primary ?? false,
              is_verified: e.is_verified ?? false,
            })),
          );

          setPhones(
            (data.refs.links.phone ?? []).map((p: any) => ({
              id: p.id ?? 0,
              number: p.number ?? "",
              name: p.name ?? "",
              type: p.type ?? "",
              is_primary: p.is_primary ?? false,
            })),
          );

          setAddresses(
            (data.refs.links.address ?? []).map((l: any) => ({
              id: l.id ?? 0,
              name: l.name ?? "",
              address_line1: l.address_line1 ?? l.address ?? "",
              address_line2: l.address_line2 ?? "",
              city: l.city ?? "",
              state: l.state ?? "",
              postal_code: l.postal_code ?? "",
              country: l.country ?? "",
              type: l.type ?? "",
              full: l.full ?? "",
            })),
          );

          setDomains(
            (data.refs.links.domain ?? []).map((d: any) => ({
              id: d.id ?? 0,
              domain: d.domain ?? d.path ?? d.name ?? "",
              name: d.name ?? "",
              is_primary: d.is_primary ?? false,
            })),
          );
        }
      } catch (error) {
        console.error("Error fetching contact data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchContactData();
  }, [isOpen, contact?.contact_id]);

  // Communication Handlers
  // EMAIL HANDLERS
  const handleAddEmail = useCallback(() => {
    const newEmail: EmailRecord = {
      id: 0,
      address: "",
      name: "",
      type: "",
      is_primary: false,
      is_verified: false,
    };
    setEditingEmail(newEmail);
    setEmails((prev) => [...prev, newEmail]);
  }, []);

  const handleEditEmail = useCallback((email: EmailRecord) => {
    setEditingEmail({ ...email });
  }, []);

  const handleDeleteEmail = useCallback(async (email: EmailRecord) => {
    if (!window.confirm("Delete this email?")) return;
    try {
      if (email.id > 0) {
        await deleteEmail("email", email.id);
      }
      setEmails((prev) =>
        prev.filter(
          (e) =>
            e.id !== email.id || (e.id === 0 && e.address !== email.address),
        ),
      );
    } catch (error) {
      console.error("Failed to delete email:", error);
    }
  }, []);

  const handleSaveEmail = useCallback(
    async (email: EmailRecord) => {
      try {
        if (!email.address) {
          alert("Email address is required");
          return;
        }
        const payload = {
          id: email.id || 0,
          email: email.address,
          name: email.name || "",
          type: email.type,
          is_primary: email.is_primary ?? false,
          is_verified: email.is_verified ?? false,
          contact_id: contact?.contact_id,
        };
        const res =
          email.id > 0
            ? await updateEmail(payload as any)
            : await createEmail(payload as any);

        if (res) {
          const savedId = (res as any).id || email.id;
          setEmails((prev) =>
            prev.map((e) =>
              e.id === email.id || (e.id === 0 && e.address === email.address)
                ? { ...email, id: savedId }
                : e,
            ),
          );
          setEditingEmail(null);
        }
      } catch (error) {
        console.error("Failed to save email:", error);
      }
    },
    [contact?.contact_id],
  );

  const handleEmailChange = useCallback(
    (field: keyof EmailRecord, value: any) => {
      setEditingEmail((prev) => (prev ? { ...prev, [field]: value } : null));
    },
    [],
  );

  // PHONE HANDLERS
  const handleAddPhone = useCallback(() => {
    const newPhone: PhoneRecord = {
      id: 0,
      number: "",
      name: "",
      type: "",
      is_primary: false,
    };
    setEditingPhone(newPhone);
    setPhones((prev) => [...prev, newPhone]);
  }, []);

  const handleEditPhone = useCallback((phone: PhoneRecord) => {
    setEditingPhone({ ...phone });
  }, []);

  const handleDeletePhone = useCallback(async (phone: PhoneRecord) => {
    if (!window.confirm("Delete this phone?")) return;
    try {
      if (phone.id > 0) {
        await deletePhone(phone.id);
      }
      setPhones((prev) =>
        prev.filter(
          (p) => p.id !== phone.id || (p.id === 0 && p.number !== phone.number),
        ),
      );
    } catch (error) {
      console.error("Failed to delete phone:", error);
    }
  }, []);

  const handleSavePhone = useCallback(
    async (phone: PhoneRecord) => {
      try {
        if (!phone.number) {
          alert("Phone number is required");
          return;
        }
        const payload = {
          number: phone.number,
          name: phone.name || "",
          country_code: "",
          opt_out: false,
          attention: "",
          format: "",
          contact_id: contact?.contact_id,
        };
        const res =
          phone.id > 0
            ? await updatePhone({ ...payload, id: String(phone.id) } as any)
            : await createPhone(payload as any);

        if (res) {
          const savedId = (res as any).id || phone.id;
          setPhones((prev) =>
            prev.map((p) =>
              p.id === phone.id || (p.id === 0 && p.number === phone.number)
                ? { ...phone, id: savedId }
                : p,
            ),
          );
          setEditingPhone(null);
        }
      } catch (error) {
        console.error("Failed to save phone:", error);
      }
    },
    [contact?.contact_id],
  );

  const handlePhoneChange = useCallback(
    (field: keyof PhoneRecord, value: any) => {
      setEditingPhone((prev) => (prev ? { ...prev, [field]: value } : null));
    },
    [],
  );

  // ADDRESS HANDLERS
  const handleAddAddress = useCallback(() => {
    const newAddress: AddressRecord = {
      id: 0,
      name: "",
      address_line1: "",
      city: "",
      state: "",
      postal_code: "",
      country: "",
      type: "",
    };
    setEditingAddress(newAddress);
    setAddresses((prev) => [...prev, newAddress]);
  }, []);

  const handleEditAddress = useCallback((addr: AddressRecord) => {
    setEditingAddress({ ...addr });
  }, []);

  const handleDeleteAddress = useCallback(async (addr: AddressRecord) => {
    if (!window.confirm("Delete this address?")) return;
    try {
      if (addr.id > 0) {
        await deleteAddress(addr.id);
      }
      setAddresses((prev) =>
        prev.filter(
          (l) =>
            l.id !== addr.id ||
            (l.id === 0 && l.address_line1 !== addr.address_line1),
        ),
      );
    } catch (error) {
      console.error("Failed to delete address:", error);
    }
  }, []);

  const handleSaveAddress = useCallback(
    async (addr: AddressRecord) => {
      try {
        const payload = {
          address1: addr.address_line1 || "",
          address2: addr.address_line2 || "",
          address_type: addr.type || "",
          full: addr.full || "",
          city: addr.city || "",
          state: addr.state || "",
          zip: addr.postal_code || "",
          country: addr.country || "",
          latitude: 0,
          longitude: 0,
          contact_id: contact?.contact_id,
        };
        const res =
          addr.id > 0
            ? await updateAddress({ ...payload, id: String(addr.id) } as any)
            : await createAddress(payload as any);

        if (res) {
          const savedId = (res as any).id || addr.id;
          setAddresses((prev) =>
            prev.map((l) =>
              l.id === addr.id ||
              (l.id === 0 && l.address_line1 === addr.address_line1)
                ? { ...addr, id: savedId }
                : l,
            ),
          );
          setEditingAddress(null);
        }
      } catch (error) {
        console.error("Failed to save address:", error);
      }
    },
    [contact?.contact_id],
  );

  const handleAddressChange = useCallback(
    (field: keyof AddressRecord, value: any) => {
      setEditingAddress((prev) => (prev ? { ...prev, [field]: value } : null));
    },
    [],
  );

  // DOMAIN HANDLERS
  const handleAddDomain = useCallback(() => {
    const newDomain: DomainRecord = {
      id: 0,
      domain: "",
      name: "",
      is_primary: false,
    };
    setEditingDomain(newDomain);
    setDomains((prev) => [...prev, newDomain]);
  }, []);

  const handleEditDomain = useCallback((domain: DomainRecord) => {
    setEditingDomain({ ...domain });
  }, []);

  const handleDeleteDomain = useCallback(async (domain: DomainRecord) => {
    if (!window.confirm("Delete this domain?")) return;
    try {
      if (domain.id > 0) {
        await deleteDomain(domain.id);
      }
      setDomains((prev) =>
        prev.filter(
          (d) =>
            d.id !== domain.id || (d.id === 0 && d.domain !== domain.domain),
        ),
      );
    } catch (error) {
      console.error("Failed to delete domain:", error);
    }
  }, []);

  const handleSaveDomain = useCallback(
    async (domain: DomainRecord) => {
      try {
        if (!domain.domain) {
          alert("Domain is required");
          return;
        }
        const payload = {
          path: domain.domain,
          type: "",
          contact_id: contact?.contact_id,
        };
        const res =
          domain.id > 0
            ? await updateDomain({ ...payload, id: String(domain.id) } as any)
            : await createDomain(payload as any);

        if (res) {
          const savedId = (res as any).id || domain.id;
          setDomains((prev) =>
            prev.map((d) =>
              d.id === domain.id || (d.id === 0 && d.domain === domain.domain)
                ? { ...domain, id: savedId }
                : d,
            ),
          );
          setEditingDomain(null);
        }
      } catch (error) {
        console.error("Failed to save domain:", error);
      }
    },
    [contact?.contact_id],
  );

  const handleDomainChange = useCallback(
    (field: keyof DomainRecord, value: any) => {
      setEditingDomain((prev) => (prev ? { ...prev, [field]: value } : null));
    },
    [],
  );

  if (!isOpen || !contact) return null;

  const handleChange = (
    field: keyof MultiContact,
    value: string | string[],
    idx?: number,
  ) => {
    if (["email", "phone", "domain", "address", "full"].includes(field)) {
      setFormData((prev) => {
        let arr: string[] = Array.isArray(prev[field])
          ? [...(prev[field] as string[])]
          : typeof prev[field] === "string"
          ? [prev[field] as string]
          : [""];
        if (typeof idx === "number") {
          arr[idx] = value ? (value as string) : "";
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
            {formData.full?.map((addr, idx) => (
              <div key={idx} className="flex gap-1 mb-1">
                <textarea
                  value={addr}
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

          {/* ----------------------------------
              COMMUNICATIONS SECTION
              Fetched from contact model using contact_id
          ---------------------------------- */}
          {contact?.contact_id && contact.contact_id > 0 && (
            <>
              <div className="border-t border-slate-200 dark:border-slate-700 pt-4 mt-4">
                <h5 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
                  <FaUser className="text-blue-500" />
                  Communications
                  {loading && (
                    <FaSpinner className="animate-spin w-3 h-3 text-blue-500" />
                  )}
                </h5>
                <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
                  Contact ID: {contact.contact_id}
                </p>
              </div>

              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <FaSpinner className="animate-spin w-6 h-6 text-blue-500" />
                  <span className="ml-2 text-sm text-slate-500">
                    Loading contact data...
                  </span>
                </div>
              ) : (
                <>
                  {/* Emails Table */}
                  <CommunicationTable<EmailRecord>
                    title="Emails"
                    icon={<FaEnvelope className="text-blue-500 w-3 h-3" />}
                    data={emails}
                    columns={[
                      { key: "address", label: "Email" },
                      { key: "name", label: "Name" },
                      {
                        key: "is_primary",
                        label: "Primary",
                        render: (e) => (e.is_primary ? "✓" : ""),
                      },
                    ]}
                    onAdd={handleAddEmail}
                    onEdit={handleEditEmail}
                    onDelete={handleDeleteEmail}
                    onSave={handleSaveEmail}
                    editingItem={editingEmail}
                    onEditChange={handleEmailChange}
                    onCancelEdit={() => {
                      if (editingEmail?.id === 0) {
                        setEmails((prev) => prev.filter((e) => e.id !== 0));
                      }
                      setEditingEmail(null);
                    }}
                  />

                  {/* Phones Table */}
                  <CommunicationTable<PhoneRecord>
                    title="Phones"
                    icon={<FaPhone className="text-green-500 w-3 h-3" />}
                    data={phones}
                    columns={[
                      { key: "number", label: "Phone" },
                      { key: "name", label: "Name" },
                      {
                        key: "is_primary",
                        label: "Primary",
                        render: (p) => (p.is_primary ? "✓" : ""),
                      },
                    ]}
                    onAdd={handleAddPhone}
                    onEdit={handleEditPhone}
                    onDelete={handleDeletePhone}
                    onSave={handleSavePhone}
                    editingItem={editingPhone}
                    onEditChange={handlePhoneChange}
                    onCancelEdit={() => {
                      if (editingPhone?.id === 0) {
                        setPhones((prev) => prev.filter((p) => p.id !== 0));
                      }
                      setEditingPhone(null);
                    }}
                  />

                  {/* Addresses Table */}
                  <CommunicationTable<AddressRecord>
                    title="Addresses"
                    icon={<FaMapMarkerAlt className="text-red-500 w-3 h-3" />}
                    data={addresses}
                    columns={[
                      { key: "address_line1", label: "Address" },
                      { key: "city", label: "City" },
                      { key: "state", label: "State" },
                      { key: "postal_code", label: "Zip" },
                    ]}
                    onAdd={handleAddAddress}
                    onEdit={handleEditAddress}
                    onDelete={handleDeleteAddress}
                    onSave={handleSaveAddress}
                    editingItem={editingAddress}
                    onEditChange={handleAddressChange}
                    onCancelEdit={() => {
                      if (editingAddress?.id === 0) {
                        setAddresses((prev) => prev.filter((l) => l.id !== 0));
                      }
                      setEditingAddress(null);
                    }}
                  />

                  {/* Domains Table */}
                  <CommunicationTable<DomainRecord>
                    title="Domains"
                    icon={<FaGlobe className="text-purple-500 w-3 h-3" />}
                    data={domains}
                    columns={[
                      { key: "domain", label: "Domain" },
                      { key: "name", label: "Name" },
                      {
                        key: "is_primary",
                        label: "Primary",
                        render: (d) => (d.is_primary ? "✓" : ""),
                      },
                    ]}
                    onAdd={handleAddDomain}
                    onEdit={handleEditDomain}
                    onDelete={handleDeleteDomain}
                    onSave={handleSaveDomain}
                    editingItem={editingDomain}
                    onEditChange={handleDomainChange}
                    onCancelEdit={() => {
                      if (editingDomain?.id === 0) {
                        setDomains((prev) => prev.filter((d) => d.id !== 0));
                      }
                      setEditingDomain(null);
                    }}
                  />
                </>
              )}
            </>
          )}
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
            Save Contact
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
  console.log("[DEBUG] ContactBlock render contact", contact);
  const displayName =
    contact.attention ||
    (typeof contact.contact_id === "number" && contact.contact_id > 0
      ? `Contact #${contact.contact_id}`
      : "Contact");

  // Check if all fields are empty (support array or string for legacy)
  const hasEmail = Array.isArray(contact.email)
    ? contact.email.some((e) => e && e.value && e.value.trim())
    : !!(
        contact.email &&
        typeof contact.email === "string" &&
        contact.email.trim()
      );
  const hasPhone = Array.isArray(contact.phone)
    ? contact.phone.some((p) => p && p.value && p.value.trim())
    : !!(
        contact.phone &&
        typeof contact.phone === "string" &&
        contact.phone.trim()
      );
  const hasDomain = Array.isArray(contact.domain)
    ? contact.domain.some((d) => d && d.value && d.value.trim())
    : !!(
        contact.domain &&
        typeof contact.domain === "string" &&
        contact.domain.trim()
      );
  const hasAddress = !!(
    contact.full &&
    typeof contact.full === "string" &&
    contact.full.trim()
  );
  const noDetails = !hasEmail && !hasPhone && !hasDomain && !hasAddress;

  //console.log("contact.email", contact.email);

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

        {/* Always render the card body for consistent layout */}
        <div className="flex flex-col gap-1 ml-5 mt-2 text-slate-500 dark:text-slate-400 min-h-[24px]">
          {/* Render all emails with id, name, value if array of objects, else fallback to string */}
          {Array.isArray(contact.email) ? (
            contact.email.map((emailObj: any, idx: number) =>
              emailObj && typeof emailObj === "object" && emailObj.value ? (
                <table className="w-full text-xs" key={emailObj.id ?? idx}>
                  {idx === 0 && (
                    <thead>
                      <tr>
                        <th
                          colSpan={4}
                          className="text-left pb-1 text-slate-600 dark:text-slate-300"
                        >
                          Emails
                        </th>
                      </tr>
                    </thead>
                  )}
                  <tbody>
                    <tr>
                      <td className="w-10 text-left align-middle text-slate-400">
                        {emailObj.id}
                      </td>
                      <td className="w-24 text-left align-middle text-slate-400">
                        {emailObj.name}
                      </td>
                      <td className="w-8 text-left align-middle">
                        <FaEnvelope size={10} />
                      </td>
                      <td className="text-left align-middle">
                        <a
                          href={`mailto:${emailObj.value}`}
                          className="hover:text-blue-500"
                        >
                          {emailObj.value}
                        </a>
                      </td>
                    </tr>
                  </tbody>
                </table>
              ) : null,
            )
          ) : typeof contact.email === "string" &&
            contact.email.trim() !== "" ? (
            <span>{contact.email}</span>
          ) : null}

          {/* Render all phones with id, name, value if array of objects, else fallback to string */}
          {Array.isArray(contact.phone) ? (
            contact.phone.map((phoneObj: any, idx: number) =>
              phoneObj && typeof phoneObj === "object" && phoneObj.value ? (
                <table className="w-full text-xs" key={phoneObj.id ?? idx}>
                  {idx === 0 && (
                    <thead>
                      <tr>
                        <th
                          colSpan={4}
                          className="text-left pb-1 text-slate-600 dark:text-slate-300"
                        >
                          Phones
                        </th>
                      </tr>
                    </thead>
                  )}
                  <tbody>
                    <tr>
                      <td className="w-10 text-left align-middle text-slate-400">
                        {phoneObj.id}
                      </td>
                      <td className="w-24 text-left align-middle text-slate-400">
                        {phoneObj.name}
                      </td>
                      <td className="w-8 text-left align-middle">
                        <FaPhone size={10} />
                      </td>
                      <td className="text-left align-middle">
                        <a
                          href={`tel:${phoneObj.value}`}
                          className="hover:text-blue-500"
                        >
                          {phoneObj.value}
                        </a>
                      </td>
                    </tr>
                  </tbody>
                </table>
              ) : null,
            )
          ) : typeof contact.phone === "string" &&
            contact.phone.trim() !== "" ? (
            <span>{contact.phone}</span>
          ) : null}

          {/* Render all domains with id, name, value if array of objects, else fallback to string */}
          {Array.isArray(contact.domain) ? (
            contact.domain.map((domainObj: any, idx: number) =>
              domainObj && typeof domainObj === "object" && domainObj.value ? (
                <table className="w-full text-xs" key={domainObj.id ?? idx}>
                  {idx === 0 && (
                    <thead>
                      <tr>
                        <th
                          colSpan={4}
                          className="text-left pb-1 text-slate-600 dark:text-slate-300"
                        >
                          Domains
                        </th>
                      </tr>
                    </thead>
                  )}
                  <tbody>
                    <tr>
                      <td className="w-10 text-left align-middle text-slate-400">
                        {domainObj.id}
                      </td>
                      <td className="w-24 text-left align-middle text-slate-400">
                        {domainObj.name}
                      </td>
                      <td className="w-8 text-left align-middle">
                        <FaGlobe size={10} />
                      </td>
                      <td className="text-left align-middle">
                        <a
                          href={`https://${domainObj.value}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:text-blue-500"
                        >
                          {domainObj.value}
                        </a>
                      </td>
                    </tr>
                  </tbody>
                </table>
              ) : null,
            )
          ) : typeof contact.domain === "string" &&
            contact.domain.trim() !== "" ? (
            <span>{contact.domain}</span>
          ) : null}

          {/* Render all addresses as array of objects (id, name, full), else fallback to string */}
          {Array.isArray(contact.address) ? (
            contact.address.map((addrObj: any, idx: number) =>
              addrObj && typeof addrObj === "object" && addrObj.full ? (
                <table className="w-full text-xs" key={addrObj.id ?? idx}>
                  {idx === 0 && (
                    <thead>
                      <tr>
                        <th
                          colSpan={4}
                          className="text-left pb-1 text-slate-600 dark:text-slate-300"
                        >
                          Addresses
                        </th>
                      </tr>
                    </thead>
                  )}
                  <tbody>
                    <tr>
                      <td className="w-10 text-left align-middle text-slate-400">
                        {addrObj.id}
                      </td>
                      <td className="w-24 text-left align-middle text-slate-400">
                        {addrObj.name}
                      </td>
                      <td className="w-8 text-left align-middle">
                        {/* You can use an icon here if desired */}
                      </td>
                      <td className="text-left align-middle whitespace-pre-line">
                        {addrObj.full}
                      </td>
                    </tr>
                  </tbody>
                </table>
              ) : null,
            )
          ) : typeof contact.address === "string" &&
            contact.address.trim() !== "" ? (
            <span>{contact.address}</span>
          ) : null}
          {/* If no details at all, show placeholder */}
          {noDetails && (
            <span className="text-xs italic text-slate-400">
              No contact details available
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

const PurposeSection: React.FC<{
  purpose: string;
  contacts: RefContact[];
  isEditing?: boolean;
  onRemove?: (contactId: number) => void;
  onEdit?: (contact: RefContact) => void;
}> = ({ purpose, contacts, isEditing, onRemove, onEdit }) => {
  console.log("[DEBUG] PurposeSection", purpose, contacts);
  return (
    <div className="border-b border-slate-200 dark:border-slate-700 pb-0 last:border-0 last:pb-0 bg-success-50 cus-bg-purple-light">
      <div className="flex items-center justify-between bg-success-200">
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide p-2">
          {formatPurpose(purpose)}
        </h4>
      </div>
      <div className="bg-success-50 hover:bg-success-100 dark:hover:bg-success-100 transition-colors  min-h-[140px]">
        {contacts && contacts.length > 0 ? (
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
            {isEditing
              ? "No contact assigned (add new contact for this purpose)"
              : "No contact assigned"}
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
  const { ensureWindow, activateWindow, activePath } = useWindowManager();
  const [editingContact, setEditingContact] = useState<RefContact | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [addContactPurpose, setAddContactPurpose] = useState<string>("");

  const grouped = groupContactsByPurpose(contacts);
  //const grouped = groupContactsByPurpose(contacts);

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
  const openWindow = (path: string, title: string) => {
    ensureWindow(path, title);
    activateWindow(path);
  };
  const handleEditContact = (contact: RefContact) => {
    setEditingContact(contact);
    setIsModalOpen(true);
  };

  const handleSaveContact = (updatedContact: RefContact) => {
    console.log("onChange", onChange);
    if (onChange) {
      // Debug: log contacts before update
      console.log("[DEBUG] contacts before update", contacts);
      // Update by both contact_id and purpose
      const updatedId = Number(updatedContact.contact_id);
      const updatedPurpose = updatedContact.purpose;
      let replaced = false;
      const newContacts = contacts.map((c) => {
        if (
          Number(c.contact_id) === updatedId &&
          c.purpose === updatedPurpose
        ) {
          replaced = true;
          // Always use updatedContact values for multi-value fields
          return {
            ...c,
            ...updatedContact,
            email: updatedContact.email,
            phone: updatedContact.phone,
            domain: updatedContact.domain,
            address: updatedContact.address,
          };
        }
        return c;
      });
      // If not found, add as new
      if (!replaced) {
        newContacts.push(updatedContact);
      }
      // Remove any accidental duplicates (same contact_id and purpose)
      const dedupedContacts = newContacts.filter(
        (c, idx, arr) =>
          arr.findIndex(
            (x) =>
              Number(x.contact_id) === Number(c.contact_id) &&
              x.purpose === c.purpose,
          ) === idx,
      );
      // Debug: log contacts after update
      console.log("[DEBUG] contacts after update", dedupedContacts);
      onChange([...dedupedContacts]);
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

      {/* Add Contact Section - Navigate to Contact List/Add page */}
      {isEditing && (
        <div className="flex justify-end mb-1 px-2">
          <button
            type="button"
            className="px-3 py-2 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700 transition-colors flex items-center gap-2"
            onClick={() => openWindow("/core/contact/list", "Contact")}
          >
            <FaPlus className="w-3 h-3" />
            Add New Contact
            <FaExternalLinkAlt className="w-3 h-3" />
          </button>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 p-2 bg-gray-100 ">
        {Array.from(allPurposes)
          .filter((purpose) => grouped[purpose] && grouped[purpose].length > 0)
          .map((purpose) => (
            <PurposeSection
              key={purpose}
              purpose={purpose}
              contacts={grouped[purpose] || []}
              isEditing={isEditing}
              onRemove={isEditing ? handleRemoveContact : undefined}
              onEdit={isEditing ? handleEditContact : undefined}
            />
          ))}
      </div>
    </>
  );
};

export default RefsLinksContactPanel;
