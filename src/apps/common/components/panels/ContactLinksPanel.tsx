/**
 * ContactLinksPanel - Display and manage entity contact relationships
 * 
 * Data source: refs.links.contact
 * Based on Django RefsMixin with LINK_DENORMALIZE_FIELDS.contact
 * 
 * Role-based access:
 * - View: All roles (default)
 * - Edit: User+ roles (default)
 */
import React, { useState } from 'react';
import { 
  FaUsers, FaChevronDown, FaChevronUp, FaPlus, FaTrash, 
  FaUser, FaEnvelope, FaPhone, FaBuilding, FaUserTag
} from 'react-icons/fa';
import { usePermissions } from './usePermissions';
import type { BasePanelProps } from './types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ContactLink {
  id: number;
  email?: string;
  name_first?: string;
  name_last?: string;
  company?: string;
  title?: string;
  role?: string;
  phone?: string;
  // Derived or display fields
  name?: string;
  isPrimary?: boolean;
}

interface ContactLinksPanelProps extends Omit<BasePanelProps<ContactLink[]>, 'data'> {
  /** Contact links array */
  data?: ContactLink[];
  /** Callback when a contact is clicked */
  onContactClick?: (contact: ContactLink) => void;
  /** Callback to search/add contacts */
  onSearchContacts?: (query: string) => Promise<ContactLink[]>;
}

// ---------------------------------------------------------------------------
// Contact Card Component
// ---------------------------------------------------------------------------

interface ContactCardProps {
  contact: ContactLink;
  canEdit: boolean;
  onClick?: () => void;
  onDelete?: () => void;
  compact?: boolean;
}

