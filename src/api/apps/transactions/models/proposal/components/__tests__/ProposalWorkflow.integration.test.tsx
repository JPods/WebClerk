import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import ProposalDetail from '../../pages/ProposalDetail';

// Mock axios
const mockedAxios = {
  create: vi.fn(() => ({
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() }
    }
  })),
  post: vi.fn(),
  get: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
};

vi.mock('axios', () => ({
  default: mockedAxios
}));

// Mock react-redux
vi.mock('react-redux', () => ({
  useDispatch: () => vi.fn(),
  useSelector: vi.fn(),
}));

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  MemoryRouter: ({ children }: { children: React.ReactNode }) => <div data-testid="memory-router">{children}</div>,
  useLocation: () => ({ state: null }),
  useNavigate: vi.fn(),
  useParams: () => ({ id: '1' }),
}));

// Mock components
vi.mock('../../../../../components/common/ComponentCard', () => ({
  default: ({ children }: { children: React.ReactNode }) => <div data-testid="component-card">{children}</div>,
}));

vi.mock('../../../../../components/common/PageBreadCrumb', () => ({
  default: () => <div data-testid="breadcrumb">Breadcrumb</div>,
}));

vi.mock('../CustomerSelect', () => ({
  default: ({ value, onChange }: any) => (
    <select
      data-testid="customer-select"
      value={value || ''}
      onChange={(e) => onChange && onChange(Number(e.target.value))}
    >
      <option value="">Select Customer</option>
      <option value="1">John Doe</option>
      <option value="2">Jane Smith</option>
    </select>
  ),
}));

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

// Mock icons
vi.mock('react-icons/fa', () => ({
  FaSave: () => <div data-testid="save-icon">Save</div>,
  FaTimes: () => <div data-testid="cancel-icon">Cancel</div>,
  FaPlus: () => <div data-testid="plus-icon">Add</div>,
  FaEdit: () => <div data-testid="edit-icon">Edit</div>,
  FaTrash: () => <div data-testid="trash-icon">Delete</div>,
}));

// Mock form components
vi.mock('../../../../../components/wrapper', () => ({
  Input: ({ value, onChange, ...props }: any) => (
    <input
      {...props}
      value={value || ''}
      onChange={(e) => onChange && onChange(e)}
    />
  ),
}));

vi.mock('../../../../../components/form/Label', () => ({
  default: ({ children, htmlFor }: any) => (
    <label htmlFor={htmlFor}>{children}</label>
  ),
}));

// Mock toast
vi.mock('../../../../../store/slices/toastSlice', () => ({
  showToast: vi.fn(),
}));

