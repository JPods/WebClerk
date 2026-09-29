import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';

const data: Record<string, any[]> = {};
const getRecords = vi.fn((model: string) => Promise.resolve({ results: data[model] || [] }));
const newRecord = vi.fn();
const saveRecord = vi.fn();
vi.mock('../../../api/wcapi', () => ({
  getRecords: (m: string, ...a: any[]) => getRecords(m, ...a),
  getRecord: vi.fn().mockResolvedValue({ record: { id: 5, version: 1, name_first: 'Ann' } }),
  newRecord: (...a: any[]) => newRecord(...a),
  saveRecord: (...a: any[]) => saveRecord(...a),
  refusedFrom: (e: any, fallback: string) => ({ message: e?.message || fallback }),
}));
vi.mock('../../../store/hooks', () => ({ useAppSelector: (f: any) => f({ auth: { user: { id: 5 } } }) }));
vi.mock('../../../apps/transactions/components/SpreedlyCardForm', () => ({
  default: (p: any) => <div>card form for invoice {p.invoiceId}: {p.amount}</div>,
}));

import CustomerConsole from '../CustomerConsole';

beforeEach(() => {
  for (const k of Object.keys(data)) delete data[k];
  getRecords.mockClear(); newRecord.mockReset(); saveRecord.mockReset();
});

describe('CustomerConsole', () => {
  it('opens on their balance, orders and open requests', async () => {
    data.invoice = [{ id: 1, ida: '1001-inv', totals: { total: 50, balance: 30 } }];
    data.action = [{ id: 2, status: 'open' }, { id: 3, status: 'complete' }];
    render(<CustomerConsole />);
    expect(await screen.findByText('$30.00')).toBeTruthy();
    expect(screen.getByText('of 3')).toBeTruthy();
  });

  it('pays an invoice with the card form for what is owed', async () => {
    data.invoice = [{ id: 9, ida: '1009-inv', totals: { total: 80, balance: 80 } }];
    render(<CustomerConsole />);
    fireEvent.click(screen.getByText('Invoices'));
    fireEvent.click(await screen.findByText('Pay'));
    expect(screen.getByText('card form for invoice 9: 80')).toBeTruthy();
  });

  it('sends a support request as a new action with its text', async () => {
    newRecord.mockResolvedValue({ id: 44, record: { version: 1 } });
    saveRecord.mockResolvedValue({});
    render(<CustomerConsole />);
    fireEvent.click(screen.getByText('Support'));
    fireEvent.change(await screen.findByPlaceholderText(/What do you need/), { target: { value: 'Late shipment' } });
    fireEvent.click(screen.getByText('Send request'));
    await waitFor(() => expect(saveRecord).toHaveBeenCalled());
    expect(newRecord).toHaveBeenCalledWith('action');
    expect(saveRecord.mock.calls[0]).toEqual(['action', { id: 44, version: 1, description: { en: 'Late shipment' } }]);
  });

  it('offers no new request when three are open', async () => {
    data.action = [{ id: 1, status: 'open' }, { id: 2, status: 'open' }, { id: 3, status: 'active' }];
    render(<CustomerConsole />);
    fireEvent.click(screen.getByText('Support'));
    expect(await screen.findByText(/most at one time/)).toBeTruthy();
    expect(screen.queryByText('Send request')).toBeNull();
  });

  it("shows the server's sentence when an order is refused", async () => {
    data.item = [{ id: 7, ida: 'W-1', name: 'Widget', price: { retail: 12.5 } }];
    newRecord.mockResolvedValue({ id: 70, record: { version: 1 } });
    saveRecord.mockRejectedValue(new Error('Item 7 is not in your catalog.'));
    render(<CustomerConsole />);
    fireEvent.click(within(screen.getByRole('navigation')).getByText('Place an order'));
    fireEvent.click(await screen.findByText('Add'));
    fireEvent.click(screen.getByText('Place order'));
    expect(await screen.findByText('Item 7 is not in your catalog.')).toBeTruthy();
    expect(saveRecord.mock.calls[0][1].lines).toEqual([{ item: { item_id: 7 }, quantity: { active: 1 } }]);
  });
});