const ContactCard: React.FC<ContactCardProps> = ({ 
  contact, 
  canEdit, 
  onClick, 
  onDelete,
  compact = false 
}) => {
  const displayName = contact.name || 
    [contact.name_first, contact.name_last].filter(Boolean).join(' ') || 
    contact.email || 
    `Contact #${contact.id}`;

  return (
    <div 
      className={`flex items-center gap-3 ${compact ? 'p-2' : 'p-3'} hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded-lg border border-slate-100 dark:border-slate-700 group ${onClick ? 'cursor-pointer' : ''}`}
      onClick={onClick}
    >
      {/* Avatar */}
      <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0">
        <FaUser className="text-blue-500" size={16} />
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-slate-700 dark:text-slate-300 truncate">
            {displayName}
          </p>
          {contact.isPrimary && (
            <span className="px-1.5 py-0.5 text-xs bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded">
              Primary
            </span>
          )}
        </div>
        
        {(contact.title || contact.company || contact.role) && (
          <p className="text-xs text-slate-500 truncate flex items-center gap-1">
            {contact.title && <span>{contact.title}</span>}
            {contact.title && contact.company && <span>@</span>}
            {contact.company && (
              <span className="flex items-center gap-1">
                <FaBuilding size={10} />
                {contact.company}
              </span>
            )}
            {contact.role && (
              <span className="flex items-center gap-1 ml-2">
                <FaUserTag size={10} />
                {contact.role}
              </span>
            )}
          </p>
        )}

        {!compact && (
          <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
            {contact.email && (
              <span className="flex items-center gap-1">
                <FaEnvelope size={10} />
                {contact.email}
              </span>
            )}
            {contact.phone && (
              <span className="flex items-center gap-1">
                <FaPhone size={10} />
                {contact.phone}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Actions */}
      {canEdit && onDelete && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="p-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded opacity-0 group-hover:opacity-100 transition-opacity"
          title="Remove contact"
        >
          <FaTrash size={12} />
        </button>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Add Contact Modal
// ---------------------------------------------------------------------------

interface AddContactModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (contact: ContactLink) => void;
  onSearch?: (query: string) => Promise<ContactLink[]>;
  existingIds: number[];
}

const AddContactModal: React.FC<AddContactModalProps> = ({ 
  isOpen, 
  onClose, 
  onAdd, 
  onSearch,
  existingIds 
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<ContactLink[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [manualMode, setManualMode] = useState(false);
  const [manualContact, setManualContact] = useState<Partial<ContactLink>>({});

  React.useEffect(() => {
    if (!isOpen) {
      setSearchQuery('');
      setSearchResults([]);
      setManualMode(false);
      setManualContact({});
    }
  }, [isOpen]);

  const handleSearch = async () => {
    if (!searchQuery.trim() || !onSearch) return;
    setIsSearching(true);
    try {
      const results = await onSearch(searchQuery);
      // Filter out already linked contacts
      setSearchResults(results.filter(c => !existingIds.includes(c.id)));
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleManualAdd = () => {
    if (!manualContact.name_first && !manualContact.name_last && !manualContact.email) return;
    onAdd({
      id: Date.now(),
      ...manualContact,
    } as ContactLink);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-slate-800 rounded-lg p-4 w-96 max-w-full mx-4 max-h-[80vh] overflow-y-auto">
        <h3 className="text-sm font-semibold mb-4 text-slate-700 dark:text-slate-200">
          Add Contact
        </h3>

        {!manualMode ? (
          <>
            {/* Search mode */}
            <div className="flex gap-2 mb-3">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Search contacts..."
                className="flex-1 px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                autoFocus
              />
              <button
                onClick={handleSearch}
                disabled={isSearching || !onSearch}
                className="px-3 py-1.5 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
              >
                {isSearching ? '...' : 'Search'}
              </button>
            </div>

            {/* Search results */}
            {searchResults.length > 0 && (
              <div className="space-y-2 mb-3 max-h-48 overflow-y-auto">
                {searchResults.map((contact) => (
                  <div
                    key={contact.id}
                    className="flex items-center gap-2 p-2 hover:bg-slate-50 dark:hover:bg-slate-700 rounded cursor-pointer"
                    onClick={() => {
                      onAdd(contact);
                      onClose();
                    }}
                  >
                    <FaUser size={12} className="text-slate-400" />
                    <span className="text-sm">
                      {contact.name || [contact.name_first, contact.name_last].filter(Boolean).join(' ')}
                    </span>
                    {contact.email && <span className="text-xs text-slate-400">({contact.email})</span>}
                  </div>
                ))}
              </div>
            )}

            {searchResults.length === 0 && searchQuery && !isSearching && (
              <p className="text-sm text-slate-400 text-center py-2">No contacts found</p>
            )}

            <button
              onClick={() => setManualMode(true)}
              className="w-full text-center text-sm text-blue-600 hover:underline mt-2"
            >
              + Add manually
            </button>
          </>
        ) : (
          <>
            {/* Manual entry mode */}
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">First Name</label>
                  <input
                    type="text"
                    value={manualContact.name_first || ''}
                    onChange={(e) => setManualContact({ ...manualContact, name_first: e.target.value })}
                    className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Last Name</label>
                  <input
                    type="text"
                    value={manualContact.name_last || ''}
                    onChange={(e) => setManualContact({ ...manualContact, name_last: e.target.value })}
                    className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Email</label>
                <input
                  type="email"
                  value={manualContact.email || ''}
                  onChange={(e) => setManualContact({ ...manualContact, email: e.target.value })}
                  className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Company</label>
                <input
                  type="text"
                  value={manualContact.company || ''}
                  onChange={(e) => setManualContact({ ...manualContact, company: e.target.value })}
                  className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Role</label>
                <input
                  type="text"
                  value={manualContact.role || ''}
                  onChange={(e) => setManualContact({ ...manualContact, role: e.target.value })}
                  className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  placeholder="e.g., Buyer, Approver, Ship To..."
                />
              </div>
            </div>

            <div className="flex justify-between items-center mt-4">
              <button
                onClick={() => setManualMode(false)}
                className="text-sm text-slate-600 hover:underline"
              >
                ← Back to search
              </button>
              <button
                onClick={handleManualAdd}
                className="px-3 py-1.5 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
              >
                Add Contact
              </button>
            </div>
          </>
        )}

        <div className="flex justify-end mt-4 pt-3 border-t dark:border-slate-700">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700 rounded"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main ContactLinksPanel Component
// ---------------------------------------------------------------------------

const ContactLinksPanel: React.FC<ContactLinksPanelProps> = ({
  entityType: _entityType,
  entityId: _entityId,
  data = [],
  onChange,
  onContactClick,
  onSearchContacts,
  readOnly = false,
  viewRoles,
  editRoles,
  className = '',
  compact = false,
  title = 'Contacts',
  defaultCollapsed = false,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [showModal, setShowModal] = useState(false);

  // Check permissions
  const { canView, canEdit: permCanEdit } = usePermissions({
    panelType: 'contactLinks',
    viewRoles,
    editRoles,
    forceReadOnly: readOnly,
  });

  const canEdit = permCanEdit && !!onChange;

  if (!canView) return null;

  const handleAdd = (contact: ContactLink) => {
    if (!onChange) return;
    // Check for duplicates
    if (data.some(c => c.id === contact.id)) return;
    onChange([...data, contact]);
  };

  const handleDelete = (index: number) => {
    if (!onChange) return;
    onChange(data.filter((_, i) => i !== index));
  };

  // Group contacts by role if available
  const groupedContacts = data.reduce<Record<string, ContactLink[]>>((acc, contact) => {
    const group = contact.role || 'Other';
    if (!acc[group]) acc[group] = [];
    acc[group].push(contact);
    return acc;
  }, {});

  const hasGroups = Object.keys(groupedContacts).length > 1;

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-lg border border-blue-200 dark:border-blue-800 ${className}`}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-800 cursor-pointer rounded-t-lg"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaUsers className="text-blue-500" size={14} />
          <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-300">{title}</h3>
          {data.length > 0 && (
            <span className="px-1.5 py-0.5 text-xs bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300 rounded-full">
              {data.length}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {canEdit && !isCollapsed && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowModal(true);
              }}
              className="p-1 text-blue-600 hover:bg-blue-100 dark:hover:bg-blue-800 rounded"
              title="Add contact"
            >
              <FaPlus size={12} />
            </button>
          )}
          {isCollapsed ? <FaChevronDown size={12} /> : <FaChevronUp size={12} />}
        </div>
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className={compact ? 'p-2' : 'p-4'}>
          {data.length === 0 ? (
            <div className="text-center py-4 text-slate-400 text-sm">
              <FaUsers size={24} className="mx-auto mb-2 opacity-50" />
              <p>No contacts linked</p>
              {canEdit && (
                <button
                  onClick={() => setShowModal(true)}
                  className="mt-2 text-blue-600 hover:underline text-xs"
                >
                  + Add first contact
                </button>
              )}
            </div>
          ) : hasGroups ? (
            // Grouped view
            <div className="space-y-4">
              {Object.entries(groupedContacts).map(([role, contacts]) => (
                <div key={role}>
                  <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">{role}</h4>
                  <div className="space-y-2">
                    {contacts.map((contact, index) => (
                      <ContactCard
                        key={contact.id || index}
                        contact={contact}
                        canEdit={canEdit}
                        compact={compact}
                        onClick={onContactClick ? () => onContactClick(contact) : undefined}
                        onDelete={() => handleDelete(data.indexOf(contact))}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            // Flat view
            <div className="space-y-2">
              {data.map((contact, index) => (
                <ContactCard
                  key={contact.id || index}
                  contact={contact}
                  canEdit={canEdit}
                  compact={compact}
                  onClick={onContactClick ? () => onContactClick(contact) : undefined}
                  onDelete={() => handleDelete(index)}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Add Modal */}
      <AddContactModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        onAdd={handleAdd}
        onSearch={onSearchContacts}
        existingIds={data.map(c => c.id)}
      />
    </div>
  );
};

export default ContactLinksPanel;
