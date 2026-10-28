import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

const addCash = vi.fn();
const applyBalance = vi.fn();
vi.mock('../../models/cash/services/cashApi', () => ({
  addCash: (...a: any[]) => addCash(...a),
  applyBalance: (...a: any[]) => applyBalance(...a),
}));
vi.mock('@/api/wcapi', () => ({ getRecords: vi.fn().mockResolvedValue({ results: [] }) }));
vi.mock('react-redux', () => ({ useDispatch: () => vi.fn() }));
vi.mock('@/store/slices/toastSlice', () => ({ showToast: (x: any) => x }));
let role: string | string[] = 'admin';
vi.mock('@/store/hooks', () => ({ useAppSelector: (f: any) => f({ auth: { user: { role } } }) }));
vi.mock('../SpreedlyCardForm', () => ({
  default: (p: any) => <div>card form for invoice {p.invoiceId}: {p.amount}</div>,
}));

import AddCashDialog from '../AddCashDialog';
import AddRelatedDialog from '@/apps/common/components/dialogs/AddRelatedDialog';

beforeEach(() => { addCash.mockReset(); applyBalance.mockReset(); role = 'admin'; });

describe('AddRelatedDialog', () => {
  it("shows the server's sentence when a save is refused and stays open", async () => {
    const onClose = vi.fn();
    render(<AddRelatedDialog isOpen title="Add" fields={[{ name: 'x', label: 'X', kind: 'text', required: true }]}
      initial={{ x: 'a' }} onClose={onClose}
      onSave={() => Promise.reject(new Error('Not fields of cash: bogus'))} />);
    fireEvent.click(screen.getByText('Save'));
    expect(await screen.findByText('Not fields of cash: bogus')).toBeTruthy();
    expect(onClose).not.toHaveBeenCalled();
  });

  it('keeps Save disabled until a required field is filled', () => {
    render(<AddRelatedDialog isOpen title="Add" fields={[{ name: 'x', label: 'X', kind: 'text', required: true }]}
      onClose={() => {}} onSave={() => Promise.resolve()} />);
    expect((screen.getByText('Save').closest('button') as HTMLButtonElement).disabled).toBe(true);
  });
});

describe('AddCashDialog', () => {
  // One command (Bill, 2026-10-25): the payment, its application and the write-off of what is
  // left stand or fall together on the server; the label names the amount written off.
  it('adds cash to an invoice and writes off the rest in the same command', async () => {
    addCash.mockResolvedValue({ applied: { state: 'applied' }, written_off: { amount: 5 } });
    const onDone = vi.fn();
    render(<AddCashDialog isOpen onClose={() => {}} model="invoice" id={7} balance={100} onDone={onDone} />);
    fireEvent.change(screen.getByLabelText('Amount received *'), { target: { value: '95' } });
    fireEvent.click(screen.getByLabelText('Write off what is left: $5.00'));
    fireEvent.click(screen.getByText('Add and apply'));
    await waitFor(() => expect(addCash).toHaveBeenCalledTimes(1));
    expect(addCash.mock.calls[0][0]).toBe('invoice');
    expect(addCash.mock.calls[0][1]).toBe(7);
    expect(addCash.mock.calls[0][2]).toMatchObject({ amount: 95, method: 'check', write_off_rest: true });
    expect(onDone).toHaveBeenCalled();
  });

  it('records a deposit on an order with no write-off offered', async () => {
    addCash.mockResolvedValue({ deposit: true });
    render(<AddCashDialog isOpen onClose={() => {}} model="order" id={3} balance={250} />);
    expect(screen.queryByLabelText(/Write off what is left/)).toBeNull();
    fireEvent.click(screen.getByText('Record deposit'));
    await waitFor(() => expect(addCash).toHaveBeenCalledWith('order', 3, expect.objectContaining({ amount: 250 })));
  });
});

describe('AddCashDialog guards (Fable review)', () => {
  // The server refuses the write-off with the payment; the dialog sends no second command.
  it('sends one command when the payment is refused', async () => {
    addCash.mockResolvedValue({ applied: { state: 'refused', reason: 'customers differ' } });
    render(<AddCashDialog isOpen onClose={() => {}} model="invoice" id={9} balance={100} />);
    fireEvent.change(screen.getByLabelText('Amount received *'), { target: { value: '40' } });
    fireEvent.click(screen.getByLabelText('Write off what is left: $60.00'));
    fireEvent.click(screen.getByText('Add and apply'));
    await waitFor(() => expect(addCash).toHaveBeenCalledTimes(1));
    expect(addCash.mock.calls[0][2]).toMatchObject({ write_off_rest: true });
  });

  it('offers no write-off on a receipt', () => {
    render(<AddCashDialog isOpen onClose={() => {}} model="receipt" id={2} balance={100} />);
    expect(screen.queryByLabelText(/Write off what is left/)).toBeNull();
  });
});

describe('Charge a card', () => {
  it('opens the card form on an invoice for the amount chosen', async () => {
    render(<AddCashDialog isOpen onClose={() => {}} model="invoice" id={7} balance={40} />);
    fireEvent.change(screen.getByLabelText('Amount to charge'), { target: { value: '25' } });
    fireEvent.click(screen.getByText('Charge a card'));
    expect(await screen.findByText('card form for invoice 7: 25')).toBeTruthy();
  });

  it('is not offered to a rep (Bill: reps do not take card payments)', () => {
    role = ['rep'];
    render(<AddCashDialog isOpen onClose={() => {}} model="invoice" id={7} balance={40} />);
    expect(screen.queryByText('Charge a card')).toBeNull();
  });

  it('is not offered on an order or a receipt', () => {
    render(<AddCashDialog isOpen onClose={() => {}} model="receipt" id={7} balance={40} />);
    expect(screen.queryByText('Charge a card')).toBeNull();
  });
});
