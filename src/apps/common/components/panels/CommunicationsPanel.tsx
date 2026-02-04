/**
 * CommunicationsPanel - Manage emails, phones, addresses, and domains linked to an entity
 * 
 * This panel makes its own API calls to create/update/delete records via wcapi.
 * On successful API response (200), it calls onChange to update the parent's local state.
 * 
 * Data sources:
 * - refs.links.email: [{id, email, name, type, is_primary}]
 * - refs.links.phone: [{id, number, format, name}]
 * - refs.links.location: [{id, address1, city, state, zip, country, full}]
 * - refs.links.domain: [{id, domain, name, is_primary}]
 * 
 * Role-based access:
 * - View: All roles (default)
 * - Edit: User+ roles (default)
 */
import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { 
  FaEnvelope, FaPhone, FaMapMarkerAlt, FaChevronDown, FaChevronUp, 
  FaPlus, FaEdit, FaTrash, FaStar, FaRegStar, FaExternalLinkAlt, FaGlobe,
  FaSpinner
} from 'react-icons/fa';
import { usePermissions } from './usePermissions';
import type { BasePanelProps, EmailLink, PhoneLink, AddressLink, DomainLink } from './types';

// WCAPI for save/delete operations
import { saveRecord, deleteRecord } from '@/api/wcapi';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CommunicationsData {
  emails?: EmailLink[];
  phones?: PhoneLink[];
  addresses?: AddressLink[];
  domains?: DomainLink[];
}

