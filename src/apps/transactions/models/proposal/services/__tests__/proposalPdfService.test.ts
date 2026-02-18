import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import jsPDF from 'jspdf';
import { generateProposalPdf } from '../proposalPdfService';

var mockDoc: any = {};

vi.mock('jspdf', () => ({
  default: vi.fn(function (this: any) {
    Object.assign(this, mockDoc);
    return this;
  }),
}));

describe('Proposal PDF Service', () => {
  beforeEach(() => {
    // Reset mocks
    vi.clearAllMocks();

    // Create a fresh mock instance
    mockDoc = {
      setFont: vi.fn(),
      setFontSize: vi.fn(),
      text: vi.fn(),
      line: vi.fn(),
      addPage: vi.fn(),
      setPage: vi.fn(),
      getNumberOfPages: vi.fn().mockReturnValue(1),
      save: vi.fn(),
    };
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  const createMockProposal = (overrides: any = {}) => ({
    id: 1,
    uuid: 'test-uuid',
    ida: 'PROP-001',
    status: 'planned',
    id_customer: 1,
    version: 1,
    dt_created: '2024-01-01T00:00:00Z',
    dt_modified: '2024-01-01T00:00:00Z',
    ...overrides,
  });

  const createMockProposalData = (proposalOverrides: any = {}, lines: any[] = []) => ({
    proposal: createMockProposal(proposalOverrides),
    lines,
  });

  it('creates a new jsPDF document', () => {
    const proposalData = createMockProposalData();

    generateProposalPdf(proposalData);

    expect(jsPDF).toHaveBeenCalledTimes(1);
  });

  it('sets up document with correct initial settings', () => {
    const proposalData = {
      proposal: {
        id: 1,
        ida: 'PROP-001',
        uuid: 'mock-uuid',
        status: 'planned',
        id_customer: 42,
        dt_created: '2024-01-01T00:00:00Z',
        dt_modified: '2024-01-01T00:00:00Z',
        version: 1,
      },
      lines: [],
    };

    generateProposalPdf(proposalData);

    expect(mockDoc.setFont).toHaveBeenCalledWith('helvetica');
    expect(mockDoc.setFontSize).toHaveBeenCalledWith(20);
    expect(mockDoc.setFont).toHaveBeenCalledWith('helvetica', 'bold');
    expect(mockDoc.text).toHaveBeenCalledWith('WebClerk', 20, 30);
  });

  it('includes proposal header information', () => {
    const proposalData = {
      proposal: {
        id: 1,
        ida: 'PROP-001',
        uuid: 'mock-uuid',
        status: 'planned',
        id_customer: 42,
        dt_created: '2024-01-01T00:00:00Z',
        dt_modified: '2024-01-01T00:00:00Z',
        version: 1,
      },
      lines: [],
    };

    generateProposalPdf(proposalData);

    // Check proposal details section
    expect(mockDoc.setFontSize).toHaveBeenCalledWith(14);
    expect(mockDoc.text).toHaveBeenCalledWith('Proposal Details', 20, 60);

    // Check proposal ID
    expect(mockDoc.text).toHaveBeenCalledWith('Proposal ID: PROP-001', 20, expect.any(Number));
    expect(mockDoc.text).toHaveBeenCalledWith('Status: planned', 20, expect.any(Number));
  });

  it('includes customer and vendor information when provided', () => {
    const proposalData = {
      proposal: {
        id: 1,
        ida: 'PROP-001',
        status: 'planned',
        dt_created: '2024-01-01T00:00:00Z',
        dt_modified: '2024-01-01T00:00:00Z',
      },
      lines: [],
      customerName: 'John Doe',
      vendorName: 'Jane Smith',
    };

    generateProposalPdf(proposalData);

    expect(mockDoc.text).toHaveBeenCalledWith('Customer: John Doe', 20, expect.any(Number));
    expect(mockDoc.text).toHaveBeenCalledWith('Vendor: Jane Smith', 20, expect.any(Number));
  });

  it('includes line items table when lines exist', () => {
    const proposalData = {
      proposal: {
        id: 1,
        ida: 'PROP-001',
        status: 'planned',
        dt_created: '2024-01-01T00:00:00Z',
        dt_modified: '2024-01-01T00:00:00Z',
      },
      lines: [
        {
          id: 1,
          item: { ida_item: 'ITEM-001', description: 'Test Item' },
          quantity: { placed: 2 },
          price: { unit: 10.00, extended: 20.00 },
        },
        {
          id: 2,
          item: { ida_item: 'ITEM-002', description: 'Another Item' },
          quantity: { placed: 1 },
          price: { unit: 15.00, extended: 15.00, discount_amount: 2.00 },
        },
      ],
    };

    generateProposalPdf(proposalData);

    // Check table headers
    expect(mockDoc.text).toHaveBeenCalledWith('Item', 20, expect.any(Number));
    expect(mockDoc.text).toHaveBeenCalledWith('Description', 60, expect.any(Number));
    expect(mockDoc.text).toHaveBeenCalledWith('Qty', 140, expect.any(Number));
    expect(mockDoc.text).toHaveBeenCalledWith('Price', 160, expect.any(Number));
    expect(mockDoc.text).toHaveBeenCalledWith('Total', 180, expect.any(Number));

    // Check line item data
    expect(mockDoc.text).toHaveBeenCalledWith('ITEM-001', 20, expect.any(Number));
    expect(mockDoc.text).toHaveBeenCalledWith('Test Item', 60, expect.any(Number));
    expect(mockDoc.text).toHaveBeenCalledWith('2', 140, expect.any(Number));
    expect(mockDoc.text).toHaveBeenCalledWith('$10.00', 160, expect.any(Number));
    expect(mockDoc.text).toHaveBeenCalledWith('$20.00', 180, expect.any(Number));

    expect(mockDoc.text).toHaveBeenCalledWith('ITEM-002', 20, expect.any(Number));
    expect(mockDoc.text).toHaveBeenCalledWith('Another Item', 60, expect.any(Number));
    expect(mockDoc.text).toHaveBeenCalledWith('1', 140, expect.any(Number));
    expect(mockDoc.text).toHaveBeenCalledWith('$15.00', 160, expect.any(Number));
    expect(mockDoc.text).toHaveBeenCalledWith('$15.00', 180, expect.any(Number)); // extended total
  });

  it('calculates and displays totals correctly', () => {
    const proposalData = {
      proposal: {
        id: 1,
        ida: 'PROP-001',
        status: 'planned',
        dt_created: '2024-01-01T00:00:00Z',
        dt_modified: '2024-01-01T00:00:00Z',
      },
      lines: [
        {
          id: 1,
          item: { ida_item: 'ITEM-001' },
          quantity: { placed: 2 },
          price: { unit: 10.00, extended: 20.00 },
        },
        {
          id: 2,
          item: { ida_item: 'ITEM-002' },
          quantity: { placed: 1 },
          price: { unit: 15.00, extended: 15.00, discount_amount: 2.00 },
        },
      ],
    };

    generateProposalPdf(proposalData);

    // Check totals: 20.00 + 13.00 = 33.00
    expect(mockDoc.text).toHaveBeenCalledWith('Subtotal:', 140, expect.any(Number));
    expect(mockDoc.text).toHaveBeenCalledWith('$33.00', 180, expect.any(Number));

    expect(mockDoc.text).toHaveBeenCalledWith('Total:', 140, expect.any(Number));
    expect(mockDoc.text).toHaveBeenCalledWith('$33.00', 180, expect.any(Number));
  });

  it('handles discounts in totals calculation', () => {
    const proposalData = {
      proposal: {
        id: 1,
        ida: 'PROP-001',
        status: 'planned',
        dt_created: '2024-01-01T00:00:00Z',
        dt_modified: '2024-01-01T00:00:00Z',
      },
      lines: [
        {
          id: 1,
          item: { ida_item: 'ITEM-001' },
          quantity: { placed: 2 },
          price: { unit: 10.00, extended: 20.00 },
        },
      ],
    };

    // Manually set discount on the line for testing
    proposalData.lines[0].price!.discount_amount = 5.00;

    generateProposalPdf(proposalData);

    // Subtotal: 20.00, Discount: 5.00, Total: 15.00
    expect(mockDoc.text).toHaveBeenCalledWith('Subtotal:', 140, expect.any(Number));
    expect(mockDoc.text).toHaveBeenCalledWith('$20.00', 180, expect.any(Number));
    expect(mockDoc.text).toHaveBeenCalledWith('Discount:', 140, expect.any(Number));
    expect(mockDoc.text).toHaveBeenCalledWith('-$5.00', 180, expect.any(Number));
    expect(mockDoc.text).toHaveBeenCalledWith('Total:', 140, expect.any(Number));
    expect(mockDoc.text).toHaveBeenCalledWith('$15.00', 180, expect.any(Number));
  });

  it('adds page numbers and footer', () => {
    const proposalData = {
      proposal: {
        id: 1,
        ida: 'PROP-001',
        status: 'planned',
        dt_created: '2024-01-01T00:00:00Z',
        dt_modified: '2024-01-01T00:00:00Z',
      },
      lines: [],
    };

    generateProposalPdf(proposalData);

    expect(mockDoc.getNumberOfPages).toHaveBeenCalled();
    expect(mockDoc.setFontSize).toHaveBeenCalledWith(8);
    expect(mockDoc.text).toHaveBeenCalledWith('Page 1 of 1', 20, 285);
    expect(mockDoc.text).toHaveBeenCalledWith('Generated by WebClerk', 150, 285);
  });

  it('saves the PDF with correct filename', () => {
    const proposalData = {
      proposal: {
        id: 1,
        ida: 'PROP-001',
        status: 'planned',
        dt_created: '2024-01-01T00:00:00Z',
        dt_modified: '2024-01-01T00:00:00Z',
      },
      lines: [],
    };

    // Mock Date to return a consistent date
    const mockDate = new Date('2024-01-15');
    vi.useFakeTimers();
    vi.setSystemTime(mockDate);

    generateProposalPdf(proposalData);

    expect(mockDoc.save).toHaveBeenCalledWith('Proposal_PROP-001_2024-01-15.pdf');

    vi.useRealTimers();
  });

  it('handles missing proposal IDA gracefully', () => {
    const proposalData = {
      proposal: {
        id: 123,
        uuid: 'missing-ida-uuid',
        status: 'planned',
        id_customer: 42,
        dt_created: '2024-01-01T00:00:00Z',
        dt_modified: '2024-01-01T00:00:00Z',
        version: 1,
        // No ida field
      },
      lines: [],
    };

    const mockDate = new Date('2024-01-15');
    vi.useFakeTimers();
    vi.setSystemTime(mockDate);

    generateProposalPdf(proposalData);

    expect(mockDoc.save).toHaveBeenCalledWith('Proposal_123_2024-01-15.pdf');

    vi.useRealTimers();
  });

  it('handles long text truncation in table', () => {
    const proposalData = {
      proposal: {
        id: 1,
        ida: 'PROP-001',
        uuid: 'mock-uuid',
        status: 'planned',
        id_customer: 42,
        dt_created: '2024-01-01T00:00:00Z',
        dt_modified: '2024-01-01T00:00:00Z',
        version: 1,
      },
      lines: [
        {
          id: 1,
          item: {
            ida_item: 'VERY_LONG_ITEM_CODE_THAT_EXCEEDS_LIMITS',
            description: 'This is a very long description that should be truncated because it exceeds the normal display length for PDF generation purposes'
          },
          quantity: { placed: 1 },
          price: { unit: 10.00, extended: 10.00 },
        },
      ],
    };

    generateProposalPdf(proposalData);

    // Check that text was added (exact truncation is handled in the implementation)
    expect(mockDoc.text).toHaveBeenCalledWith(
      expect.stringContaining('VERY_LONG_ITEM_CODE_THAT_EXCEEDS_LIMITS'.substring(0, 15)),
      20,
      expect.any(Number)
    );
  });
});