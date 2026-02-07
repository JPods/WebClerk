/**
 * RefsLinksContactPanel - Display contacts grouped by purpose with editing support
 * Syncs with refs.links.contact structure from API
 */
import React, { useState, useEffect } from "react";
import { useWindowManager } from "@/context/WindowManagerContext";
import { SearchableSelect } from "@/components/ui/dropdown/SearchableSelect";
import {
  FaUser,
  FaEnvelope,
  FaPhone,
  FaTimes,
  FaGlobe,
  FaPlus,
  FaExternalLinkAlt,
  FaEdit,
  FaSpinner,
  FaStar,
} from "react-icons/fa";
import type { ContactPurpose } from "../types/transactionTypes";
import { CommunicationsPanel } from "@/apps/common/components/panels";
import { getRecord, getRecords, saveRecord } from "@/api/wcapi";

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

// API contact structure from refs.links.contact
export interface RefContact {
  contact_id: number;
  purpose: ContactPurpose | string;
  attention?: string;
  email?: string | { id: any; name: any; value: any }[];
  phone?: string | { id: any; name: any; value: any }[];
  full?: string | string[];
  domain?: string | { id: any; name: any; value: any }[];
  address?: any; // Added to fix compile error
}

// Helper to normalize refs.links.contact API data to RefContact[]
export function normalizeRefsLinksContact(apiContacts: any[]): RefContact[] {
  if (!Array.isArray(apiContacts)) return [];
  return apiContacts.map((c, idx) => {
    // Accept both {contact, purpose} and {purpose, ...fields} shapes
    let base = c;
    let purpose = c.purpose || "";
    let contact_id: any;

    // If nested contact, flatten and get contact_id from nested object
    // API structure: refs.links.contact[].contact.id
    if (c.contact && typeof c.contact === "object") {
      base = c.contact;
      purpose = c.purpose || base.purpose || "";
      contact_id = c.contact.id; // Get id from nested contact object
    } else {
      contact_id = c.id;
    }

    // Fallback if contact_id is still not set
    if (contact_id === undefined || contact_id === null || contact_id === "") {
      contact_id = idx + 1;
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
  orderId?: number; // Order ID for saving contact data
  onAdd?: (purpose: ContactPurpose | string) => void;
  onRemove?: (contactId: number) => void;
  onEdit?: (contact: RefContact) => void;
  onChange?: (contacts: RefContact[]) => void;
  onSaveSuccess?: () => void; // Callback after successful save
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

// Helper to format purpose label (during dev: return raw value for alignment)
const formatPurpose = (purpose: string): string => {
  return purpose;  // Dev mode: exact field names
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
  orderId?: number;
  onClose: () => void;
  onSave: (contact: RefContact) => void;
  onSaveSuccess?: () => void;
}> = ({ contact, isOpen, orderId, onClose, onSave, onSaveSuccess }) => {
  // Communications state - fetched from contact model using contact_id
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [emails, setEmails] = useState<EmailRecord[]>([]);
  const [phones, setPhones] = useState<PhoneRecord[]>([]);
  const [addresses, setAddresses] = useState<AddressRecord[]>([]);
  const [domains, setDomains] = useState<DomainRecord[]>([]);

  // Contact selection state
  const [contactsList, setContactsList] = useState<
    { id: number; name: string }[]
  >([]);
  const [selectedContactId, setSelectedContactId] = useState<number>(0);
  const [selectedPurpose, setSelectedPurpose] = useState<string>("");
  const [loadingContacts, setLoadingContacts] = useState(false);

  // Initialize selected values when modal opens or contact changes
  useEffect(() => {
    if (isOpen && contact) {
      setSelectedContactId(contact.contact_id || 0);
      setSelectedPurpose(contact.purpose || "");
    }
  }, [isOpen, contact]);

  // Fetch contacts list on modal open
  useEffect(() => {
    const fetchContactsList = async () => {
      if (!isOpen) return;

      setLoadingContacts(true);
      try {
        const result = (await getRecords("contact", {
          is_active: true,
          limit: 500,
        })) as any;
        // API returns results array
        const records =
          result?.results || result?.records || result?.data || [];
        console.log(
          "[ContactEditModal] Fetched contacts list:",
          records.length,
          "from result keys:",
          Object.keys(result || {}),
        );

        // Map to simple id/name structure
        const contacts = records.map((c: any) => ({
          id: c.id,
          name: c.name || c.attention || c.full_name || `Contact #${c.id}`,
        }));
        setContactsList(contacts);
      } catch (error) {
        console.error(
          "[ContactEditModal] Error fetching contacts list:",
          error,
        );
      } finally {
        setLoadingContacts(false);
      }
    };

    fetchContactsList();
  }, [isOpen]);

  // Fetch contact data from API using selectedContactId (similar to ContactDetail.tsx)
  useEffect(() => {
    const fetchContactData = async () => {
      if (!isOpen || !selectedContactId || selectedContactId <= 0) {
        setEmails([]);
        setPhones([]);
        setAddresses([]);
        setDomains([]);
        return;
      }

      setLoading(true);
      try {
        // Fetch contact data from contact model using getRecord
        const result = await getRecord("contact", selectedContactId);
        const data = result?.record || result;
        console.log("[ContactEditModal] Fetched contact data:", data);

        // Contact model returns data in "communications" object, not refs.links
        const comms = data?.communications;
        console.log("[ContactEditModal] Communications data:", {
          emailsCount: comms?.emails?.length || 0,
          phonesCount: comms?.phones?.length || 0,
          addressesCount: comms?.addresses?.length || 0,
          domainsCount: comms?.domains?.length || 0,
        });

        if (comms) {
          // Load communication records from communications object
          // Email structure: {id, name, email, type, is_primary, is_verified, ...}
          setEmails(
            (comms.emails ?? []).map((e: any) => ({
              id: e.id ?? 0,
              address: e.email ?? e.address ?? "",
              name: e.name ?? "",
              type: e.type ?? "",
              is_primary: e.is_primary ?? false,
              is_verified: e.is_verified ?? false,
            })),
          );

          // Phone structure: {id, name, number/phone, type, is_primary, ...}
          setPhones(
            (comms.phones ?? []).map((p: any) => ({
              id: p.id ?? 0,
              number: p.number ?? p.phone ?? "",
              name: p.name ?? "",
              type: p.type ?? "",
              is_primary: p.is_primary ?? false,
            })),
          );

          // Address structure: {id, name, full, address_line1, city, state, ...}
          setAddresses(
            (comms.addresses ?? []).map((a: any) => ({
              id: a.id ?? 0,
              name: a.name ?? "",
              address_line1: a.address_line1 ?? a.address1 ?? a.address ?? "",
              address_line2: a.address_line2 ?? a.address2 ?? "",
              city: a.city ?? "",
              state: a.state ?? "",
              postal_code: a.postal_code ?? a.zip ?? "",
              country: a.country ?? "",
              type: a.type ?? "",
              full: a.full ?? "",
            })),
          );

          // Domain structure: {id, name, domain, is_primary, ...}
          setDomains(
            (comms.domains ?? []).map((d: any) => ({
              id: d.id ?? 0,
              domain: d.domain ?? d.path ?? d.url ?? "",
              name: d.name ?? "",
              is_primary: d.is_primary ?? false,
            })),
          );
        }
      } catch (error) {
        console.error("[ContactEditModal] Error fetching contact data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchContactData();
  }, [isOpen, selectedContactId]);

  if (!isOpen || !contact) return null;

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
          {/* COMMUNICATIONS PANEL - Fetches data from contact model using contact_id */}
          {selectedContactId > 0 && (
            <>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <FaSpinner className="animate-spin w-6 h-6 text-blue-500" />
                  <span className="ml-2 text-sm text-slate-500">
                    Loading contact data...
                  </span>
                </div>
              ) : (
                <>
                  <div>
                    <SearchableSelect
                      label="Contact"
                      options={contactsList.map((c) => ({
                        value: c.id,
                        label: `#${c.id} - ${c.name}`,
                        description: c.name,
                      }))}
                      value={selectedContactId || null}
                      onChange={(val) => {
                        const newId =
                          typeof val === "number"
                            ? val
                            : parseInt(String(val), 10) || 0;

                        setSelectedContactId(newId);
                      }}
                      placeholder="-- Select Contact --"
                      searchPlaceholder="Search contacts..."
                      loading={loadingContacts}
                      disabled={loadingContacts}
                      clearable={false}
                    />
                  </div>
                  <div>
                    <div className="flex-1 items-center gap-1 mb-1">
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                        Purpose
                      </label>
                      <select
                        value={selectedPurpose || ""}
                        onChange={(e) => {
                          console.log(
                            "[ContactEditModal] Purpose changed:",
                            e.target.value,
                          );
                          setSelectedPurpose(e.target.value);
                        }}
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
                        value={contact.attention || ""}
                        onChange={() => {}}
                        placeholder="Contact name"
                        className="w-full px-3 py-2 text-xs border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                      />
                    </div>
                  </div>
                  <CommunicationsPanel
                    entityType="contact"
                    entityId={selectedContactId}
                    contactId={selectedContactId}
                    data={{
                      emails: emails.map((e) => ({
                        id: e.id,
                        email: e.address,
                        name: e.name || "",
                        type: e.type || "",
                        is_primary: e.is_primary || false,
                      })),
                      phones: phones.map((p) => ({
                        id: p.id,
                        number: p.number,
                        name: p.name || "",
                        format: p.number,
                      })),
                      addresses: addresses.map((a) => ({
                        id: a.id,
                        name: a.name || "",
                        address1: a.address_line1 || "",
                        city: a.city || "",
                        state: a.state || "",
                        zip: a.postal_code || "",
                        country: a.country || "",
                        full: a.full || "",
                      })),
                      domains: domains.map((d) => ({
                        id: d.id,
                        domain: d.domain,
                        name: d.name || "",
                        is_primary: d.is_primary || false,
                      })),
                    }}
                    onChange={(comms) => {
                      // Update local state with new communications data
                      // Only update if we have data to prevent accidental overwrites
                      console.log(
                        "[ContactEditModal] CommunicationsPanel onChange:",
                        {
                          emailsCount: comms.emails?.length,
                          phonesCount: comms.phones?.length,
                          addressesCount: comms.addresses?.length,
                          domainsCount: comms.domains?.length,
                          currentEmailsCount: emails.length,
                        },
                      );

                      if (comms.emails && comms.emails.length > 0) {
                        setEmails(
                          comms.emails.map((e: any) => ({
                            id: e.id ?? 0,
                            address: e.email ?? e.value ?? "",
                            name: e.name ?? "",
                            type: e.type ?? "",
                            is_primary: e.is_primary ?? false,
                            is_verified: e.verified ?? false,
                          })),
                        );
                      }
                      if (comms.phones && comms.phones.length > 0) {
                        setPhones(
                          comms.phones.map((p: any) => ({
                            id: p.id ?? 0,
                            number: p.number ?? p.value ?? "",
                            name: p.name ?? "",
                            type: p.type ?? "",
                            is_primary: p.is_primary ?? false,
                          })),
                        );
                      }
                      if (comms.addresses && comms.addresses.length > 0) {
                        setAddresses(
                          comms.addresses.map((a: any) => ({
                            id: a.id ?? 0,
                            name: a.name ?? "",
                            address_line1: a.address1 ?? "",
                            address_line2: a.address2 ?? "",
                            city: a.city ?? "",
                            state: a.state ?? "",
                            postal_code: a.zip ?? "",
                            country: a.country ?? "",
                            type: a.type ?? "",
                            full: a.full ?? "",
                          })),
                        );
                      }
                      if (comms.domains && comms.domains.length > 0) {
                        setDomains(
                          comms.domains.map((d: any) => ({
                            id: d.id ?? 0,
                            domain: d.domain ?? d.value ?? "",
                            name: d.name ?? "",
                            is_primary: d.is_primary ?? false,
                          })),
                        );
                      }
                    }}
                    defaultCollapsed={false}
                    title="Contact Info"
                  />
                </>
              )}
            </>
          )}
        </div>

        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 flex justify-end gap-2">
          <button
            onClick={onClose}
            disabled={saving}
            className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={async () => {
              if (!orderId || !contact) {
                console.warn(
                  "[ContactEditModal] No orderId or contact to save",
                );
                onSave(contact);
                onClose();
                return;
              }

              setSaving(true);
              try {
                // Log current state counts before building payload
                console.log("[ContactEditModal] Current state counts:", {
                  emailsCount: emails.length,
                  phonesCount: phones.length,
                  domainsCount: domains.length,
                  addressesCount: addresses.length,
                  emails: emails.map((e) => ({ id: e.id, address: e.address })),
                });

                // Build contact data in the format expected by order refs.links.contact
                // Format: {purpose, contact: {id, email: [{id, name, value}], phone: [...], domain: [...], address: [{id, name, full}]}}
                // Use selectedContactId and selectedPurpose (which may have been changed via dropdowns)
                const contactPayload = {
                  purpose: selectedPurpose,
                  contact: {
                    id: selectedContactId,
                    email: emails.map((e) => ({
                      id: e.id,
                      name: e.name || "",
                      value: e.address || "",
                    })),
                    phone: phones.map((p) => ({
                      id: p.id,
                      name: p.name || "",
                      value: p.number || "",
                    })),
                    domain: domains.map((d) => ({
                      id: d.id,
                      name: d.name || "",
                      value: d.domain || "",
                    })),
                    address: addresses.map((a) => ({
                      id: a.id,
                      name: a.name || "",
                      full: a.full || "",
                    })),
                  },
                };

                console.log("[ContactEditModal] Saving contact to order:", {
                  orderId,
                  contactPayload,
                  originalContactId: contact.contact_id,
                  newContactId: selectedContactId,
                  originalPurpose: contact.purpose,
                  newPurpose: selectedPurpose,
                  emailCount: contactPayload.contact.email.length,
                });

                // Save to order model - update refs.links.contact
                // The API expects the full refs.links.contact array, so we need to:
                // 1. Fetch current order to get existing contacts
                // 2. Update the specific contact by original id and purpose (find by original values)
                // 3. Save back to order with new selectedContactId and selectedPurpose
                const orderResult = await getRecord("order", orderId);
                const orderData = orderResult?.record || orderResult;
                const existingContacts = orderData?.refs?.links?.contact || [];

                console.log(
                  "[ContactEditModal] Existing contacts:",
                  existingContacts,
                );
                console.log("[ContactEditModal] Looking for original:", {
                  originalContactId: contact.contact_id,
                  originalPurpose: contact.purpose,
                });

                // Find and update the contact with matching ORIGINAL id and purpose
                let updated = false;
                const updatedContacts = existingContacts.map(
                  (c: any, index: number) => {
                    // Get the contact id from the nested structure
                    const cId = c.contact?.id || c.id;
                    const cPurpose = c.purpose;

                    console.log(
                      `[ContactEditModal] Checking contact[${index}]:`,
                      {
                        cId,
                        cPurpose,
                        matchesId: cId === contact.contact_id,
                        matchesPurpose: cPurpose === contact.purpose,
                      },
                    );

                    // Match by original contact_id AND purpose
                    if (
                      cId === contact.contact_id &&
                      cPurpose === contact.purpose
                    ) {
                      updated = true;
                      console.log(
                        `[ContactEditModal] Found match at index ${index}, replacing with:`,
                        contactPayload,
                      );
                      return contactPayload; // This now has the new selectedContactId and selectedPurpose
                    }
                    return c;
                  },
                );

                console.log("[ContactEditModal] Updated:", updated);

                // If not found, add as new
                if (!updated) {
                  console.log(
                    "[ContactEditModal] No match found, adding as new contact",
                  );
                  updatedContacts.push(contactPayload);
                }

                // Save to order - wrap refs in proper mode/value structure for save_view.py
                // The backend expects: { field_name: { mode: 'update', value: <actual_value> } }
                const savePayload = {
                  id: orderId,
                  refs: {
                    mode: "update",
                    value: {
                      links: {
                        contact: updatedContacts,
                      },
                    },
                  },
                };

                console.log(
                  "[ContactEditModal] Saving order payload:",
                  savePayload,
                );
                await saveRecord("order", savePayload);
                console.log("[ContactEditModal] Save successful");

                // Build updated contact object with new selectedContactId and selectedPurpose
                const updatedContact: RefContact = {
                  ...contact,
                  contact_id: selectedContactId,
                  purpose: selectedPurpose,
                  email: emails.map((e) => ({
                    id: e.id,
                    name: e.name || "",
                    value: e.address || "",
                  })),
                  phone: phones.map((p) => ({
                    id: p.id,
                    name: p.name || "",
                    value: p.number || "",
                  })),
                  domain: domains.map((d) => ({
                    id: d.id,
                    name: d.name || "",
                    value: d.domain || "",
                  })),
                  address: addresses.map((a) => ({
                    id: a.id,
                    name: a.name || "",
                    full: a.full || "",
                  })),
                };

                // If onSaveSuccess is provided, it will refresh data from API
                // so we don't need to update local state via onSave
                if (onSaveSuccess) {
                  // API refresh will handle the data update
                  console.log(
                    "[ContactEditModal] Triggering API refresh via onSaveSuccess",
                  );
                  onSaveSuccess();
                } else {
                  // No API refresh, update local state
                  onSave(updatedContact);
                }
                onClose();
              } catch (error) {
                console.error(
                  "[ContactEditModal] Error saving contact:",
                  error,
                );
                alert("Failed to save contact. Please try again.");
              } finally {
                setSaving(false);
              }
            }}
            disabled={saving}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {saving && <FaSpinner className="animate-spin w-4 h-4" />}
            {saving ? "Saving..." : "Save Contact"}
          </button>
        </div>
      </div>
    </div>
  );
};

// Add New Purpose Modal - Add a new contact with a specific purpose
const AddPurposeModal: React.FC<{
  isOpen: boolean;
  orderId?: number;
  existingContacts: RefContact[];
  onClose: () => void;
  onChange?: (newContact: RefContact) => void; // For instant local state update
  onSaveSuccess?: () => void;
}> = ({
  isOpen,
  orderId,
  existingContacts,
  onClose,
  onChange,
  onSaveSuccess,
}) => {
  const [saving, setSaving] = useState(false);
  const [selectedPurpose, setSelectedPurpose] = useState<string>("");
  const [selectedContactId, setSelectedContactId] = useState<number>(0);
  const [contactsList, setContactsList] = useState<
    { id: number; name: string }[]
  >([]);
  const [loadingContacts, setLoadingContacts] = useState(false);
  const [validationError, setValidationError] = useState<string>("");

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setSelectedPurpose("");
      setSelectedContactId(0);
      setValidationError("");
    }
  }, [isOpen]);

  // Fetch contacts list on modal open
  useEffect(() => {
    const fetchContactsList = async () => {
      if (!isOpen) return;

      setLoadingContacts(true);
      try {
        const result = (await getRecords("contact", {
          is_active: true,
          limit: 500,
        })) as any;
        const records =
          result?.results || result?.records || result?.data || [];
        console.log("[AddPurposeModal] Fetched contacts list:", records.length);

        const contacts = records.map((c: any) => ({
          id: c.id,
          name: c.name || c.attention || c.full_name || `Contact #${c.id}`,
        }));
        setContactsList(contacts);
      } catch (error) {
        console.error("[AddPurposeModal] Error fetching contacts list:", error);
      } finally {
        setLoadingContacts(false);
      }
    };

    fetchContactsList();
  }, [isOpen]);

  // Validate for duplicate contact_id + purpose combinations
  useEffect(() => {
    if (selectedPurpose && selectedContactId > 0) {
      const isDuplicate = existingContacts.some(
        (c) =>
          Number(c.contact_id) === selectedContactId &&
          c.purpose === selectedPurpose,
      );
      if (isDuplicate) {
        setValidationError(
          `This contact already exists with purpose "${formatPurpose(
            selectedPurpose,
          )}"`,
        );
      } else {
        setValidationError("");
      }
    } else {
      setValidationError("");
    }
  }, [selectedPurpose, selectedContactId, existingContacts]);

  const handleSave = async () => {
    if (!orderId) {
      console.warn("[AddPurposeModal] No orderId to save");
      return;
    }

    if (!selectedPurpose || selectedContactId <= 0) {
      setValidationError("Please select both a purpose and a contact");
      return;
    }

    if (validationError) {
      return;
    }

    setSaving(true);
    try {
      // Build contact payload in the format expected by order refs.links.contact
      const contactPayload = {
        purpose: selectedPurpose,
        contact: {
          id: selectedContactId,
          email: [],
          phone: [],
          domain: [],
          address: [],
        },
      };

      console.log(
        "[AddPurposeModal] Adding new purpose contact:",
        contactPayload,
      );

      // Fetch current order to get existing contacts
      const orderResult = await getRecord("order", orderId);
      const orderData = orderResult?.record || orderResult;
      const existingOrderContacts = orderData?.refs?.links?.contact || [];

      // Add the new contact
      const updatedContacts = [...existingOrderContacts, contactPayload];

      // Save to order with proper mode/value structure
      const savePayload = {
        id: orderId,
        refs: {
          mode: "update",
          value: {
            links: {
              contact: updatedContacts,
            },
          },
        },
      };

      console.log("[AddPurposeModal] Saving order payload:", savePayload);
      await saveRecord("order", savePayload);
      console.log("[AddPurposeModal] Save successful");

      // Build RefContact for instant local state update
      const newRefContact: RefContact = {
        contact_id: selectedContactId,
        purpose: selectedPurpose,
        email: [],
        phone: [],
        domain: [],
        address: [],
      };

      // Instant UI update via onChange (ContactBlock will fetch its own communications)
      if (onChange) {
        console.log(
          "[AddPurposeModal] Triggering instant local state update",
          newRefContact,
        );
        onChange(newRefContact);
      }

      // Optional: Trigger background API refresh for full sync
      // (UI already updated, this ensures data consistency)
      if (onSaveSuccess) {
        onSaveSuccess();
      }
      onClose();
    } catch (error) {
      console.error("[AddPurposeModal] Error saving:", error);
      alert("Failed to add new purpose. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="pointer-events-none fixed inset-0 z-[200000] flex items-center justify-center">
      <div
        className="pointer-events-auto absolute inset-0 bg-black/30"
        onClick={onClose}
      />
      <div className="pointer-events-auto relative w-full max-w-md mx-4 bg-white dark:bg-slate-800 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-700">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">
            Add New Purpose
          </h2>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          >
            <FaTimes size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4">
          {/* Purpose Dropdown */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              Purpose <span className="text-red-500">*</span>
            </label>
            <select
              value={selectedPurpose}
              onChange={(e) => setSelectedPurpose(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Select a purpose...</option>
              {STANDARD_PURPOSES.map((purpose) => (
                <option key={purpose} value={purpose}>
                  {formatPurpose(purpose)}
                </option>
              ))}
            </select>
          </div>

          {/* Contact Dropdown */}
          <div>
            <SearchableSelect
              label="Contact"
              options={contactsList.map((c) => ({
                value: c.id,
                label: `${c.name} (#${c.id})`,
                description: c.name,
              }))}
              value={selectedContactId || null}
              onChange={(val) => {
                const newId =
                  typeof val === "number"
                    ? val
                    : parseInt(String(val), 10) || 0;
                setSelectedContactId(newId);
              }}
              placeholder="Select a contact..."
              searchPlaceholder="Search contacts..."
              loading={loadingContacts}
              disabled={loadingContacts}
              clearable={false}
              size="md"
            />
          </div>

          {/* Validation Error */}
          {validationError && (
            <div className="p-3 text-sm text-red-600 bg-red-50 dark:bg-red-900/20 dark:text-red-400 rounded-lg">
              {validationError}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={
              saving ||
              !selectedPurpose ||
              selectedContactId <= 0 ||
              !!validationError
            }
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {saving && <FaSpinner className="animate-spin w-4 h-4" />}
            {saving ? "Adding..." : "Add Purpose"}
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
  // State for fetched contact data from contact model
  const [loading, setLoading] = useState(false);
  const [emails, setEmails] = useState<
    { id: number; name: string; value: string; is_primary?: boolean }[]
  >([]);
  const [phones, setPhones] = useState<
    { id: number; name: string; value: string; is_primary?: boolean }[]
  >([]);
  const [domains, setDomains] = useState<
    { id: number; name: string; value: string; is_primary?: boolean }[]
  >([]);
  const [addresses, setAddresses] = useState<
    { id: number; name: string; full: string }[]
  >([]);

  // Fetch contact data from API using contact_id
  useEffect(() => {
    const fetchContactData = async () => {
      if (!contact?.contact_id || contact.contact_id <= 0) {
        setEmails([]);
        setPhones([]);
        setDomains([]);
        setAddresses([]);
        return;
      }

      setLoading(true);
      try {
        const result = await getRecord("contact", contact.contact_id);
        const data = result?.record || result;

        // Contact model returns data in "communications" object
        const comms = data?.communications;

        if (comms) {
          // Map emails from communications.emails
          setEmails(
            (comms.emails ?? []).map((e: any) => ({
              id: e.id ?? 0,
              name: e.name ?? "",
              value: e.email ?? e.address ?? "",
              is_primary: e.is_primary ?? false,
            })),
          );

          // Map phones from communications.phones
          setPhones(
            (comms.phones ?? []).map((p: any) => ({
              id: p.id ?? 0,
              name: p.name ?? "",
              value: p.number ?? p.phone ?? "",
              is_primary: p.is_primary ?? false,
            })),
          );

          // Map domains from communications.domains
          setDomains(
            (comms.domains ?? []).map((d: any) => ({
              id: d.id ?? 0,
              name: d.name ?? "",
              value: d.domain ?? d.path ?? d.url ?? "",
              is_primary: d.is_primary ?? false,
            })),
          );

          // Map addresses from communications.addresses
          setAddresses(
            (comms.addresses ?? []).map((a: any) => ({
              id: a.id ?? 0,
              name: a.name ?? "",
              full: a.full ?? "",
            })),
          );
        }
      } catch (error) {
        console.error("[ContactBlock] Error fetching contact data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchContactData();
  }, [contact?.contact_id]);

  const displayName =
    contact.attention ||
    (typeof contact.contact_id === "number" && contact.contact_id > 0
      ? `Contact #${contact.contact_id}`
      : "Contact");

  // Check if all fields are empty (from fetched data)
  const hasEmail =
    emails.length > 0 && emails.some((e) => e.value && e.value.trim());
  const hasPhone =
    phones.length > 0 && phones.some((p) => p.value && p.value.trim());
  const hasDomain =
    domains.length > 0 && domains.some((d) => d.value && d.value.trim());
  const hasAddress =
    addresses.length > 0 && addresses.some((a) => a.full && a.full.trim());
  const noDetails = !hasEmail && !hasPhone && !hasDomain && !hasAddress;

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
          {loading ? (
            <div className="flex items-center gap-2 py-2">
              <FaSpinner className="animate-spin w-4 h-4 text-blue-500" />
              <span className="text-xs text-slate-400">Loading...</span>
            </div>
          ) : (
            <>
              {/* Render all emails from fetched data */}
              {emails.length > 0 &&
                emails.map((emailObj, idx) =>
                  emailObj.value ? (
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
                            <span className="flex items-center gap-1">
                              <a
                                href={`mailto:${emailObj.value}`}
                                className="hover:text-blue-500"
                              >
                                {emailObj.value}
                              </a>
                              {emailObj.is_primary && (
                                <FaStar
                                  size={10}
                                  className="text-yellow-500"
                                  title="Primary"
                                />
                              )}
                            </span>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  ) : null,
                )}

              {/* Render all phones from fetched data */}
              {phones.length > 0 &&
                phones.map((phoneObj, idx) =>
                  phoneObj.value ? (
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
                            <span className="flex items-center gap-1">
                              <a
                                href={`tel:${phoneObj.value}`}
                                className="hover:text-blue-500"
                              >
                                {phoneObj.value}
                              </a>
                              {phoneObj.is_primary && (
                                <FaStar
                                  size={10}
                                  className="text-yellow-500"
                                  title="Primary"
                                />
                              )}
                            </span>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  ) : null,
                )}

              {/* Render all domains from fetched data */}
              {domains.length > 0 &&
                domains.map((domainObj, idx) =>
                  domainObj.value ? (
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
                            <span className="flex items-center gap-1">
                              <a
                                href={`https://${domainObj.value}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="hover:text-blue-500"
                              >
                                {domainObj.value}
                              </a>
                              {domainObj.is_primary && (
                                <FaStar
                                  size={10}
                                  className="text-yellow-500"
                                  title="Primary"
                                />
                              )}
                            </span>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  ) : null,
                )}

              {/* Render all addresses from fetched data */}
              {addresses.length > 0 &&
                addresses.map((addrObj, idx) =>
                  addrObj.full ? (
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
                            {/* Address icon placeholder */}
                          </td>
                          <td className="text-left align-middle whitespace-pre-line">
                            {addrObj.full}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  ) : null,
                )}

              {/* If no details at all, show placeholder */}
              {noDetails && !loading && (
                <span className="text-xs italic text-slate-400">
                  No contact details available
                </span>
              )}
            </>
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
  orderId,
  onRemove,
  onEdit,
  onChange,
  onSaveSuccess,
}) => {
  const { ensureWindow, activateWindow } = useWindowManager();
  const [editingContact, setEditingContact] = useState<RefContact | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isAddPurposeModalOpen, setIsAddPurposeModalOpen] = useState(false);

  const grouped = groupContactsByPurpose(contacts);
  //const grouped = groupContactsByPurpose(contacts);

  // Get all unique purposes, with standard ones first
  const allPurposes = new Set([
    ...STANDARD_PURPOSES.filter((p) => grouped[p]?.length > 0 || isEditing),
    ...Object.keys(grouped).filter((p) => !STANDARD_PURPOSES.includes(p)),
  ]);

  const openWindow = (path: string, title: string) => {
    ensureWindow(path, title);
    activateWindow(path);
  };
  const handleEditContact = (contact: RefContact) => {
    console.log("handleEditContact", contact);
    setEditingContact(contact);
    setIsModalOpen(true);
  };
  console.log("contacts edit", contacts);
  const handleSaveContact = (updatedContact: RefContact) => {
    if (onChange) {
      // Find the ORIGINAL contact using editingContact (before any changes)
      // and replace it with the updatedContact (which has new contact_id and purpose)
      const originalId = editingContact ? Number(editingContact.contact_id) : 0;
      const originalPurpose = editingContact?.purpose || "";

      console.log("[handleSaveContact] Finding original:", {
        originalId,
        originalPurpose,
        newId: updatedContact.contact_id,
        newPurpose: updatedContact.purpose,
      });

      let replaced = false;
      const newContacts = contacts.map((c) => {
        // Match by ORIGINAL contact_id and purpose
        if (
          Number(c.contact_id) === originalId &&
          c.purpose === originalPurpose
        ) {
          replaced = true;
          console.log(
            "[handleSaveContact] Replacing contact:",
            c,
            "with:",
            updatedContact,
          );
          // Replace with the updated contact (new contact_id and purpose)
          return {
            ...updatedContact,
          };
        }
        return c;
      });
      // If not found, add as new
      if (!replaced) {
        console.log("[handleSaveContact] Adding as new contact");
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
      console.log("[handleSaveContact] Final contacts:", dedupedContacts);
      onChange([...dedupedContacts]);
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
  console.log("editingContact", editingContact);
  return (
    <>
      {/* Edit Contact Modal */}
      <ContactEditModal
        contact={editingContact}
        isOpen={isModalOpen}
        orderId={orderId}
        onClose={() => {
          setIsModalOpen(false);
          setEditingContact(null);
        }}
        onSave={handleSaveContact}
        onSaveSuccess={onSaveSuccess}
      />

      {/* Add Purpose Modal */}
      <AddPurposeModal
        isOpen={isAddPurposeModalOpen}
        orderId={orderId}
        existingContacts={contacts}
        onClose={() => setIsAddPurposeModalOpen(false)}
        onChange={(newContact) => {
          // Instant local state update - add new contact to existing contacts
          if (onChange) {
            console.log(
              "[RefsLinksContactPanel] Adding new contact to local state:",
              newContact,
            );
            onChange([...contacts, newContact]);
          }
        }}
        onSaveSuccess={onSaveSuccess}
      />

      {/* Add Contact Section - Navigate to Contact List/Add page */}
      {isEditing && (
        <div className="flex justify-end mb-1 px-2">
          <button
            type="button"
            className="me-2 px-3 py-2 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700 transition-colors flex items-center gap-2"
            onClick={() => openWindow("/core/contact/list", "Contact")}
          >
            <FaPlus className="w-3 h-3" />
            Add New Contact
            <FaExternalLinkAlt className="w-3 h-3" />
          </button>
          <button
            type="button"
            className="px-3 py-2 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700 transition-colors flex items-center gap-2"
            onClick={() => setIsAddPurposeModalOpen(true)}
          >
            <FaPlus className="w-3 h-3" />
            Add New Purpose
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
