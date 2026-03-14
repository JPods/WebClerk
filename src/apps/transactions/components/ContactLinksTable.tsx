/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * ContactLinksTable - Display contact links in a tabular format with draggable columns
 * This component provides a detailed table view of contacts linked to a transaction.
 * Clicking a contact ID or name navigates to the contact edit page.
 */
import React, { useMemo, useState, useCallback, useRef, type ReactNode, type DragEvent as ReactDragEvent } from 'react';
import { useNavigate } from 'react-router-dom';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** A raw contact link record from refs.links.contact */
type ContactLinkRecord = Record<string, unknown> & {
  id?: number | string;
  contact?: Record<string, unknown>;
};

/** Display-ready row after resolving fields from the raw record */
interface ContactLinkDisplayRow {
  id: number | null;
  alias: string;
  purpose: string;
  name: string;
  company: string;
  role: string;
  email: string;
  phone: string;
  domain: string;
  address: string;
  city: string;
  state: string;
  zip: string;
  raw: ContactLinkRecord;
}

/** Available column keys */
type ContactColumnKey = 'id' | 'alias' | 'purpose' | 'name' | 'company' | 'role' | 'email' | 'phone' | 'domain' | 'address' | 'city' | 'state' | 'zip';

/** Column definition with render function */
interface ContactLinkColumnDef {
  key: ContactColumnKey;
  label: string;
  render: (row: ContactLinkDisplayRow) => ReactNode;
}

// ---------------------------------------------------------------------------
// Column Definitions
// ---------------------------------------------------------------------------

const CONTACT_LINK_COLUMN_DEFS: ContactLinkColumnDef[] = [
  {
    key: 'id',
    label: 'id',
    render: (row) => row.id ? (
      <span className="text-blue-600 hover:underline dark:text-blue-400 cursor-pointer font-medium">
        {row.id}
      </span>
    ) : '--',
  },
  {
    key: 'alias',
    label: 'ida_contact',
    render: (row) => row.alias || '--',
  },
  {
    key: 'name',
    label: 'display_name',
    render: (row) => row.id ? (
      <span className="text-blue-600 hover:underline dark:text-blue-400 cursor-pointer">
        {row.name}
      </span>
    ) : row.name,
  },
  {
    key: 'company',
    label: 'company',
    render: (row) => row.company || '--',
  },
  {
    key: 'role',
    label: 'role',
    render: (row) => row.role || '--',
  },
  {
    key: 'purpose',
    label: 'purpose',
    render: (row) => row.purpose || '--',
  },
  {
    key: 'email',
    label: 'email',
    render: (row) => (row.email ? (
      <a href={`mailto:${row.email}`} className="text-blue-600 hover:underline dark:text-blue-400">
        {row.email}
      </a>
    ) : '--'),
  },
  {
    key: 'phone',
    label: 'phone',
    render: (row) => (row.phone ? (
      <a href={`tel:${row.phone}`} className="text-blue-600 hover:underline dark:text-blue-400">
        {row.phone}
      </a>
    ) : '--'),
  },
  {
    key: 'domain',
    label: 'domain',
    render: (row) => row.domain || '--',
  },
  {
    key: 'address',
    label: 'address',
    render: (row) => row.address || '--',
  },
  {
    key: 'city',
    label: 'city',
    render: (row) => row.city || '--',
  },
  {
    key: 'state',
    label: 'state',
    render: (row) => row.state || '--',
  },
  {
    key: 'zip',
    label: 'zip',
    render: (row) => row.zip || '--',
  },
];

const CONTACT_LINK_COLUMN_LOOKUP: Record<ContactColumnKey, ContactLinkColumnDef> = 
  CONTACT_LINK_COLUMN_DEFS.reduce((acc, def) => {
    acc[def.key] = def;
    return acc;
  }, {} as Record<ContactColumnKey, ContactLinkColumnDef>);

