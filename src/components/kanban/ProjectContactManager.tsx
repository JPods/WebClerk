import { useState, useEffect, useCallback, useMemo, ChangeEvent } from "react";
import { getRecords, saveRecord } from "../../api/wcapi";
import { useAuth } from "../../hooks/useAuth";

/**
 * ProjectContactManager
 * 
 * A modal component for managing the contact list associated with a project.
 * Contacts are stored in project.refs.links.contact as an array of {id, attention} objects.
 * 
 * Role-based access:
 * - Users with "admin", "manager", or "owner" roles can add/remove contacts
 * - Other users can view but not modify the list
 */

// Contact as stored in project.refs.links.contact
export interface ProjectContact {
  id: number | string;
  attention?: string;
}

// Full contact record from API
interface ContactRecord {
  id: number | string;
  attention?: string;
  is_active?: boolean;
  role?: string;
  email?: string;
  is_staff?: boolean;
}

interface ProjectContactManagerProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  projectName: string;
  currentContacts: ProjectContact[];
  onContactsUpdated: (contacts: ProjectContact[]) => void;
}

// Roles that can modify project contacts
const EDITABLE_ROLES = ["admin", "manager", "owner", "Admin", "Manager", "Owner"];

const hasEditPermission = (role: string | string[] | undefined): boolean => {
  if (!role) return false;
  const roles = Array.isArray(role) ? role : [role];
  return roles.some((r) => EDITABLE_ROLES.includes(r));
};

