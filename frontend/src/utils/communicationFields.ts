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

export type CommunicationField = { model: string; pointer: string };

export const COMMUNICATION_FIELDS: Record<string, Record<string, CommunicationField>> = {
  contact: {
    phone: { model: 'phone', pointer: 'phone_id' },
    address_full: { model: 'address', pointer: 'address_id' },
    domain: { model: 'domain', pointer: 'domain_id' },
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