const CONTACT_LINK_CELL_CLASS: Record<ContactColumnKey, string> = {
  id: 'px-3 py-2 text-gray-800 dark:text-gray-100',
  alias: 'px-3 py-2 text-gray-600 dark:text-gray-300',
  name: 'px-3 py-2 text-gray-800 dark:text-gray-100 font-medium',
  company: 'px-3 py-2 text-gray-600 dark:text-gray-300',
  role: 'px-3 py-2 text-gray-600 dark:text-gray-300',
  purpose: 'px-3 py-2 text-gray-600 dark:text-gray-300',
  email: 'px-3 py-2 text-gray-600 dark:text-gray-300',
  phone: 'px-3 py-2 text-gray-600 dark:text-gray-300',
  domain: 'px-3 py-2 text-gray-600 dark:text-gray-300',
  address: 'px-3 py-2 text-gray-600 dark:text-gray-300',
  city: 'px-3 py-2 text-gray-600 dark:text-gray-300',
  state: 'px-3 py-2 text-gray-600 dark:text-gray-300',
  zip: 'px-3 py-2 text-gray-600 dark:text-gray-300',
};

// ---------------------------------------------------------------------------
// Field Resolution Helpers
// ---------------------------------------------------------------------------

function resolveStringField(obj: Record<string, unknown>, keys: string[]): string {
  for (const key of keys) {
    const value = obj[key];
    if (typeof value === 'string' && value.trim()) {
      return value.trim();
    }
  }
  return '';
}

function resolveContactRecord(entry: ContactLinkRecord): Record<string, unknown> {
  if (entry.contact && typeof entry.contact === 'object') {
    return entry.contact;
  }
  return entry;
}

function resolveContactId(entry: ContactLinkRecord): number | null {
  const record = resolveContactRecord(entry);
  const candidates = [
    entry.id,
    record.id,
    record.contact_id,
    record.id_contact,
    record.contactId,
  ];
  for (const candidate of candidates) {
    if (typeof candidate === 'number' && Number.isFinite(candidate) && candidate > 0) {
      return candidate;
    }
    if (typeof candidate === 'string') {
      const parsed = Number.parseInt(candidate, 10);
      if (Number.isFinite(parsed) && parsed > 0) {
        return parsed;
      }
    }
  }
  return null;
}

function resolveContactName(entry: ContactLinkRecord): string {
  const record = resolveContactRecord(entry);
  const first = resolveStringField(record, ['name_first', 'first_name', 'given_name']);
  const last = resolveStringField(record, ['name_last', 'last_name', 'family_name']);
  const combined = `${first} ${last}`.trim();
  if (combined) {
    return combined;
  }
  const display = resolveStringField(record, ['display_name', 'label', 'name']);
  if (display) {
    return display;
  }
  const id = resolveContactId(entry);
  return id ? `Contact #${id}` : 'Contact';
}

function resolveContactAlias(entry: ContactLinkRecord): string {
  const record = resolveContactRecord(entry);
  return resolveStringField(record, ['ida_contact', 'ida', 'contact_code']);
}

function resolveContactEmail(entry: ContactLinkRecord): string {
  const record = resolveContactRecord(entry);
  return resolveStringField(record, ['email', 'email_primary', 'contact_email']);
}

function resolveContactPhone(entry: ContactLinkRecord): string {
  const record = resolveContactRecord(entry);
  return resolveStringField(record, ['phone', 'phone_primary', 'phoneCell', 'phone_number']);
}

function resolveContactRole(entry: ContactLinkRecord): string {
  const record = resolveContactRecord(entry);
  return resolveStringField(record, ['role', 'relation', 'type', 'category']);
}

function resolveContactCompany(entry: ContactLinkRecord): string {
  const record = resolveContactRecord(entry);
  return resolveStringField(record, ['company', 'organization', 'org_name', 'company_name']);
}

function resolveContactDomain(entry: ContactLinkRecord): string {
  const record = resolveContactRecord(entry);
  return resolveStringField(record, ['domain', 'website', 'web', 'url']);
}

function resolveContactAddress(entry: ContactLinkRecord): string {
  const record = resolveContactRecord(entry);
  // Check for nested address object first
  const addressObj = record.address as Record<string, unknown> | undefined;
  if (addressObj && typeof addressObj === 'object') {
    const street = resolveStringField(addressObj, ['street', 'address1', 'line1', 'street1']);
    const street2 = resolveStringField(addressObj, ['street2', 'address2', 'line2']);
    return [street, street2].filter(Boolean).join(', ');
  }
  // Fall back to flat fields
  const addr1 = resolveStringField(record, ['address1', 'address', 'street', 'street1']);
  const addr2 = resolveStringField(record, ['address2', 'street2', 'line2']);
  return [addr1, addr2].filter(Boolean).join(', ');
}

