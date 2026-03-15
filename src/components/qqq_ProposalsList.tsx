/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useEffect, useState } from "react";
import DataTable, { TableColumn } from 'react-data-table-component';
import { createTheme } from 'react-data-table-component';
import { getRecords } from "../api/wcapi";

// Create the dark theme only once
createTheme('tailwindDark', {
  text: {
    primary: '#d1d5db',
    secondary: '#9ca3af',
  },
  background: {
    default: '#111827',
  },
  context: {
    background: '#1f2937',
    text: '#d1d5db',
  },
  divider: {
    default: '#374151',
  },
  button: {
    default: '#1f2937',
    hover: '#374151',
    focus: '#6b7280',
    disabled: '#4b5563',
  },
  sortFocus: {
    default: '#d1d5db',
  },
  highlightOnHover: {
    default: '#1e293b',
    text: '#d1d5db',
  },
  striped: {
    default: '#1f2937',
    text: '#d1d5db',
  },
});

interface Proposal {
  id: number;
  proposal_num: string;
  company: string;
  address1: string;
  city: string;
  state: string;
  phone: string;
  phone_cell: string;
  action: string;
  action_by: string;
  action_date: string;
  total: number;
}

interface ProposalsListProps {
  customerId?: number;
  count?: number;
  onCountChange?: (count: number) => void;
}

export default function ProposalsList({ customerId, count, onCountChange }: ProposalsListProps) {
  const [data, setData] = useState<Proposal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProposals();
  }, [customerId]);

  const fetchProposals = async () => {
    setLoading(true);
    try {
      const res = await getRecords('proposal');
      const proposals = res.results || [];
      // Filter by customer if provided
      const filtered = customerId ? proposals.filter((prop: any) => prop.customer_id === customerId) : proposals;
      setData(filtered);
      if (onCountChange) {
        onCountChange(filtered.length);
      }
    } catch (error) {
      console.error("Failed to fetch proposals", error);
      setData([]);
      if (onCountChange) {
        onCountChange(0);
      }
    } finally {
      setLoading(false);
    }
  };

  const columns: TableColumn<Proposal>[] = [
    {
      name: 'Proposal Num',
      selector: (row) => row.proposal_num,
      sortable: true,
      cell: (row) => (
        <a href="#" onClick={(e) => { e.preventDefault(); /* navigate to proposal detail */ }}>
          {row.proposal_num}
        </a>
      ),
    },
    { name: 'Company', selector: (row) => row.company, sortable: true },
    {
      name: 'Address1',
      selector: (row) => row.address1,
      cell: (row) => (
        <a
          href={`https://maps.google.com/?q=${encodeURIComponent(row.address1)},${encodeURIComponent(row.city)},${encodeURIComponent(row.state)}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          {row.address1}
        </a>
      ),
    },
    { name: 'City', selector: (row) => row.city },
    {
      name: 'Phone',
      selector: (row) => row.phone,
      cell: (row) => (
        <a href={`tel:+1${row.phone}`}>{row.phone}</a>
      ),
    },
    {
      name: 'Phone Cell',
      selector: (row) => row.phone_cell,
      cell: (row) => (
        <a href={`tel:+1${row.phone_cell}`}>{row.phone_cell}</a>
      ),
    },
    { name: 'Action', selector: (row) => row.action, sortable: true },
    { name: 'Action By', selector: (row) => row.action_by, sortable: true },
    { name: 'Action Date', selector: (row) => row.action_date, sortable: true },
    {
      name: 'Total',
      selector: (row) => row.total,
      sortable: true,
      right: true,
      format: (row) => `$${row.total?.toFixed(2)}`,
    },
  ];

  return (
    <div>
      <h5>Proposals ({data.length})</h5>
      <div className="overflow-x-auto bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-400 rounded-md">
        <DataTable
          columns={columns}
          data={data}
          progressPending={loading}
          pagination
          theme="default"
          highlightOnHover
          pointerOnHover
        />
      </div>
    </div>
  );
}