export const ProjectContactManager: React.FC<ProjectContactManagerProps> = ({
  isOpen,
  onClose,
  projectId,
  projectName,
  currentContacts,
  onContactsUpdated,
}) => {
  const { user } = useAuth();
  const canEdit = hasEditPermission(user?.role);

  // Local state for contacts being edited
  const [contacts, setContacts] = useState<ProjectContact[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // State for available contacts (for adding new ones)
  const [availableContacts, setAvailableContacts] = useState<ContactRecord[]>([]);
  const [isLoadingAvailable, setIsLoadingAvailable] = useState(false);
  const [availableError, setAvailableError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  // Initialize contacts when modal opens
  useEffect(() => {
    if (isOpen) {
      setContacts([...currentContacts]);
      setSaveError(null);
      setSearchQuery("");
    }
  }, [isOpen, currentContacts]);

  // Fetch all available contacts when modal opens
  const fetchAvailableContacts = useCallback(async () => {
    setIsLoadingAvailable(true);
    setAvailableError(null);
    try {
      const response = await getRecords("contact", { is_active: true, limit: 500 });
      const records = response?.results || [];
      const contactList: ContactRecord[] = records
        .filter((r: Record<string, unknown>) => r.id !== undefined && r.id !== null)
        .map((r: Record<string, unknown>) => ({
          id: r.id as number | string,
          attention: typeof r.attention === "string" ? r.attention : undefined,
          is_active: r.is_active === true || r.is_active === "true",
          role: typeof r.role === "string" ? r.role : undefined,
          email: typeof r.email === "string" ? r.email : undefined,
          is_staff: r.is_staff === true || r.is_staff === "true",
        }));
      setAvailableContacts(contactList);
    } catch (error) {
      console.error("Failed to fetch available contacts:", error);
      setAvailableError("Failed to load available contacts");
    } finally {
      setIsLoadingAvailable(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen && canEdit) {
      fetchAvailableContacts();
    }
  }, [isOpen, canEdit, fetchAvailableContacts]);

  // Current contact IDs as a set for quick lookup
  const currentContactIds = useMemo(
    () => new Set(contacts.map((c) => String(c.id))),
    [contacts]
  );

  // Filter available contacts that are not already in the project
  const filteredAvailableContacts = useMemo(() => {
    const filtered = availableContacts.filter(
      (c) => !currentContactIds.has(String(c.id))
    );
    if (!searchQuery.trim()) return filtered;
    const query = searchQuery.toLowerCase();
    return filtered.filter(
      (c) =>
        c.attention?.toLowerCase().includes(query) ||
        c.email?.toLowerCase().includes(query) ||
        String(c.id).includes(query)
    );
  }, [availableContacts, currentContactIds, searchQuery]);

  // Add a contact to the project
  const handleAddContact = (contact: ContactRecord) => {
    if (!canEdit) return;
    setContacts((prev) => [
      ...prev,
      { id: contact.id, attention: contact.attention },
    ]);
  };

  // Remove a contact from the project
  const handleRemoveContact = (contactId: number | string) => {
    if (!canEdit) return;
    setContacts((prev) => prev.filter((c) => String(c.id) !== String(contactId)));
  };

  // Save changes to the project
  const handleSave = async () => {
    if (!canEdit) return;
    setIsSaving(true);
    setSaveError(null);

    try {
      // Build the payload to update project.refs.links.contact
      const payload = {
        id: Number(projectId),
        refs: {
          links: {
            contact: contacts.map((c) => ({
              id: Number(c.id),
              attention: c.attention || "",
            })),
          },
        },
      };

      await saveRecord("project", payload);
      onContactsUpdated(contacts);
      onClose();
    } catch (error) {
      console.error("Failed to save project contacts:", error);
      const message =
        (error as any)?.response?.data?.message ||
        (error as any)?.message ||
        "Failed to save contacts. Please try again.";
      setSaveError(message);
    } finally {
      setIsSaving(false);
    }
  };

  // Check if there are unsaved changes
  const hasChanges = useMemo(() => {
    if (contacts.length !== currentContacts.length) return true;
    const currentIds = new Set(currentContacts.map((c) => String(c.id)));
    return contacts.some((c) => !currentIds.has(String(c.id)));
  }, [contacts, currentContacts]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/50 p-4">
      <div className="relative w-full max-w-2xl rounded-2xl bg-white shadow-xl dark:bg-gray-900">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 dark:border-gray-700">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Manage Project Contacts
            </h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {projectName}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-300"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="max-h-[60vh] overflow-y-auto px-6 py-4">
          {saveError && (
            <div className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/30 dark:text-rose-200">
              {saveError}
            </div>
          )}

          {/* Current Contacts Section */}
          <div className="mb-6">
            <h3 className="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">
              Current Contacts ({contacts.length})
            </h3>
            {contacts.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                No contacts assigned to this project.
              </p>
            ) : (
              <div className="space-y-2">
                {contacts.map((contact) => (
                  <div
                    key={contact.id}
                    className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 px-4 py-2 dark:border-gray-700 dark:bg-gray-800"
                  >
                    <div>
                      <span className="text-sm font-medium text-gray-900 dark:text-white">
                        {contact.attention || `Contact #${contact.id}`}
                      </span>
                      <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                        ID: {contact.id}
                      </span>
                    </div>
                    {canEdit && (
                      <button
                        type="button"
                        onClick={() => handleRemoveContact(contact.id)}
                        className="rounded p-1 text-gray-400 transition hover:bg-rose-100 hover:text-rose-600 dark:hover:bg-rose-900/30 dark:hover:text-rose-400"
                        title="Remove contact"
                      >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Add Contacts Section - Only visible if user can edit */}
          {canEdit && (
            <div>
              <h3 className="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">
                Add Contacts
              </h3>

              {/* Search Input */}
              <div className="mb-3">
                <input
                  type="text"
                  placeholder="Search contacts by name or email..."
                  value={searchQuery}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
                  className="w-full rounded-lg border border-gray-200 px-4 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                />
              </div>

              {availableError && (
                <p className="mb-3 text-sm text-rose-600 dark:text-rose-400">
                  {availableError}
                </p>
              )}

              {isLoadingAvailable ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Loading available contacts...
                </p>
              ) : filteredAvailableContacts.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {searchQuery ? "No matching contacts found." : "All contacts are already assigned."}
                </p>
              ) : (
                <div className="max-h-48 space-y-2 overflow-y-auto">
                  {filteredAvailableContacts.slice(0, 50).map((contact) => (
                    <div
                      key={contact.id}
                      className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-2 dark:border-gray-700 dark:bg-gray-800"
                    >
                      <div>
                        <span className="text-sm font-medium text-gray-900 dark:text-white">
                          {contact.attention || `Contact #${contact.id}`}
                        </span>
                        {contact.email && (
                          <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                            {contact.email}
                          </span>
                        )}
                        {contact.role && (
                          <span className="ml-2 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                            {contact.role}
                          </span>
                        )}
                      </div>
                      <button
                        type="button"
                        onClick={() => handleAddContact(contact)}
                        className="rounded p-1 text-gray-400 transition hover:bg-emerald-100 hover:text-emerald-600 dark:hover:bg-emerald-900/30 dark:hover:text-emerald-400"
                        title="Add contact"
                      >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                      </button>
                    </div>
                  ))}
                  {filteredAvailableContacts.length > 50 && (
                    <p className="text-center text-xs text-gray-500 dark:text-gray-400">
                      Showing first 50 results. Use search to narrow down.
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Read-only notice for non-editors */}
          {!canEdit && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700 dark:border-amber-800 dark:bg-amber-900/30 dark:text-amber-200">
              <p>
                <strong>View Only:</strong> Your role does not permit editing project contacts.
                Contact an administrator or project manager to make changes.
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t border-gray-200 px-6 py-4 dark:border-gray-700">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            {canEdit ? "Cancel" : "Close"}
          </button>
          {canEdit && (
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving || !hasChanges}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSaving ? "Saving..." : "Save Changes"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProjectContactManager;
