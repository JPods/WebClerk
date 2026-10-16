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
  /** One line for a cache entry in the card's list. */
  line: (row: Record<string, any>) => string;
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
        { field: 'address_type', label: 'type (billing, shipping…)', cache: 'name', wide: true },
        { field: 'address1', label: 'street', wide: true },
        { field: 'address2', label: 'street 2', wide: true },
        { field: 'city', label: 'city' },
        { field: 'state', label: 'state' },
        { field: 'zip', label: 'zip' },
        { field: 'country', label: 'country (US, GB…)' },
      ],
      line: r => [r.full || [r.address1, r.city, r.state, r.zip].filter(Boolean).join(', '),
                  r.name && `(${r.name})`].filter(Boolean).join(' '),
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

/** True when a save of `savedModel` can change what `modelName` shows. */
export function showsCommunication(modelName: string, savedModel: string): boolean {
  return Object.values(COMMUNICATION_FIELDS[modelName] || {}).some(f => f.model === savedModel);
}

/** Fired after a record saves from a detail card: { model, id }. */
export const RECORD_SAVED_EVENT = 'wc3-record-saved';