function resolveContactCity(entry: ContactLinkRecord): string {
  const record = resolveContactRecord(entry);
  const addressObj = record.address as Record<string, unknown> | undefined;
  if (addressObj && typeof addressObj === 'object') {
    return resolveStringField(addressObj, ['city', 'locality']);
  }
  return resolveStringField(record, ['city', 'locality']);
}

function resolveContactState(entry: ContactLinkRecord): string {
  const record = resolveContactRecord(entry);
  const addressObj = record.address as Record<string, unknown> | undefined;
  if (addressObj && typeof addressObj === 'object') {
    return resolveStringField(addressObj, ['state', 'region', 'province']);
  }
  return resolveStringField(record, ['state', 'region', 'province']);
}

function resolveContactZip(entry: ContactLinkRecord): string {
  const record = resolveContactRecord(entry);
  const addressObj = record.address as Record<string, unknown> | undefined;
  if (addressObj && typeof addressObj === 'object') {
    return resolveStringField(addressObj, ['zip', 'postal_code', 'postalCode', 'zipcode']);
  }
  return resolveStringField(record, ['zip', 'postal_code', 'postalCode', 'zipcode']);
}

function resolveContactPurpose(entry: ContactLinkRecord): string {
  const fallbackTargets = entry as Record<string, unknown>;
  const record = resolveContactRecord(entry);
  const purpose = resolveStringField(record, ['purpose', 'contact_purpose', 'link_purpose', 'context']);
  if (purpose) {
    return purpose;
  }
  // Fallback to entry-level purpose
  return resolveStringField(fallbackTargets, ['purpose', 'contact_purpose', 'link_purpose', 'type']);
}

// ---------------------------------------------------------------------------
// Component Props
// ---------------------------------------------------------------------------

interface ContactLinksTableProps {
  /** The refs object containing links.contact array */
  refs?: Record<string, unknown> | null;
  /** Title to display above the table */
  title?: string;
  /** Initial column order (array of ContactColumnKey) */
  initialColumnOrder?: ContactColumnKey[];
  /** Callback when a row is clicked */
  onRowClick?: (row: ContactLinkDisplayRow) => void;
  /** Callback when edit icon/link is clicked - receives contact id */
  onContactEdit?: (contactId: number) => void;
  /** Enable built-in navigation to /contacts/:id/edit when clicking ID or name */
  enableNavigation?: boolean;
  /** Show empty state message or hide component when no data */
  showEmptyState?: boolean;
  /** Custom class name for the container */
  className?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const ContactLinksTable: React.FC<ContactLinksTableProps> = ({
  refs,
  title = 'refs.links.contact',
  initialColumnOrder,
  onRowClick,
  onContactEdit,
  enableNavigation = false,
  showEmptyState = true,
  className = '',
}) => {
  const navigate = useNavigate();
  
  // Column ordering state
  const [contactColumnOrder, setContactColumnOrder] = useState<ContactColumnKey[]>(
    () => initialColumnOrder || CONTACT_LINK_COLUMN_DEFS.map((def) => def.key)
  );
  const draggingContactColumn = useRef<ContactColumnKey | null>(null);
  
  // Handler for clicking on ID or name to edit contact
  const handleContactEditClick = useCallback(
    (contactId: number | null, event: React.MouseEvent) => {
      if (!contactId) return;
      event.stopPropagation(); // Prevent row click if set
      
      if (onContactEdit) {
        onContactEdit(contactId);
      } else if (enableNavigation) {
        navigate(`/contacts/${contactId}/edit`);
      }
    },
    [onContactEdit, enableNavigation, navigate]
  );

  // Ordered columns based on current order
  const orderedContactColumns = useMemo(() => {
    return contactColumnOrder
      .map((key) => CONTACT_LINK_COLUMN_LOOKUP[key])
      .filter((column): column is ContactLinkColumnDef => Boolean(column));
  }, [contactColumnOrder]);

  // Parse contact rows from refs.links.contact
  const contactLinkRows = useMemo<ContactLinkDisplayRow[]>(() => {
    if (!refs || typeof refs !== 'object') {
      return [];
    }
    const links = (refs as Record<string, unknown>).links;
    if (!links || typeof links !== 'object') {
      return [];
    }
    const contacts = (links as Record<string, unknown>).contact;
    if (!Array.isArray(contacts)) {
      return [];
    }
    return contacts
      .map((entry) => (typeof entry === 'object' && entry ? entry as ContactLinkRecord : {} as ContactLinkRecord))
      .map((entry) => ({
        id: resolveContactId(entry),
        alias: resolveContactAlias(entry),
        name: resolveContactName(entry),
        company: resolveContactCompany(entry),
        role: resolveContactRole(entry),
        purpose: resolveContactPurpose(entry),
        email: resolveContactEmail(entry),
        phone: resolveContactPhone(entry),
        domain: resolveContactDomain(entry),
        address: resolveContactAddress(entry),
        city: resolveContactCity(entry),
        state: resolveContactState(entry),
        zip: resolveContactZip(entry),
        raw: entry,
      }));
  }, [refs]);

  // Drag and drop handlers
  const handleContactColumnDragStart = useCallback(
    (key: ContactColumnKey) => (event: ReactDragEvent<HTMLTableHeaderCellElement>) => {
      draggingContactColumn.current = key;
      event.dataTransfer.effectAllowed = 'move';
    },
    []
  );

  const handleContactColumnDragOver = useCallback(
    (event: ReactDragEvent<HTMLTableHeaderCellElement>) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = 'move';
    },
    []
  );

