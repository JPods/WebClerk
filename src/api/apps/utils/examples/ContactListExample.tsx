import { useState, useEffect, useMemo } from "react";
import { TableColumn } from "react-data-table-component";
import AdvancedDataTable, { ColumnFilter } from "../../../../components/common/AdvancedDataTable";
import { FaPlus } from "react-icons/fa";

// Example: Contact List using the Advanced Data Table
// This demonstrates how to adapt the component for any data model

interface Contact {
  id: string | number;
  name: string;
  email: string;
  phone: string;
  company: string;
  status: "active" | "inactive";
  is_staff: boolean;
  created_at: string;
}

const ContactListExample = () => {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedContacts, setSelectedContacts] = useState<Contact[]>([]);

  // Fetch contacts (replace with your actual API call)
  useEffect(() => {
    setLoading(true);
    // Simulated API call
    setTimeout(() => {
      setContacts([
        {
          id: 1,
          name: "John Doe",
          email: "john@example.com",
          phone: "+1234567890",
          company: "Acme Corp",
          status: "active",
          is_staff: true,
          created_at: "2024-01-15T10:00:00Z",
        },
        {
          id: 2,
          name: "Jane Smith",
          email: "jane@example.com",
          phone: "+0987654321",
          company: "Tech Inc",
          status: "active",
          is_staff: false,
          created_at: "2024-02-20T14:30:00Z",
        },
        // Add more sample data...
      ]);
      setLoading(false);
    }, 1000);
  }, []);

  // Define columns
  const columns: TableColumn<Contact>[] = useMemo(
    () => [
      {
        name: "Name",
        selector: (row) => row.name,
        sortable: true,
        width: "200px",
      },
      {
        name: "Email",
        selector: (row) => row.email,
        sortable: true,
        width: "220px",
      },
      {
        name: "Phone",
        selector: (row) => row.phone,
        sortable: true,
        width: "150px",
      },
      {
        name: "Company",
        selector: (row) => row.company,
        sortable: true,
        width: "180px",
      },
      {
        name: "Status",
        selector: (row) => row.status,
        sortable: true,
        width: "120px",
        cell: (row) => (
          <span
            className={`px-3 py-1 text-xs font-semibold rounded-full ${
              row.status === "active"
                ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                : "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300"
            }`}
          >
            {row.status}
          </span>
        ),
      },
      {
        name: "Staff",
        selector: (row) => (row.is_staff ? "Yes" : "No"),
        sortable: true,
        width: "100px",
        cell: (row) => (
          <span className={row.is_staff ? "text-green-600" : "text-gray-400"}>
            {row.is_staff ? "✓ Yes" : "✗ No"}
          </span>
        ),
      },
      {
        name: "Created",
        selector: (row) => row.created_at,
        sortable: true,
        width: "150px",
        cell: (row) => new Date(row.created_at).toLocaleDateString(),
      },
    ],
    []
  );

  // Define filters - extracted from actual data
  const filters: ColumnFilter[] = useMemo(() => {
    const companies = Array.from(new Set(contacts.map((c) => c.company)))
      .filter(Boolean)
      .map((company) => ({ value: company, label: company }));

    return [
      {
        key: "status",
        label: "Status",
        type: "select",
        options: [
          { value: "active", label: "Active" },
          { value: "inactive", label: "Inactive" },
        ],
      },
      {
        key: "company",
        label: "Company",
        type: "select",
        options: companies,
      },
      {
        key: "is_staff",
        label: "Staff Member",
        type: "select",
        options: [
          { value: "true", label: "Yes" },
          { value: "false", label: "No" },
        ],
      },
    ];
  }, [contacts]);

  // Handle bulk operations
  const handleBulkAction = () => {
    console.log("Bulk action for:", selectedContacts);
    alert(`Performing action on ${selectedContacts.length} contacts`);
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6 text-gray-900 dark:text-white">
        Contact List Example
      </h1>

      <AdvancedDataTable
        data={contacts}
        columns={columns}
        title="Contacts"
        loading={loading}
        filters={filters}
        enableExport={true}
        enableSelection={true}
        onSelectionChange={setSelectedContacts}
        exportFileName="contacts"
        searchPlaceholder="Search contacts by name, email, phone, company..."
        noDataMessage="No contacts found"
        customActions={
          <div className="flex gap-2">
            {selectedContacts.length > 0 && (
              <button
                onClick={handleBulkAction}
                className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 transition-colors"
              >
                Bulk Action ({selectedContacts.length})
              </button>
            )}
            <button
              onClick={() => alert("Add new contact")}
              className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
            >
              <FaPlus className="w-4 h-4" />
              New Contact
            </button>
          </div>
        }
        onRowClicked={(row) => {
          console.log("Row clicked:", row);
          alert(`Viewing contact: ${row.name}`);
        }}
      />

      {/* Usage Instructions */}
      <div className="mt-8 p-6 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
        <h2 className="text-lg font-semibold mb-3 text-blue-900 dark:text-blue-100">
          📚 Usage Example
        </h2>
        <p className="text-sm text-blue-800 dark:text-blue-200 mb-4">
          This is a complete example of using the AdvancedDataTable component. Key features:
        </p>
        <ul className="space-y-2 text-sm text-blue-700 dark:text-blue-300">
          <li>✅ Search across all fields</li>
          <li>✅ Filter by Status, Company, and Staff status</li>
          <li>✅ Sort by any column</li>
          <li>✅ Select individual or all rows</li>
          <li>✅ Export to Excel or PDF (all data or selected only)</li>
          <li>✅ Pagination with customizable rows per page</li>
          <li>✅ Custom actions (Add New, Bulk Action)</li>
          <li>✅ Click rows for details</li>
          <li>✅ Responsive and dark mode ready</li>
        </ul>
      </div>
    </div>
  );
};

export default ContactListExample;
