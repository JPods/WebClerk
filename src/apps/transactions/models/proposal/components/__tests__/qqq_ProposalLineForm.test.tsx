/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ProposalLineForm from '../ProposalLineForm';

// Mock the ProductSelect component
vi.mock('../ProductSelect', () => ({
  default: ({ value, onChange, placeholder }: any) => (
    <div data-testid="product-select">
      <select
        data-testid="product-select-input"
        value={value || ''}
        onChange={(e) => onChange && onChange(Number(e.target.value), { name: 'Test Product' })}
      >
        <option value="">{placeholder || 'Select product'}</option>
        <option value="1">Test Product</option>
      </select>
    </div>
  ),
}));

// Mock react-icons
vi.mock('react-icons/fa', () => ({
  FaSave: () => <div data-testid="save-icon">Save</div>,
  FaTimes: () => <div data-testid="cancel-icon">Cancel</div>,
}));

describe('ProposalLineForm', () => {
    const renderInTable = (ui: React.ReactElement) => {
      return render(
        <table>
          <tbody>{ui}</tbody>
        </table>
      );
    };
  const mockOnSave = vi.fn();
  const mockOnCancel = vi.fn();
  const mockOnChange = vi.fn();

  const defaultProps = {
    onSave: mockOnSave,
    onCancel: mockOnCancel,
    onChange: mockOnChange,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders form with default values', () => {
    renderInTable(<ProposalLineForm {...defaultProps} />);

    const productSelect = screen.getByTestId('product-select-input');
    expect(productSelect).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Select product (optional)' })).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Description')).toBeInTheDocument();
    const inputs = screen.getAllByRole('spinbutton');
    expect(inputs).toHaveLength(4);
    expect(inputs[0]).toHaveValue(1);
    expect(inputs[1]).toHaveValue(0);
    expect(inputs[2]).toHaveValue(0);
    expect(inputs[3]).toHaveValue(0);
    expect(screen.getByText('$0.00')).toBeInTheDocument(); // total
  });

  it('renders form with provided line data', () => {
    const lineData = {
      id: 1,
      item_id: 123,
      description: 'Test Item',
      quantity: 5,
      price: { sell: 10.50, cost: 8.25 },
      discount_amount: 1.00,
    };

    renderInTable(<ProposalLineForm {...defaultProps} line={lineData} />);

    expect(screen.getByDisplayValue('Test Item')).toBeInTheDocument();
    expect(screen.getByDisplayValue('5')).toBeInTheDocument();
    expect(screen.getByDisplayValue('10.5')).toBeInTheDocument();
    expect(screen.getByDisplayValue('8.25')).toBeInTheDocument();
    expect(screen.getByDisplayValue('1')).toBeInTheDocument();
    expect(screen.getByText('$51.50')).toBeInTheDocument(); // (5 * 10.50) - 1.00
  });

  it('updates description when typing', async () => {
    const user = userEvent.setup();
    renderInTable(<ProposalLineForm {...defaultProps} />);

    const descriptionInput = screen.getByPlaceholderText('Description');
    await user.clear(descriptionInput);
    await user.type(descriptionInput, 'New Description');

    expect(descriptionInput).toHaveValue('New Description');
    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({ description: 'New Description' })
    );
  });

  it('updates quantity when changed', async () => {
    const user = userEvent.setup();
    renderInTable(<ProposalLineForm {...defaultProps} />);

    const quantityInput = screen.getAllByRole('spinbutton')[0];
    await user.clear(quantityInput);
    await user.type(quantityInput, '3');

    expect(quantityInput).toHaveValue(3);
    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({ quantity: 3 })
    );
  });

  it('updates sell price when changed', async () => {
    const user = userEvent.setup();
    renderInTable(<ProposalLineForm {...defaultProps} />);

    const sellPriceInput = screen.getAllByRole('spinbutton')[1];
    await user.clear(sellPriceInput);
    await user.type(sellPriceInput, '25.99');

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({
        price: expect.objectContaining({ sell: 25.99 })
      })
    );
  });

  it('updates cost price when changed', async () => {
    const user = userEvent.setup();
    renderInTable(<ProposalLineForm {...defaultProps} />);

    const costPriceInput = screen.getAllByRole('spinbutton')[2];
    await user.clear(costPriceInput);
    await user.type(costPriceInput, '20.50');

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({
        price: expect.objectContaining({ cost: 20.50 })
      })
    );
  });

  it('updates discount when changed', async () => {
    const user = userEvent.setup();
    renderInTable(<ProposalLineForm {...defaultProps} />);

    const discountInput = screen.getAllByRole('spinbutton')[3];
    await user.clear(discountInput);
    await user.type(discountInput, '5.00');

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({ discount_amount: 5.00 })
    );
  });

  it('updates product selection and description', async () => {
    const user = userEvent.setup();
    renderInTable(<ProposalLineForm {...defaultProps} />);

    const productSelect = screen.getByTestId('product-select-input');
    await user.selectOptions(productSelect, '1');

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({
        item_id: 1,
        description: 'Test Product'
      })
    );
  });

  it('calculates total correctly', async () => {
    const user = userEvent.setup();
    renderInTable(<ProposalLineForm {...defaultProps} />);

    // Set quantity to 2
    const quantityInput = screen.getAllByRole('spinbutton')[0];
    await user.clear(quantityInput);
    await user.type(quantityInput, '2');

    // Set sell price to 15.00
    const sellPriceInput = screen.getAllByRole('spinbutton')[1];
    await user.clear(sellPriceInput);
    await user.type(sellPriceInput, '15.00');

    // Set discount to 3.00
    const discountInput = screen.getAllByRole('spinbutton')[3];
    await user.clear(discountInput);
    await user.type(discountInput, '3.00');

    // Total should be (2 * 15.00) - 3.00 = 27.00
    await waitFor(() => {
      expect(screen.getByText('$27.00')).toBeInTheDocument();
    });
  });

  it('calls onSave with form data when save button is clicked', async () => {
    const user = userEvent.setup();
    renderInTable(<ProposalLineForm {...defaultProps} />);

    // Fill out the form
    const descriptionInput = screen.getByPlaceholderText('Description');
    await user.clear(descriptionInput);
    await user.type(descriptionInput, 'Test Description');

    const quantityInput = screen.getAllByRole('spinbutton')[0];
    await user.clear(quantityInput);
    await user.type(quantityInput, '2');

    // Click save button
    const saveButton = screen.getByTestId('save-icon').closest('button');
    expect(saveButton).toBeInTheDocument();
    await user.click(saveButton!);

    expect(mockOnSave).toHaveBeenCalledWith(
      expect.objectContaining({
        description: 'Test Description',
        quantity: 2,
        price: { sell: 0, cost: 0 },
        discount_amount: 0,
      })
    );
  });

  it('calls onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup();
    renderInTable(<ProposalLineForm {...defaultProps} />);

    const cancelButton = screen.getByTestId('cancel-icon').closest('button');
    expect(cancelButton).toBeInTheDocument();
    await user.click(cancelButton!);

    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });

  it('validates required description field', () => {
    renderInTable(<ProposalLineForm {...defaultProps} />);

    const descriptionInput = screen.getByPlaceholderText('Description');
    expect(descriptionInput).toHaveAttribute('required');
  });

  it('validates numeric inputs', () => {
    renderInTable(<ProposalLineForm {...defaultProps} />);

    const quantityInput = screen.getAllByRole('spinbutton')[0];
    expect(quantityInput).toHaveAttribute('type', 'number');
    expect(quantityInput).toHaveAttribute('min', '0');
    expect(quantityInput).toHaveAttribute('step', '0.01');
    expect(quantityInput).toHaveAttribute('required');

    const numericInputs = screen.getAllByRole('spinbutton');
    numericInputs.forEach(input => {
      expect(input).toHaveAttribute('type', 'number');
      expect(input).toHaveAttribute('min', '0');
      expect(input).toHaveAttribute('step', '0.01');
    });
  });
});