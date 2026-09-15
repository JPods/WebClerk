/**
 * Test factories for WebClerk model records.
 *
 * Each factory returns a record with the minimum required fields
 * plus a valid JSON envelope structure (metadata, refs, prefs, comments).
 * Override any field by passing an object.
 */

let _nextId = 1000;
function nextId(): number {
  return _nextId++;
}

function nowUtc(): string {
  return new Date().toISOString().replace(/\.\d{3}/, '').replace(/\+00:00$/, 'Z');
}

function baseRecord(overrides?: Record<string, unknown>) {
  const id = nextId();
  const now = nowUtc();
  return {
    id,
    ida: '',
    is_active: true,
    is_deleted: false,
    status: 'open',
    dt: now,
    dt_created: now,
    dt_modified: now,
    metadata: {},
    refs: {},
    prefs: {},
    comments: {},
    ...overrides,
  };
}

export function buildContact(overrides?: Record<string, unknown>) {
  const id = nextId();
  return {
    ...baseRecord({ id }),
    email: `user${id}@example.com`,
    name_first: 'Test',
    name_last: `Contact${id}`,
    display_name: `Test Contact${id}`,
    ...overrides,
  };
}

export function buildItem(overrides?: Record<string, unknown>) {
  const id = nextId();
  return {
    ...baseRecord({ id }),
    ida: `ITEM-${String(id).padStart(4, '0')}`,
    description: `Test Item ${id}`,
    kind: 'physical',
    ...overrides,
  };
}

export function buildOrder(overrides?: Record<string, unknown>) {
  const id = nextId();
  return {
    ...baseRecord({ id }),
    ida: `SO-${String(id).padStart(5, '0')}`,
    status: 'open',
    totals: { sell: { subtotal: 0, tax: 0, total: 0 } },
    ...overrides,
  };
}

export function buildInvoice(overrides?: Record<string, unknown>) {
  const id = nextId();
  return {
    ...baseRecord({ id }),
    ida: `INV-${String(id).padStart(5, '0')}`,
    status: 'open',
    totals: { sell: { subtotal: 0, tax: 0, total: 0 } },
    ...overrides,
  };
}

export function buildProposal(overrides?: Record<string, unknown>) {
  const id = nextId();
  return {
    ...baseRecord({ id }),
    ida: `QT-${String(id).padStart(5, '0')}`,
    status: 'open',
    totals: { sell: { subtotal: 0, tax: 0, total: 0 } },
    ...overrides,
  };
}

export function buildPayment(overrides?: Record<string, unknown>) {
  const id = nextId();
  return {
    ...baseRecord({ id }),
    ida: `PMT-${String(id).padStart(5, '0')}`,
    amount: 0,
    method: '',
    ...overrides,
  };
}