interface CommunicationsPanelProps extends Omit<BasePanelProps<CommunicationsData>, 'data'> {
  /** Communications data */
  data?: CommunicationsData;
  /** Contact ID to link new records to */
  contactId?: number;
  /** Show only specific types */
  showTypes?: ('email' | 'phone' | 'address' | 'domain')[];
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

const EmailItem: React.FC<EmailItemProps> = ({ email, canEdit, onSetPrimary, onEdit, onDelete }) => (
  <div className="flex items-center gap-2 py-1.5 group hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded px-2 -mx-2">
    <FaEnvelope size={12} className="text-slate-400 flex-shrink-0" />
    <div className="flex-1 min-w-0">
      <div className="flex items-center gap-2">
        <a 
          href={`mailto:${email.email}`} 
          className="text-sm text-blue-600 hover:underline truncate"
        >
          {email.email}
        </a>
        {email.is_primary && (
          <FaStar size={10} className="text-amber-400" title="Primary" />
        )}
      </div>
      {(email.name || email.type) && (
        <p className="text-xs text-slate-400">
          {[email.name, email.type].filter(Boolean).join(' • ')}
        </p>
      )}
    </div>
    {canEdit && (
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        {!email.is_primary && onSetPrimary && (
          <button onClick={onSetPrimary} className="p-1 text-slate-400 hover:text-amber-500" title="Set primary">
            <FaRegStar size={10} />
          </button>
        )}
        {onEdit && (
          <button onClick={onEdit} className="p-1 text-slate-400 hover:text-blue-500" title="Edit">
            <FaEdit size={10} />
          </button>
        )}
        {onDelete && (
          <button onClick={onDelete} className="p-1 text-slate-400 hover:text-red-500" title="Delete">
            <FaTrash size={10} />
          </button>
        )}
      </div>
    )}
  </div>
);

interface PhoneItemProps {
  phone: PhoneLink;
  canEdit: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
}

const PhoneItem: React.FC<PhoneItemProps> = ({ phone, canEdit, onEdit, onDelete }) => (
  <div className="flex items-center gap-2 py-1.5 group hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded px-2 -mx-2">
    <FaPhone size={12} className="text-slate-400 flex-shrink-0" />
    <div className="flex-1 min-w-0">
      <a 
        href={`tel:${phone.number}`}
        className="text-sm text-blue-600 hover:underline"
      >
        {phone.format || phone.number}
      </a>
      {phone.name && (
        <p className="text-xs text-slate-400">{phone.name}</p>
      )}
    </div>
    {canEdit && (
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        {onEdit && (
          <button onClick={onEdit} className="p-1 text-slate-400 hover:text-blue-500" title="Edit">
            <FaEdit size={10} />
          </button>
        )}
        {onDelete && (
          <button onClick={onDelete} className="p-1 text-slate-400 hover:text-red-500" title="Delete">
            <FaTrash size={10} />
          </button>
        )}
      </div>
    )}
  </div>
);

interface AddressItemProps {
  address: AddressLink;
  canEdit: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
}

const AddressItem: React.FC<AddressItemProps> = ({ address, canEdit, onEdit, onDelete }) => {
  const fullAddress = address.full || [
    address.address1,
    [address.city, address.state, address.zip].filter(Boolean).join(', '),
    address.country
  ].filter(Boolean).join(', ');

  const mapsUrl = `https://maps.google.com/?q=${encodeURIComponent(fullAddress)}`;

  return (
    <div className="flex items-start gap-2 py-1.5 group hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded px-2 -mx-2">
      <FaMapMarkerAlt size={12} className="text-slate-400 flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-slate-700 dark:text-slate-300">
          {address.address1}
        </p>
        <p className="text-xs text-slate-500">
          {[address.city, address.state, address.zip].filter(Boolean).join(', ')}
        </p>
        {address.country && address.country !== 'US' && (
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
            {onEdit && (
              <button onClick={onEdit} className="p-1 text-slate-400 hover:text-blue-500" title="Edit">
                <FaEdit size={10} />
              </button>
            )}
            {onDelete && (
              <button onClick={onDelete} className="p-1 text-slate-400 hover:text-red-500" title="Delete">
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

const DomainItem: React.FC<DomainItemProps> = ({ domain, canEdit, onSetPrimary, onEdit, onDelete }) => (
  <div className="flex items-center gap-2 py-1.5 group hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded px-2 -mx-2">
    <FaGlobe size={12} className="text-slate-400 flex-shrink-0" />
    <div className="flex-1 min-w-0">
      <div className="flex items-center gap-2">
        <a 
          href={`https://${domain.domain}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-blue-600 hover:underline truncate"
        >
          {domain.domain}
        </a>
        {domain.is_primary && (
          <FaStar size={10} className="text-amber-400" title="Primary" />
        )}
        {domain.verified && (
          <span className="text-xs text-green-500">✓</span>
        )}
      </div>
      {domain.name && (
        <p className="text-xs text-slate-400">{domain.name}</p>
      )}
    </div>
    {canEdit && (
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        {!domain.is_primary && onSetPrimary && (
          <button onClick={onSetPrimary} className="p-1 text-slate-400 hover:text-amber-500" title="Set primary">
            <FaRegStar size={10} />
          </button>
        )}
        {onEdit && (
          <button onClick={onEdit} className="p-1 text-slate-400 hover:text-blue-500" title="Edit">
            <FaEdit size={10} />
          </button>
        )}
        {onDelete && (
          <button onClick={onDelete} className="p-1 text-slate-400 hover:text-red-500" title="Delete">
            <FaTrash size={10} />
          </button>
        )}
      </div>
    )}
  </div>
);

// ---------------------------------------------------------------------------
// Add/Edit Modals
// ---------------------------------------------------------------------------

interface AddEditModalProps {
  isOpen: boolean;
  type: 'email' | 'phone' | 'address' | 'domain';
  data?: EmailLink | PhoneLink | AddressLink | DomainLink;
  onClose: () => void;
  onSave: (data: EmailLink | PhoneLink | AddressLink | DomainLink) => void;
  isSaving?: boolean;
  contactId?: number;  // Debug: show which contact we're linking to
}

const AddEditModal: React.FC<AddEditModalProps> = ({ isOpen, type, data, onClose, onSave, isSaving = false, contactId }) => {
  const [formData, setFormData] = useState<Record<string, string | boolean>>({});

  React.useEffect(() => {
    if (data) {
      setFormData(data as Record<string, string | boolean>);
    } else {
      setFormData({});
    }
  }, [data, isOpen]);

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
          {data ? 'Edit' : 'Add'} {type}
        </h3>
        <p className="text-xs text-slate-500 mb-4">Contact ID: <strong className="text-blue-600">{contactId ?? 'NOT SET'}</strong></p>

        <form onSubmit={handleSubmit} className="space-y-3">
          {type === 'email' && (
            <>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Email</label>
                <input
                  type="email"
                  value={(formData.email as string) || ''}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  required
                />
              </div>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Label</label>
                <input
                  type="text"
                  value={(formData.name as string) || ''}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Work, Personal, etc."
                  className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={formData.is_primary as boolean || false}
                  onChange={(e) => setFormData({ ...formData, is_primary: e.target.checked })}
                />
                Primary email
              </label>
            </>
          )}

          {type === 'phone' && (
            <>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Number</label>
                <input
                  type="tel"
                  value={(formData.number as string) || ''}
                  onChange={(e) => setFormData({ ...formData, number: e.target.value })}
                  className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  required
                />
              </div>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Label</label>
                <input
                  type="text"
                  value={(formData.name as string) || ''}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Mobile, Office, etc."
                  className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                />
              </div>
            </>
          )}

          {type === 'address' && (
            <>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Street Address</label>
                <input
                  type="text"
                  value={(formData.address1 as string) || ''}
                  onChange={(e) => setFormData({ ...formData, address1: e.target.value })}
                  className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">City</label>
                  <input
                    type="text"
                    value={(formData.city as string) || ''}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">State</label>
                  <input
                    type="text"
                    value={(formData.state as string) || ''}
                    onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                    className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Zip</label>
                  <input
                    type="text"
                    value={(formData.zip as string) || ''}
                    onChange={(e) => setFormData({ ...formData, zip: e.target.value })}
                    className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Country</label>
                  <input
                    type="text"
                    value={(formData.country as string) || ''}
                    onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                    placeholder="US"
                    className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  />
                </div>
              </div>
            </>
          )}

          {type === 'domain' && (
            <>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Domain</label>
                <input
                  type="text"
                  value={(formData.domain as string) || ''}
                  onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
                  placeholder="example.com"
                  className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  required
                />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={formData.is_primary as boolean || false}
                  onChange={(e) => setFormData({ ...formData, is_primary: e.target.checked })}
                />
                Primary domain
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={formData.verified as boolean || false}
                  onChange={(e) => setFormData({ ...formData, verified: e.target.checked })}
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
              {isSaving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
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
  className = '',
  compact = false,
  title = 'Contact Info',
  defaultCollapsed = false,
  showTypes = ['email', 'phone', 'address', 'domain'],
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [isSaving, setIsSaving] = useState(false);
  const [modalState, setModalState] = useState<{
    isOpen: boolean;
    type: 'email' | 'phone' | 'address' | 'domain';
    data?: EmailLink | PhoneLink | AddressLink | DomainLink;
    index?: number;
  }>({ isOpen: false, type: 'email' });

  // Check permissions
  const { canView, canEdit: permCanEdit } = usePermissions({
    panelType: 'communications',
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

  const totalItems = emails.length + phones.length + addresses.length + domains.length;

  // Handlers
  const handleAdd = (type: 'email' | 'phone' | 'address' | 'domain') => {
    setModalState({ isOpen: true, type, data: undefined });
  };

  const handleEdit = (type: 'email' | 'phone' | 'address' | 'domain', item: EmailLink | PhoneLink | AddressLink | DomainLink, index: number) => {
    setModalState({ isOpen: true, type, data: item, index });
  };

  const handleDelete = async (type: 'email' | 'phone' | 'address' | 'domain', index: number) => {
    if (!onChange) return;
    
    // Get the item to delete
    let itemToDelete: { id?: number } | undefined;
    if (type === 'email') itemToDelete = emails[index];
    else if (type === 'phone') itemToDelete = phones[index];
    else if (type === 'address') itemToDelete = addresses[index];
    else if (type === 'domain') itemToDelete = domains[index];
    
    // If item has an id, delete from backend first
    if (itemToDelete?.id) {
      setIsSaving(true);
      try {
        await deleteRecord(type, itemToDelete.id);
        // On success, update local state
        const newData = { ...data };
        if (type === 'email') newData.emails = emails.filter((_, i) => i !== index);
        if (type === 'phone') newData.phones = phones.filter((_, i) => i !== index);
        if (type === 'address') newData.addresses = addresses.filter((_, i) => i !== index);
        if (type === 'domain') newData.domains = domains.filter((_, i) => i !== index);
        onChange(newData);
      } catch (err) {
        console.error(`Failed to delete ${type}:`, err);
        // Could show toast here
      } finally {
        setIsSaving(false);
      }
    } else {
      // No id means it's a new unsaved item, just remove from local state
      const newData = { ...data };
      if (type === 'email') newData.emails = emails.filter((_, i) => i !== index);
      if (type === 'phone') newData.phones = phones.filter((_, i) => i !== index);
      if (type === 'address') newData.addresses = addresses.filter((_, i) => i !== index);
      if (type === 'domain') newData.domains = domains.filter((_, i) => i !== index);
      onChange(newData);
    }
  };

  const handleSetPrimary = async (index: number) => {
    if (!onChange) return;
    const emailToUpdate = emails[index];
    if (!emailToUpdate?.id) return;
    
    setIsSaving(true);
    try {
      // Update the email to be primary via wcapi - always include contact_id
      await saveRecord('email', { 
        id: emailToUpdate.id, 
        is_primary: true,
        contact_id: contactId 
      });
      // On success, update all emails locally
      const newEmails = emails.map((e, i) => ({ ...e, is_primary: i === index }));
      onChange({ ...data, emails: newEmails });
    } catch (err) {
      console.error('Failed to set primary email:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleSave = async (item: EmailLink | PhoneLink | AddressLink | DomainLink) => {
    if (!onChange) return;
    const { type, index } = modalState;
    
    setIsSaving(true);
    try {
      // Build the payload for wcapi - always include contact_id
      const payload: any = { ...item };
      if (contactId) {
        payload.contact_id = contactId;
      } else {
        console.warn('[CommunicationsPanel] No contactId provided!');
      }
      
      console.log('[CommunicationsPanel] handleSave:', { 
        type, 
        contactId, 
        'payload.contact_id': payload.contact_id,
        fullPayload: JSON.stringify(payload)
      });
      
      // Save via wcapi - it handles create vs update based on presence of id
      const result = await saveRecord(type, payload);
      console.log('[CommunicationsPanel] saveRecord result:', result);
      
      // On success (200), format the data for refs.links structure
      // Format: {id, value, name} for email/phone/domain, or full object for address
      const returnedId = result?.record?.id || result?.id || item.id;
      
      let linkItem: any;
      if (type === 'email') {
        // refs.links.email: [{id, value, name, is_primary}]
        linkItem = {
          id: returnedId,
          value: (item as EmailLink).email || payload.email,
          name: (item as EmailLink).name || payload.name || '',
          is_primary: (item as EmailLink).is_primary || false,
          // Keep original fields for display
          email: (item as EmailLink).email || payload.email,
        };
      } else if (type === 'phone') {
        // refs.links.phone: [{id, value, name}]
        linkItem = {
          id: returnedId,
          value: (item as PhoneLink).number || payload.number,
          name: (item as PhoneLink).name || payload.name || '',
          number: (item as PhoneLink).number || payload.number,
        };
      } else if (type === 'domain') {
        // refs.links.domain: [{id, value, name, is_primary}]
        linkItem = {
          id: returnedId,
          value: (item as DomainLink).domain || payload.domain,
          name: (item as DomainLink).name || payload.name || '',
          is_primary: (item as DomainLink).is_primary || false,
          domain: (item as DomainLink).domain || payload.domain,
        };
      } else if (type === 'address') {
        // refs.links.address: [{id, name, full, address1, city, state, zip, country}]
        const addr = item as AddressLink;
        linkItem = {
          id: returnedId,
          name: addr.name || payload.name || '',
          full: addr.full || `${addr.address1 || ''}\n${addr.city || ''}, ${addr.state || ''} ${addr.zip || ''}`.trim(),
          address1: addr.address1 || payload.address1 || '',
          city: addr.city || payload.city || '',
          state: addr.state || payload.state || '',
          zip: addr.zip || payload.zip || '',
          country: addr.country || payload.country || '',
        };
      }
      
      // Update local state with the formatted link item
      const newData = { ...data };
      if (type === 'email') {
        const arr = [...emails];
        if (index !== undefined) arr[index] = linkItem as EmailLink;
        else arr.push(linkItem as EmailLink);
        newData.emails = arr;
      } else if (type === 'phone') {
        const arr = [...phones];
        if (index !== undefined) arr[index] = linkItem as PhoneLink;
        else arr.push(linkItem as PhoneLink);
        newData.phones = arr;
      } else if (type === 'address') {
        const arr = [...addresses];
        if (index !== undefined) arr[index] = linkItem as AddressLink;
        else arr.push(linkItem as AddressLink);
        newData.addresses = arr;
      } else if (type === 'domain') {
        const arr = [...domains];
        if (index !== undefined) arr[index] = linkItem as DomainLink;
        else arr.push(linkItem as DomainLink);
        newData.domains = arr;
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
    <div className={`bg-white dark:bg-slate-800 rounded-lg border border-teal-200 dark:border-teal-800 ${className}`}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-teal-50 dark:bg-teal-900/20 border-b border-teal-200 dark:border-teal-800 cursor-pointer rounded-t-lg"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaEnvelope className="text-teal-500" size={14} />
          <h3 className="text-sm font-semibold text-teal-700 dark:text-teal-300">{title}</h3>
          {totalItems > 0 && (
            <span className="px-1.5 py-0.5 text-xs bg-teal-100 dark:bg-teal-900 text-teal-600 dark:text-teal-300 rounded-full">
              {totalItems}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isCollapsed ? <FaChevronDown size={12} /> : <FaChevronUp size={12} />}
        </div>
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className={compact ? 'p-2' : 'p-4'}>
          {totalItems === 0 ? (
            <div className="text-center py-4 text-slate-400 text-sm">
              <FaEnvelope size={24} className="mx-auto mb-2 opacity-50" />
              <p>No contact information</p>
              {canEdit && (
                <div className="flex justify-center gap-2 mt-2 text-xs">
                  {showTypes.includes('email') && (
                    <button onClick={() => handleAdd('email')} className="text-teal-600 hover:underline">+ Email</button>
                  )}
                  {showTypes.includes('phone') && (
                    <button onClick={() => handleAdd('phone')} className="text-teal-600 hover:underline">+ Phone</button>
                  )}
                  {showTypes.includes('address') && (
                    <button onClick={() => handleAdd('address')} className="text-teal-600 hover:underline">+ Address</button>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {/* Emails */}
              {showTypes.includes('email') && emails.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider">Email</h4>
                    {canEdit && (
                      <button onClick={() => handleAdd('email')} className="p-1 text-teal-600 hover:bg-teal-50 dark:hover:bg-teal-900/20 rounded">
                        <FaPlus size={10} />
                      </button>
                    )}
                  </div>
                  {emails.map((email, idx) => (
                    <EmailItem
                      key={email.id || idx}
                      email={email}
                      canEdit={canEdit}
                      onSetPrimary={() => handleSetPrimary(idx)}
                      onEdit={() => handleEdit('email', email, idx)}
                      onDelete={() => handleDelete('email', idx)}
                    />
                  ))}
                </div>
              )}

              {/* Phones */}
              {showTypes.includes('phone') && phones.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider">Phone</h4>
                    {canEdit && (
                      <button onClick={() => handleAdd('phone')} className="p-1 text-teal-600 hover:bg-teal-50 dark:hover:bg-teal-900/20 rounded">
                        <FaPlus size={10} />
                      </button>
                    )}
                  </div>
                  {phones.map((phone, idx) => (
                    <PhoneItem
                      key={phone.id || idx}
                      phone={phone}
                      canEdit={canEdit}
                      onEdit={() => handleEdit('phone', phone, idx)}
                      onDelete={() => handleDelete('phone', idx)}
                    />
                  ))}
                </div>
              )}

              {/* Addresses */}
              {showTypes.includes('address') && addresses.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider">Address</h4>
                    {canEdit && (
                      <button onClick={() => handleAdd('address')} className="p-1 text-teal-600 hover:bg-teal-50 dark:hover:bg-teal-900/20 rounded">
                        <FaPlus size={10} />
                      </button>
                    )}
                  </div>
                  {addresses.map((addr, idx) => (
                    <AddressItem
                      key={addr.id || idx}
                      address={addr}
                      canEdit={canEdit}
                      onEdit={() => handleEdit('address', addr, idx)}
                      onDelete={() => handleDelete('address', idx)}
                    />
                  ))}
                </div>
              )}

              {/* Domains */}
              {showTypes.includes('domain') && domains.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Domains
                    </h4>
                    {canEdit && (
                      <button
                        onClick={() => handleAdd('domain')}
                        className="text-xs text-teal-600 hover:text-teal-700 dark:text-teal-400"
                      >
                        + Add
                      </button>
                    )}
                  </div>
                  {domains.map((domain, idx) => (
                    <DomainItem
                      key={domain.domain || idx}
                      domain={domain}
                      canEdit={canEdit}
                      onEdit={() => handleEdit('domain', domain, idx)}
                      onDelete={() => handleDelete('domain', idx)}
                    />
                  ))}
                </div>
              )}

              {/* Add buttons for empty sections */}
              {canEdit && (
                <div className="flex gap-2 pt-2 border-t border-slate-100 dark:border-slate-700">
                  {showTypes.includes('email') && emails.length === 0 && (
                    <button onClick={() => handleAdd('email')} className="text-xs text-teal-600 hover:underline">+ Email</button>
                  )}
                  {showTypes.includes('phone') && phones.length === 0 && (
                    <button onClick={() => handleAdd('phone')} className="text-xs text-teal-600 hover:underline">+ Phone</button>
                  )}
                  {showTypes.includes('address') && addresses.length === 0 && (
                    <button onClick={() => handleAdd('address')} className="text-xs text-teal-600 hover:underline">+ Address</button>
                  )}
                  {showTypes.includes('domain') && domains.length === 0 && (
                    <button onClick={() => handleAdd('domain')} className="text-xs text-teal-600 hover:underline">+ Domain</button>
                  )}
                </div>
              )}
            </div>
          )}
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
