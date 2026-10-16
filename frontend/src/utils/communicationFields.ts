import { formatAddress } from '@/utils/fieldFormatters';

/**
 * communicationFields.ts — values a record shows but keeps in another record.
 *
 * Bill, 2026-10-16: a contact's phone, address and domain are edited only in their own
 * Phone / Address / Domain card. The contact holds a pointer (phone_id, …) and a cache
 * the server rebuilds when either side saves. Clicking the field opens the card; one
 * way to edit, so the two cannot drift.
 *
 * The login email stays on the contact: it flows one way into its Email record.
 */

/** One input in the card: the record's field, and its key in the contact's cache
 *  (refs.links.<kind>[]) when the two differ. */
export type CommunicationInput = { field: string; label: string; cache?: string; wide?: boolean };

export type CommunicationField = {
  model: string;
  pointer: string;
  /** Key of the cache list in refs.links. */
  kind: string;
  label: string;
  inputs: CommunicationInput[];
  /** What the contact's field shows for its cache entry. */
  line: (row: Record<string, any>) => string;
  /** Live preview in the card while typing (the server's format is authoritative). */
  preview?: (values: Record<string, string>) => string;
};

export const COMMUNICATION_FIELDS: Record<string, Record<string, CommunicationField>> = {
  contact: {
    phone: {
      model: 'phone', pointer: 'phone_id', kind: 'phone', label: 'phone',
      inputs: [
        { field: 'number', label: 'number' },
        { field: 'name', label: 'type (cell, office…)' },
        { field: 'country_code', label: 'country code' },
      ],
      line: r => [r.number, r.name && `(${r.name})`].filter(Boolean).join(' '),
    },
    address_full: {
      model: 'address', pointer: 'address_id', kind: 'address', label: 'address',
      inputs: [
        { field: 'address1', label: 'street', wide: true },
        { field: 'address2', label: 'street 2', wide: true },
        { field: 'city', label: 'city' },
        { field: 'state', label: 'state' },
        { field: 'zip', label: 'zip' },
        { field: 'country', label: 'country (US, GB…)' },
        { field: 'address_type', label: 'type (billing, shipping…)', cache: 'name', wide: true },
      ],
      line: r => r.full || formatAddress(r).replace(/\n/g, ', '),
      preview: v => formatAddress(v).replace(/\n/g, ', '),
    },
    domain: {
      model: 'domain', pointer: 'domain_id', kind: 'domain', label: 'domain',
      inputs: [{ field: 'path', label: 'web address or handle', wide: true }],
      line: r => r.path || '',
    },
  },
};

export function communicationField(modelName: string, field: string): CommunicationField | undefined {
  return COMMUNICATION_FIELDS[modelName]?.[field];
}

/** The value a record's field shows: the cache entry its pointer names. The GET does not
 *  carry computed properties (address_full, …), so the field reads the cache itself. */
export function communicationValue(comm: CommunicationField, record: Record<string, any> | null): string {
  const id = record?.[comm.pointer];
  const row = id ? (record?.refs?.links?.[comm.kind] || []).find((r: any) => r?.id === id) : null;
  return row ? comm.line(row) : '';
}

/** True when a save of `savedModel` can change what `modelName` shows. */
export function showsCommunication(modelName: string, savedModel: string): boolean {
  return Object.values(COMMUNICATION_FIELDS[modelName] || {}).some(f => f.model === savedModel);
}

/** Fired after a record saves from a detail card: { model, id }. */
export const RECORD_SAVED_EVENT = 'wc3-record-saved';