  const handleContactColumnDrop = useCallback(
    (targetKey: ContactColumnKey) => (event: ReactDragEvent<HTMLTableHeaderCellElement>) => {
      event.preventDefault();
      const sourceKey = draggingContactColumn.current;
      if (!sourceKey || sourceKey === targetKey) {
        return;
      }
      setContactColumnOrder((prev) => {
        const next = [...prev];
        const sourceIndex = next.indexOf(sourceKey);
        const targetIndex = next.indexOf(targetKey);
        if (sourceIndex === -1 || targetIndex === -1) {
          return prev;
        }
        next.splice(sourceIndex, 1);
        next.splice(targetIndex, 0, sourceKey);
        return next;
      });
      draggingContactColumn.current = null;
    },
    []
  );

  const handleContactColumnDragEnd = useCallback(() => {
    draggingContactColumn.current = null;
  }, []);

  const handleRowClick = useCallback(
    (row: ContactLinkDisplayRow) => {
      if (onRowClick) {
        onRowClick(row);
      }
    },
    [onRowClick]
  );

  // Don't render if no data and showEmptyState is false
  if (contactLinkRows.length === 0 && !showEmptyState) {
    return null;
  }

  return (
    <section className={className}>
      <h4 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-300">
        {title}
      </h4>
      <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-gray-50 text-gray-700 dark:bg-gray-800 dark:text-gray-100">
            <tr>
              {orderedContactColumns.map((column) => (
                <th
                  key={column.key}
                  draggable
                  onDragStart={handleContactColumnDragStart(column.key)}
                  onDragOver={handleContactColumnDragOver}
                  onDrop={handleContactColumnDrop(column.key)}
                  onDragEnd={handleContactColumnDragEnd}
                  className="px-3 py-2 font-medium uppercase tracking-wide text-xs cursor-move select-none hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <span className="flex items-center gap-1">
                    <span>{column.label}</span>
                    <span className="text-[10px] text-gray-400">↕</span>
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {contactLinkRows.length === 0 ? (
              <tr>
                <td
                  colSpan={orderedContactColumns.length || 1}
                  className="px-3 py-3 text-center text-sm text-gray-500 dark:text-gray-400"
                >
                  No linked contacts.
                </td>
              </tr>
            ) : (
              contactLinkRows.map((row, index) => (
                <tr
                  key={`contact-row-${row.id ?? index}`}
                  className={`border-b border-gray-100 last:border-none dark:border-gray-700 ${
                    onRowClick ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800' : ''
                  }`}
                  onClick={() => handleRowClick(row)}
                >
                  {orderedContactColumns.map((column) => {
                    // Make ID and name columns clickable for editing
                    const isClickableColumn = (column.key === 'id' || column.key === 'name') && 
                      (onContactEdit || enableNavigation) && 
                      row.id !== null;
                    
                    return (
                      <td 
                        key={column.key} 
                        className={CONTACT_LINK_CELL_CLASS[column.key]}
                        onClick={isClickableColumn ? (e) => handleContactEditClick(row.id, e) : undefined}
                      >
                        {column.render(row)}
                      </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
};

export default ContactLinksTable;

// Also export types for external use
export type { ContactLinkDisplayRow, ContactColumnKey, ContactLinkColumnDef, ContactLinksTableProps };
