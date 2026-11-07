/**
 * useRecordForm — the one record-form state (plan 101 step 2). Written before the hook.
 */
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';

const api = {
  getRecord: vi.fn(), saveRecord: vi.fn(), saveTransactionWithLines: vi.fn(),
  previewTotals: vi.fn(), newRecord: vi.fn(),
};
vi.mock('@/api/wcapi', () => ({
  getRecord: (...a: any[]) => api.getRecord(...a),
  saveRecord: (...a: any[]) => api.saveRecord(...a),
  saveTransactionWithLines: (...a: any[]) => api.saveTransactionWithLines(...a),
  previewTotals: (...a: any[]) => api.previewTotals(...a),
  newRecord: (...a: any[]) => api.newRecord(...a),
}));
const toasts: any[] = [];
const dispatch = (x: any) => toasts.push(x);   // one function: a new one each render refetches forever
vi.mock('react-redux', () => ({ useDispatch: () => dispatch }));
vi.mock('@/store/slices/toastSlice', () => ({ showToast: (x: any) => x }));
const windows = { ensureWindow: vi.fn(), closeWindow: vi.fn() };
vi.mock('@/context/WindowManagerContext', () => ({ useWindowManager: () => windows }));
vi.mock('@/hooks/useEditHold', () => ({ useEditHold: () => ({ heldBy: null, touch: () => {} }) }));
vi.mock('@/utils/jsonLimits', () => ({
  jsonLimitsLoaded: () => null, loadJsonLimits: () => Promise.resolve(null),
  checkJsonLimits: () => [], describeJsonLimitProblems: () => '',
}));
vi.mock('@/utils/windowChannel', () => ({ windowChannel: { on: () => () => {}, send: () => {} } }));
vi.mock('@/apps/transactions/utils/applyCustomerDefaults', () => ({
  applyPartyDefaults: vi.fn(), DISPLAY_ONLY_KEYS: ['customer_config', 'customer_company'],
}));

import { useRecordForm, editTierOf, nestedWrite } from './useRecordForm';

const contactLayout: any = { model: 'contact', family: 'core', sections: [{ type: 'header', columns: [] }],
  edit_rules: { status_field: 'status', locked_statuses: ['canceled'] } };
const orderLayout: any = { model: 'order', family: 'sell',
  sections: [{ type: 'header', columns: [] }, { type: 'line_card', family: 'sell' }],
  edit_rules: { status_field: 'status', closed_statuses: ['complete', 'canceled'], pend_statuses: ['released'] } };

beforeEach(() => {
  Object.values(api).forEach((f) => f.mockReset());
  toasts.length = 0;
  api.saveRecord.mockResolvedValue({});
  api.saveTransactionWithLines.mockResolvedValue({});
});

async function load(modelName: string, record: any, layout: any) {
  api.getRecord.mockResolvedValue({ record });
  const hook = renderHook(() => useRecordForm({ modelName, recordId: record.id, layout }));
  await waitFor(() => expect(hook.result.current.loading).toBe(false));
  return hook;
}

describe('useRecordForm', () => {
  it('saves only the fields that changed, with the derived attention', async () => {
    const { result } = await load('contact', { id: 7, version: 3, name_first: 'Al', name_last: '', attention: 'Al', status: 'active' }, contactLayout);
    act(() => result.current.startEdit());
    act(() => result.current.setField('name_last', 'Jones'));
    expect(result.current.editData.attention).toBe('Al Jones');
    await act(() => result.current.save());
    expect(api.saveRecord).toHaveBeenCalledWith('contact', { id: 7, version: 3, name_last: 'Jones', attention: 'Al Jones' });
    expect(api.saveTransactionWithLines).not.toHaveBeenCalled();
    expect(result.current.isEditing).toBe(false);
  });

  it('writes a dotted field into its envelope', () => {
    expect(nestedWrite({ config: { ship_to: { city: 'x' } } }, 'config.ship_to.company', 'Acme'))
      .toEqual({ config: { ship_to: { city: 'x', company: 'Acme' } } });
  });

  it('sends touched lines and identifies a removed saved line with _delete', async () => {
    const record = { id: 20, version: 1, status: 'planned', totals: { total: 10 },
      lines: [{ id: 1, line_number: 1, quantity: { ordered: 1 } }, { id: 2, line_number: 2, quantity: { ordered: 2 } }] };
    const { result } = await load('order', record, orderLayout);
    act(() => result.current.startEdit());
    act(() => result.current.setLines([
      { id: 1, line_number: 1, quantity: { ordered: 5 }, _dirty: true } as any,
      { id: 2, line_number: 2, quantity: { ordered: 2 }, _removed: true } as any,   // the line card marks a removal
      { line_number: 3, quantity: { ordered: 1 }, price: {}, notes: '', _new: true } as any,
    ]));
    await act(() => result.current.save());
    const [model, payload] = api.saveTransactionWithLines.mock.calls[0];
    expect(model).toBe('order');
    expect(payload.id).toBe(20);
    expect(payload.lines).toEqual([
      { id: 1, quantity: { ordered: 5 }, _dirty: true },
      { line_number: 3, quantity: { ordered: 1 }, _new: true },
      { id: 2, line_number: 2, quantity: { ordered: 2 }, _removed: true, _delete: true },
    ]);
    expect(payload).not.toHaveProperty('totals');
    expect(api.saveRecord).not.toHaveBeenCalled();
  });

  it('reads the edit tier from the layout rules and the journal', () => {
    expect(editTierOf({ status: 'complete' }, orderLayout)).toBe('closed');
    expect(editTierOf({ status: 'released' }, orderLayout)).toBe('pend');
    expect(editTierOf({ status: 'planned' }, orderLayout)).toBe('open');
    expect(editTierOf({ status: 'planned', dt_journaled: 1 }, orderLayout)).toBe('closed');
    expect(editTierOf({ status: 'canceled' }, contactLayout)).toBe('closed');
    expect(editTierOf({ status: 'active' }, contactLayout)).toBe('open');
  });

  it('will not open a closed record for edit', async () => {
    const { result } = await load('order', { id: 21, version: 1, status: 'complete', totals: {} }, orderLayout);
    expect(result.current.canEdit).toBe(false);
    act(() => result.current.startEdit());
    expect(result.current.isEditing).toBe(false);
  });

  it("shows the server's sentence when a save is refused and stays in edit", async () => {
    const { result } = await load('contact', { id: 8, version: 1, name_first: 'B', attention: 'B', status: 'active' }, contactLayout);
    api.saveRecord.mockRejectedValue({ response: { data: { message: "Not on the contact list yet: status 'bogus'." } } });
    act(() => result.current.startEdit());
    act(() => result.current.setField('status', 'bogus'));
    await act(() => result.current.save());
    expect(toasts[toasts.length - 1]).toEqual({ message: "Save failed: Not on the contact list yet: status 'bogus'.", type: 'error' });
    expect(result.current.isEditing).toBe(true);
  });

  it('shows a contact field from its communication cache', async () => {
    const { result } = await load('contact', { id: 9, version: 1, attention: 'C', phone_id: 5, status: 'active',
      refs: { links: { phone: [{ id: 5, number: '555-1212' }] } } }, contactLayout);
    expect(result.current.currentData.phone).toBe('555-1212');
  });
});