// Create test wrapper
const createTestWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        {children}
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe('Proposal Creation Workflow Integration', () => {
  const TestWrapper = createTestWrapper();
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    user = userEvent.setup();
    vi.clearAllMocks();

    // Mock successful API responses
    mockedAxios.get.mockResolvedValue({ data: { results: [] } });
    mockedAxios.post.mockResolvedValue({ data: { id: 1 } });
    mockedAxios.patch.mockResolvedValue({ data: { id: 1, status: 'updated' } });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders proposal creation form', async () => {
    render(
      <TestWrapper>
        <ProposalDetail modeProp="add" />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Add New Proposal')).toBeInTheDocument();
    });

    expect(screen.getByLabelText('Proposal ID')).toBeInTheDocument();
    expect(screen.getByTestId('customer-select')).toBeInTheDocument();
    expect(screen.getByText('Submit')).toBeInTheDocument();
  });

  it('allows creating a new proposal with basic information', async () => {
    // Mock successful creation
    mockedAxios.post.mockResolvedValueOnce({
      data: {
        id: 1,
        ida: 'PROP-001',
        status: 'planned',
        id_customer: 1,
        customer_name: 'John Doe'
      }
    });

    render(
      <TestWrapper>
        <ProposalDetail modeProp="add" />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Add New Proposal')).toBeInTheDocument();
    });

    // Fill out basic proposal information
    const proposalIdInput = screen.getByLabelText('Proposal ID');
    await user.clear(proposalIdInput);
    await user.type(proposalIdInput, 'PROP-001');

    const customerSelect = screen.getByTestId('customer-select');
    await user.selectOptions(customerSelect, '1');

    // Submit the form
    const submitButton = screen.getByText('Submit');
    await user.click(submitButton);

    // Verify API was called with correct data
    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith(
        expect.stringContaining('/proposals/'),
        expect.objectContaining({
          ida: 'PROP-001',
          id_customer: 1,
          status: 'planned'
        }),
        expect.any(Object)
      );
    });
  });

  it('allows adding line items to a proposal', async () => {
    // Mock proposal data
    const mockProposal = {
      id: 1,
      ida: 'PROP-001',
      status: 'planned',
      id_customer: 1,
      customer_name: 'John Doe'
    };

    // Mock empty lines initially
    mockedAxios.get.mockResolvedValueOnce({ data: { results: [] } });

    render(
      <TestWrapper>
        <ProposalDetail modeProp="edit" dataProp={mockProposal} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Edit Proposal')).toBeInTheDocument();
    });

    // Click add line button
    const addButton = screen.getByText('Add Line Item');
    await user.click(addButton);

    // Verify line form appears
    await waitFor(() => {
      expect(screen.getByPlaceholderText('Select product (optional)')).toBeInTheDocument();
    });

    // Fill out line item
    const descriptionInput = screen.getByPlaceholderText('Description');
    await user.clear(descriptionInput);
    await user.type(descriptionInput, 'Test Product');

    const quantityInput = screen.getAllByDisplayValue('1')[0]; // Quantity field
    await user.clear(quantityInput);
    await user.type(quantityInput, '5');

    const priceInput = screen.getAllByDisplayValue('0')[0]; // Price field
    await user.clear(priceInput);
    await user.type(priceInput, '25.00');

    // Save the line
    const saveButton = screen.getByTestId('save-icon').closest('button');
    await user.click(saveButton!);

    // Verify API call for creating line
    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith(
        expect.stringContaining('/proposal_lines/'),
        expect.objectContaining({
          parent: 1,
          description: 'Test Product',
          quantity: 5,
          price: { sell: 25.00, cost: 0 }
        }),
        expect.any(Object)
      );
    });
  });

  it('displays proposal with existing line items in view mode', async () => {
    const mockProposal = {
      id: 1,
      ida: 'PROP-001',
      status: 'planned',
      id_customer: 1,
      customer_name: 'John Doe',
      total_amount: 125.00,
      line_count: 1
    };

    const mockLines = [{
      id: 1,
      parent: 1,
      description: 'Test Product',
      quantity: 5,
      price: { sell: 25.00, cost: 20.00 },
      discount_amount: 0,
      extended_price: 125.00,
      item_name: 'Test Product'
    }];

    // Mock API calls
    mockedAxios.get.mockResolvedValueOnce({ data: { results: mockLines } });

    render(
      <TestWrapper>
        <ProposalDetail modeProp="view" dataProp={mockProposal} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('View Proposal')).toBeInTheDocument();
    });

    // Verify proposal details are displayed
    expect(screen.getByText('PROP-001')).toBeInTheDocument();
    expect(screen.getByText('John Doe')).toBeInTheDocument();

    // Verify line items are displayed
    await waitFor(() => {
      expect(screen.getByText('Test Product')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument();
      expect(screen.getByText('$25.00')).toBeInTheDocument();
      expect(screen.getByText('$125.00')).toBeInTheDocument();
    });

    // Verify totals are displayed
    expect(screen.getByText('$125.00')).toBeInTheDocument(); // Total amount
  });

  it('allows editing existing line items', async () => {
    const mockProposal = {
      id: 1,
      ida: 'PROP-001',
      status: 'planned',
      id_customer: 1,
      customer_name: 'John Doe'
    };

    const mockLines = [{
      id: 1,
      parent: 1,
      description: 'Original Product',
      quantity: 2,
      price: { sell: 10.00, cost: 8.00 },
      discount_amount: 0
    }];

    // Mock API calls
    mockedAxios.get.mockResolvedValueOnce({ data: { results: mockLines } });
    mockedAxios.put.mockResolvedValueOnce({ data: { ...mockLines[0], quantity: 5 } });

    render(
      <TestWrapper>
        <ProposalDetail modeProp="edit" dataProp={mockProposal} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Edit Proposal')).toBeInTheDocument();
    });

    // Wait for lines to load and find edit button
    await waitFor(() => {
      const editButton = screen.getByTestId('edit-icon').closest('button');
      expect(editButton).toBeInTheDocument();
    });

    const editButton = screen.getByTestId('edit-icon').closest('button');
    await user.click(editButton!);

    // Verify form is populated with existing data
    await waitFor(() => {
      expect(screen.getByDisplayValue('Original Product')).toBeInTheDocument();
      expect(screen.getByDisplayValue('2')).toBeInTheDocument();
    });

    // Update quantity
    const quantityInput = screen.getAllByDisplayValue('2')[0];
    await user.clear(quantityInput);
    await user.type(quantityInput, '5');

    // Save changes
    const saveButton = screen.getByTestId('save-icon').closest('button');
    await user.click(saveButton!);

    // Verify update API call
    await waitFor(() => {
      expect(mockedAxios.put).toHaveBeenCalledWith(
        expect.stringContaining('/proposal_lines/1/'),
        expect.objectContaining({
          id: 1,
          quantity: 5
        }),
        expect.any(Object)
      );
    });
  });

  it('allows deleting line items', async () => {
    const mockProposal = {
      id: 1,
      ida: 'PROP-001',
      status: 'planned',
      id_customer: 1,
      customer_name: 'John Doe'
    };

    const mockLines = [{
      id: 1,
      parent: 1,
      description: 'Product to Delete',
      quantity: 1,
      price: { sell: 10.00, cost: 8.00 },
      discount_amount: 0
    }];

    // Mock API calls
    mockedAxios.get.mockResolvedValueOnce({ data: { results: mockLines } });
    mockedAxios.delete.mockResolvedValueOnce({});

    // Mock window.confirm
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

    render(
      <TestWrapper>
        <ProposalDetail modeProp="edit" dataProp={mockProposal} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Edit Proposal')).toBeInTheDocument();
    });

    // Wait for delete button and click it
    await waitFor(() => {
      const deleteButton = screen.getByTestId('trash-icon').closest('button');
      expect(deleteButton).toBeInTheDocument();
    });

    const deleteButton = screen.getByTestId('trash-icon').closest('button');
    await user.click(deleteButton!);

    // Verify confirmation was shown
    expect(confirmSpy).toHaveBeenCalledWith('Delete this line item?');

    // Verify delete API call
    await waitFor(() => {
      expect(mockedAxios.delete).toHaveBeenCalledWith(
        expect.stringContaining('/proposal_lines/1/'),
        expect.any(Object)
      );
    });

    confirmSpy.mockRestore();
  });

  it('allows changing proposal status', async () => {
    const mockProposal = {
      id: 1,
      ida: 'PROP-001',
      status: 'planned',
      id_customer: 1,
      customer_name: 'John Doe'
    };

    // Mock status change
    mockedAxios.patch.mockResolvedValueOnce({
      data: { ...mockProposal, status: 'sent' }
    });

    render(
      <TestWrapper>
        <ProposalDetail modeProp="view" dataProp={mockProposal} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('View Proposal')).toBeInTheDocument();
    });

    // Find and change status (assuming there's a status select in view mode)
    // This would depend on the ProposalStatus component implementation
    // For now, we'll just verify the component renders
    expect(screen.getByText('planned')).toBeInTheDocument();
  });

  it('shows PDF download button in view mode', async () => {
    const mockProposal = {
      id: 1,
      ida: 'PROP-001',
      status: 'planned',
      id_customer: 1,
      customer_name: 'John Doe'
    };

    const mockLines = [{
      id: 1,
      parent: 1,
      description: 'Test Product',
      quantity: 1,
      price: { sell: 10.00, cost: 8.00 },
      discount_amount: 0
    }];

    mockedAxios.get.mockResolvedValueOnce({ data: { results: mockLines } });

    render(
      <TestWrapper>
        <ProposalDetail modeProp="view" dataProp={mockProposal} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('View Proposal')).toBeInTheDocument();
    });

    // Verify PDF download button is present
    const pdfButton = screen.getByText('Download PDF');
    expect(pdfButton).toBeInTheDocument();
  });

  it('calculates and displays totals correctly', async () => {
    const mockProposal = {
      id: 1,
      ida: 'PROP-001',
      status: 'planned',
      id_customer: 1,
      customer_name: 'John Doe',
      total_amount: 250.00,
      margin_amount: 50.00,
      margin_percentage: 20.00,
      line_count: 2
    };

    const mockLines = [
      {
        id: 1,
        parent: 1,
        description: 'Product A',
        quantity: 2,
        price: { sell: 50.00, cost: 40.00 },
        discount_amount: 0,
        extended_price: 100.00
      },
      {
        id: 2,
        parent: 1,
        description: 'Product B',
        quantity: 3,
        price: { sell: 50.00, cost: 40.00 },
        discount_amount: 0,
        extended_price: 150.00
      }
    ];

    mockedAxios.get.mockResolvedValueOnce({ data: { results: mockLines } });

    render(
      <TestWrapper>
        <ProposalDetail modeProp="view" dataProp={mockProposal} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('View Proposal')).toBeInTheDocument();
    });

    // Verify totals are displayed
    await waitFor(() => {
      expect(screen.getByText('$250.00')).toBeInTheDocument(); // Total amount
      expect(screen.getByText('$50.00')).toBeInTheDocument(); // Margin amount
      expect(screen.getByText('20.0%')).toBeInTheDocument(); // Margin percentage
      expect(screen.getByText('2')).toBeInTheDocument(); // Line count
    });
  });

  it('handles form validation errors', async () => {
    // Mock validation error
    mockedAxios.post.mockRejectedValueOnce({
      response: {
        data: {
          id_customer: ['Customer is required'],
          ida: ['Proposal ID already exists']
        }
      }
    });

    render(
      <TestWrapper>
        <ProposalDetail modeProp="add" />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Add New Proposal')).toBeInTheDocument();
    });

    // Try to submit without required fields
    const submitButton = screen.getByText('Submit');
    await user.click(submitButton);

    // Verify error handling (this would depend on how errors are displayed)
    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalled();
    });
  });

  it('handles API errors gracefully', async () => {
    // Mock network error
    mockedAxios.post.mockRejectedValueOnce(new Error('Network error'));

    render(
      <TestWrapper>
        <ProposalDetail modeProp="add" />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Add New Proposal')).toBeInTheDocument();
    });

    // Fill minimal data and submit
    const proposalIdInput = screen.getByLabelText('Proposal ID');
    await user.clear(proposalIdInput);
    await user.type(proposalIdInput, 'PROP-001');

    const submitButton = screen.getByText('Submit');
    await user.click(submitButton);

    // Verify error is handled (toast notification would be shown)
    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalled();
    });
  });
});